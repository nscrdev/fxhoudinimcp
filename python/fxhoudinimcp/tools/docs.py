"""MCP tools for fetching Houdini's local documentation.

Houdini runs a built-in HTTP doc server (the same pages as sidefx.com/docs
but for the exact Houdini version that is running). These tools fetch
from that server directly over localhost — version-exact, zero latency,
no internet dependency.

Port discovery goes through the bridge exactly once (HScript
``helpserverurl``); subsequent fetches use MCP-side httpx against the
cached URL, bypassing Houdini's main thread entirely. A pyro sim can be
mid-cook and docs still come back in ~5 ms.
"""

from __future__ import annotations

# Built-in
import asyncio
import logging
import re
from html.parser import HTMLParser
from urllib.parse import quote

# Third-party
import httpx
from mcp.server.fastmcp import Context

# Internal
from fxhoudinimcp.server import _get_bridge, mcp

logger = logging.getLogger(__name__)


###### Cached help-server URL (discovered lazily on first tool call)

_cached_url: str | None = None
_url_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    """Defer Lock creation until there is a running event loop."""
    global _url_lock
    if _url_lock is None:
        _url_lock = asyncio.Lock()
    return _url_lock


async def _get_help_url(ctx: Context, force_refresh: bool = False) -> str:
    """Return the cached help server URL, discovering via the bridge if needed."""
    global _cached_url
    async with _get_lock():
        if _cached_url is None or force_refresh:
            bridge = _get_bridge(ctx)
            result = await bridge.execute("docs.get_help_server_url")
            _cached_url = result["url"].rstrip("/")
        return _cached_url


###### HTML -> text extraction

# Anchor-link glyphs Houdini injects into every heading (U+23CE return
# symbol, U+00B6 pilcrow, U+2029 paragraph separator). Stripping these
# cleans up empty headings and stray symbols in the extracted text.
_NOISE_CHARS = str.maketrans("", "", "\u23ce\u00b6\u2029")

# Empty-heading cleanup: "## \n" (marker with no content after) survives
# the per-line strip; drop those trailing orphans after join.
_EMPTY_HEADING_RE = re.compile(r"^#{1,6}\s*$", re.MULTILINE)


class _HelpPageExtractor(HTMLParser):
    """Strip Houdini help HTML down to readable text.

    Extracts content inside ``<main>`` when present, falling back to
    ``<body>`` for pages that don't have a main element (search results,
    fragments). Emits newlines around block-level tags, prepends markdown
    heading markers, and drops nav/script/style/header/footer/aside
    chrome entirely.
    """

    _BLOCK_TAGS = {
        "p", "div", "section", "article", "li", "ul", "ol",
        "pre", "table", "tr", "br", "hr",
    }
    _HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
    _SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside"}

    def __init__(self, entry_tag: str = "main") -> None:
        super().__init__()
        self._entry_tag = entry_tag
        self._in_content = False
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == self._entry_tag:
            self._in_content = True
            return
        if not self._in_content:
            return
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in self._HEADING_TAGS:
            level = int(tag[1])
            self._parts.append("\n\n" + ("#" * level) + " ")
        elif tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == self._entry_tag:
            self._in_content = False
            return
        if not self._in_content:
            return
        if tag in self._SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag in self._HEADING_TAGS or tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_content and not self._skip_depth:
            self._parts.append(data.translate(_NOISE_CHARS))

    def get_text(self) -> str:
        raw = "".join(self._parts)
        raw = _EMPTY_HEADING_RE.sub("", raw)
        lines = [ln.strip() for ln in raw.splitlines()]
        cleaned: list[str] = []
        blank_run = 0
        for ln in lines:
            if not ln:
                blank_run += 1
                if blank_run <= 1:
                    cleaned.append("")
            else:
                blank_run = 0
                cleaned.append(ln)
        return "\n".join(cleaned).strip()


def _html_to_text(html: str) -> str:
    """Extract readable text from a Houdini help page.

    Prefers the ``<main>`` region; falls back to ``<body>`` for fragment
    responses (e.g. ``/_search``) that lack a main element.
    """
    entry = "main" if "<main" in html else "body"
    parser = _HelpPageExtractor(entry_tag=entry)
    parser.feed(html)
    return parser.get_text()


###### Optional html2text backend for prettier markdown output

try:
    import html2text as _html2text_mod  # type: ignore[import-not-found]
    _HAS_HTML2TEXT = True
except ImportError:
    _HAS_HTML2TEXT = False


def _html_to_markdown(html: str) -> str:
    """Convert help HTML to markdown via html2text (preserves links/tables).

    Produces ~5-10x more output than ``_html_to_text`` because it keeps
    breadcrumb nav and cross-reference tooltips. Use when you want
    prettier formatting for display; prefer plain text for LLM input.
    """
    if not _HAS_HTML2TEXT:
        raise RuntimeError(
            "format='markdown' requires html2text. "
            "Install with: pip install 'fxhoudinimcp[docs-markdown]'"
        )
    h = _html2text_mod.HTML2Text()
    h.body_width = 0  # disable line wrapping
    h.ignore_images = True
    h.skip_internal_links = True
    return h.handle(html)


def _render(html: str, format: str) -> str:
    """Route to plain-text or markdown renderer based on caller preference."""
    if format == "markdown":
        return _html_to_markdown(html)
    return _html_to_text(html)


###### HTTP fetch with port-refresh fallback

async def _fetch(ctx: Context, path: str) -> str:
    """GET ``path`` from the help server and return the raw HTML body.

    On HTTP failure, refreshes the cached URL once (in case Houdini
    restarted with a new port) and retries. Second failure propagates.
    """
    url = await _get_help_url(ctx)
    full = f"{url}{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(full)
            resp.raise_for_status()
            return resp.text
    except httpx.HTTPError as first_error:
        logger.warning("Docs fetch failed (%s), refreshing URL and retrying", first_error)
        url = await _get_help_url(ctx, force_refresh=True)
        full = f"{url}{path}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(full)
            resp.raise_for_status()
            return resp.text


###### Search result parsing

# Houdini's /_search response nests each hit as:
#   <div class="hit  ">
#     <p class="label">
#       <a class="label" href="/nodes/sop/voronoifracture">Voronoi Fracture</a>
#       <small class="desc">in Geometry nodes</small>
#     </p>
#   </div>
# We deliberately match `class="hit\s*"` (trailing whitespace only) so we
# skip `class="hit findpage"` which is the "Open on separate page" entry.
_SEARCH_HIT_RE = re.compile(
    r'<div[^>]*class="hit\s*"[^>]*>\s*'
    r'<p[^>]*class="label"[^>]*>\s*'
    r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    r'(?:\s*<small[^>]*class="desc"[^>]*>(.*?)</small>)?',
    re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(html: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub("", html)).strip()


def _parse_search_results(html: str, limit: int) -> list[dict]:
    hits: list[dict] = []
    for match in _SEARCH_HIT_RE.finditer(html):
        if len(hits) >= limit:
            break
        href, title_html, desc_html = match.group(1), match.group(2), match.group(3)
        hits.append({
            "path": href,
            "title": _strip_tags(title_html) or href,
            "desc": _strip_tags(desc_html) if desc_html else "",
        })
    return hits


###### Tools

@mcp.tool()
async def get_node_docs(
    ctx: Context,
    context: str,
    node_name: str,
    format: str = "plain",
) -> dict:
    """Fetch the official documentation for a Houdini node.

    Reads Houdini's built-in local help server (same pages as sidefx.com/docs
    but for the exact Houdini version running). Use this before guessing
    parameter names, writing VEX workarounds, or relying on training data —
    node docs change between versions.

    Args:
        context: Node context — one of "sop", "lop", "dop", "chop", "cop",
                 "top", "vop", "obj", "out", "apex".
        node_name: Internal node type name (e.g. "box", "scatter",
                   "pyrosolver", "karmarendersettings", "voronoifracture").
        format: "plain" (default, token-efficient) or "markdown" (preserves
                links/tables, requires the optional html2text dep — install
                with ``pip install 'fxhoudinimcp[docs-markdown]'``).
    """
    ctx_norm = context.lower().strip()
    name_norm = node_name.lower().strip()
    path = f"/nodes/{quote(ctx_norm)}/{quote(name_norm)}.html"
    html = await _fetch(ctx, path)
    return {
        "context": ctx_norm,
        "node_name": name_norm,
        "path": path,
        "format": format,
        "text": _render(html, format),
    }


@mcp.tool()
async def search_docs(
    ctx: Context,
    query: str,
    limit: int = 20,
) -> dict:
    """Search Houdini's local documentation.

    Hits the help server's ``/_search`` endpoint. Use to discover nodes,
    VEX functions, shelf tools, or guide pages you are not sure exist —
    returns hit paths that can be fed back into get_doc_page or
    get_node_docs.

    Args:
        query: Search text (node name, keyword, concept).
        limit: Max number of hits to return (default 20).
    """
    path = f"/_search?q={quote(query)}&lang=en"
    html = await _fetch(ctx, path)
    hits = _parse_search_results(html, limit=limit)
    return {"query": query, "count": len(hits), "hits": hits}


@mcp.tool()
async def get_vex_function(
    ctx: Context,
    function_name: str,
    format: str = "plain",
) -> dict:
    """Fetch documentation for a VEX function.

    Args:
        function_name: VEX function name (e.g. "ch", "chf", "xyzdist",
                       "point", "addpoint", "nearpoints").
        format: "plain" (default) or "markdown" — see get_node_docs.
    """
    name = function_name.lower().strip()
    path = f"/vex/functions/{quote(name)}.html"
    html = await _fetch(ctx, path)
    return {
        "function_name": name,
        "path": path,
        "format": format,
        "text": _render(html, format),
    }


@mcp.tool()
async def get_doc_page(
    ctx: Context,
    path: str,
    format: str = "plain",
) -> dict:
    """Fetch an arbitrary page from Houdini's local help server.

    Use for guide pages that are not node or VEX docs — e.g.
    "/solaris/materials.html", "/pyro/index.html",
    "/expressions/functions.html", "/hom/hou/Node.html".

    Args:
        path: URL path beginning with "/" (e.g. "/solaris/materials.html").
        format: "plain" (default) or "markdown" — see get_node_docs.
    """
    if not path.startswith("/"):
        path = "/" + path
    html = await _fetch(ctx, path)
    return {"path": path, "format": format, "text": _render(html, format)}
