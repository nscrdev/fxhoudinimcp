"""Node-level handlers for FXHoudini-MCP.

Provides tools for creating, inspecting, connecting, and manipulating
nodes within Houdini's node graph.
"""

from __future__ import annotations

# Built-in
import re

# Third-party
import hou

# Internal
from fxhoudinimcp_server.config import auto_layout_enabled, layout_if_enabled
from fxhoudinimcp_server.dispatcher import register_handler


###### Helpers

def _get_node(node_path: str) -> hou.Node:
    """Resolve a node path and raise a clear error if it does not exist."""
    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"Node not found: {node_path}")
    return node


def _node_summary(node: hou.Node) -> dict:
    """Return a compact summary dict for a single node."""
    return {
        "name": node.name(),
        "path": node.path(),
        "type": node.type().name(),
        "category": node.type().category().name(),
    }


def _focus_network_editor(node: hou.Node) -> None:
    """Best-effort: layout the parent network, then pan the editor to *node*."""
    try:
        parent = node.parent()
        if parent is not None:
            layout_if_enabled(parent)
        for pane_tab in hou.ui.paneTabs():
            if pane_tab.type() == hou.paneTabType.NetworkEditor:
                if parent is not None:
                    pane_tab.cd(parent.path())
                pane_tab.setCurrentNode(node)
                pane_tab.homeToSelection()
                return
    except Exception:
        pass  # Never let UI helpers break a tool call


###### nodes.create_node

def create_node(
    parent_path: str,
    node_type: str,
    name: str = None,
    position: list = None,
) -> dict:
    """Create a new node inside the given parent network.

    Args:
        parent_path: Path to the parent network (e.g. "/obj" or "/obj/geo1").
        node_type: Type name (e.g. "geo", "box", "grid", "merge").
        name: Optional explicit node name.
        position: Optional [x, y] position in the network editor.
    """
    parent = _get_node(parent_path)

    try:
        node = parent.createNode(node_type, node_name=name)
    except hou.OperationFailed as e:
        raise ValueError(
            f"Failed to create node of type '{node_type}' inside '{parent_path}': {e}"
        )

    if position is not None and len(position) >= 2:
        node.setPosition(hou.Vector2(position[0], position[1]))

    _focus_network_editor(node)

    return {
        "success": True,
        "node_path": node.path(),
        "node_type": node.type().name(),
        "name": node.name(),
        "position": list(node.position()),
    }


###### nodes.delete_node

def delete_node(node_path: str) -> dict:
    """Delete a node from the scene.

    Args:
        node_path: Absolute path to the node to delete.
    """
    node = _get_node(node_path)
    name = node.name()
    parent_path = node.parent().path()
    node.destroy()

    return {
        "success": True,
        "deleted_node": node_path,
        "name": name,
        "parent_path": parent_path,
    }


###### nodes.rename_node

def rename_node(node_path: str, new_name: str) -> dict:
    """Rename an existing node.

    Args:
        node_path: Absolute path to the node.
        new_name: Desired new name for the node.
    """
    node = _get_node(node_path)
    old_name = node.name()
    node.setName(new_name, unique_name=True)

    return {
        "success": True,
        "old_name": old_name,
        "new_name": node.name(),
        "new_path": node.path(),
    }


###### nodes.classify_node_for_rename

# Verdict reason codes returned by classify_node_for_rename. Documented here so
# downstream tools (bulk_rename_nodes, the houdini-cleanup skill prompt) can
# pattern-match without hard-coding strings in multiple places.
_CLASSIFY_REASONS = (
    "ok",                          # safe to rename
    "node_not_found",              # path did not resolve to any node
    "is_root_or_manager",          # root "/" or top-level manager (/obj, /out, /stage, ...)
    "is_container_hda_wrapper",    # asset definition exists AND its type allows children (Rule 2)
    "inside_hda_contents",         # any ancestor is a container HDA wrapper (Rule 3)
    "inside_locked_hda",           # hou.OpNode.isInsideLockedHDA() == True (locked-asset interior)
    "not_editable",                # hou.Node.isEditable() == False (catch-all engine signal)
)


def _is_container_hda_wrapper(node: hou.Node) -> bool:
    """Return True if *node* is a container HDA wrapper per Rule 2.

    A container HDA wrapper has BOTH:
      1. ``node.type().definition() is not None`` — HDA-implemented type
         (asset definition exists). See /hom/hou/NodeType (definition()).
      2. ``node.type().childTypeCategory() is not None`` — its type can hold
         a child network (equivalent to ``node.isNetwork() == True``).
         See /hom/hou/NodeType (childTypeCategory()) and /hom/hou/Node
         (isNetwork()).

    The previous heuristic also required ``len(node.children()) > 0``; that
    clause is intentionally dropped — an empty / deferred-contents HDA
    wrapper is still an asset wrapper and its name is still part of the
    contract.
    """
    try:
        node_type = node.type()
        if node_type.definition() is None:
            return False
        if node_type.childTypeCategory() is None:
            return False
        return True
    except (hou.OperationFailed, hou.ObjectWasDeleted, AttributeError):
        return False


def _find_containing_hda(node: hou.Node) -> hou.Node | None:
    """Walk parents up to root; return the nearest container HDA wrapper
    ancestor, or None if the node is not inside HDA contents.

    Does not include *node* itself — only ancestors. Use
    ``_is_container_hda_wrapper(node)`` separately to test the node itself.
    """
    try:
        parent = node.parent()
    except (hou.OperationFailed, hou.ObjectWasDeleted, AttributeError):
        return None
    while parent is not None:
        if _is_container_hda_wrapper(parent):
            return parent
        try:
            parent = parent.parent()
        except (hou.OperationFailed, hou.ObjectWasDeleted, AttributeError):
            return None
    return None


def _is_root_or_manager(node: hou.Node) -> bool:
    """Return True for the root node or top-level manager nodes.

    Top-level managers (/obj, /out, /stage, /mat, /tasks, ...) cannot be
    renamed (``hou.NetworkMovableItem.setName`` raises) and asking the
    classifier about them is almost always a misuse, so we report a
    distinct reason.
    """
    try:
        if node.parent() is None:
            return True  # the root /
    except (hou.OperationFailed, hou.ObjectWasDeleted, AttributeError):
        return True
    try:
        if node.type().isManager(include_management_types=True):
            return True
    except (hou.OperationFailed, hou.ObjectWasDeleted, AttributeError):
        pass
    return False


def classify_node_for_rename(node_path: str) -> dict:
    """Decide whether a node is safe to rename for graph-cleanup purposes.

    Centralises Rule 2 (container HDA wrappers off-limits) and Rule 3
    (nodes inside HDA contents are off-limits) of the houdini-cleanup
    skill, plus belt-and-suspenders signals (``isInsideLockedHDA``,
    ``isEditable``). The agent should call this before any rename and
    obey the verdict; ``bulk_rename_nodes`` runs it implicitly when
    ``enforce_safety=True``.

    Doc references:
        /hom/hou/Node — isEditable, isNetwork, setName note about locked
            assets.
        /hom/hou/OpNode — isInsideLockedHDA, matchesCurrentDefinition,
            allowEditingOfContents.
        /hom/hou/NodeType — definition, childTypeCategory, isManager.
        /hom/hou/HDADefinition — locked vs unlocked instances; "Allow
            Editing of Contents".

    Args:
        node_path: Absolute node path to classify.

    Returns:
        Dict with:
            node_path: The path requested.
            allowed: True if the node is safe to rename, False otherwise.
            reason: One of the ``_CLASSIFY_REASONS`` codes.
            containing_asset_path / containing_asset_type: Populated when
                the verdict is ``is_container_hda_wrapper`` /
                ``inside_hda_contents`` / ``inside_locked_hda``; identifies
                the asset whose contract is being protected.
            is_editable: ``hou.Node.isEditable()`` raw value.
            is_inside_locked_hda: ``hou.OpNode.isInsideLockedHDA()`` raw value
                (False when the method is not available, e.g. non-OpNode).
            type_definition_present: True iff ``node.type().definition()`` is
                not None.
            child_type_category: ``node.type().childTypeCategory().name()``
                or None.
    """
    node = hou.node(node_path)
    if node is None:
        return {
            "node_path": node_path,
            "allowed": False,
            "reason": "node_not_found",
            "containing_asset_path": None,
            "containing_asset_type": None,
            "is_editable": None,
            "is_inside_locked_hda": None,
            "type_definition_present": None,
            "child_type_category": None,
        }

    # Type-level signals
    try:
        node_type = node.type()
    except (hou.OperationFailed, hou.ObjectWasDeleted, AttributeError):
        node_type = None

    type_definition_present = False
    child_type_category = None
    if node_type is not None:
        try:
            type_definition_present = node_type.definition() is not None
        except (hou.OperationFailed, AttributeError):
            type_definition_present = False
        try:
            ctc = node_type.childTypeCategory()
            child_type_category = ctc.name() if ctc is not None else None
        except (hou.OperationFailed, AttributeError):
            child_type_category = None

    # Editability signals
    try:
        is_editable = bool(node.isEditable())
    except (hou.OperationFailed, AttributeError):
        is_editable = True  # conservative — only treat False as a positive skip
    try:
        is_inside_locked_hda = bool(node.isInsideLockedHDA())
    except (hou.OperationFailed, AttributeError):
        # isInsideLockedHDA only exists on hou.OpNode; some node-like
        # classes (Apex graph items, etc.) don't implement it.
        is_inside_locked_hda = False

    # Locate any container HDA ancestor (used by multiple branches below).
    containing_hda = _find_containing_hda(node)

    base_payload = {
        "node_path": node_path,
        "is_editable": is_editable,
        "is_inside_locked_hda": is_inside_locked_hda,
        "type_definition_present": type_definition_present,
        "child_type_category": child_type_category,
        "containing_asset_path": containing_hda.path() if containing_hda is not None else None,
        "containing_asset_type": (
            containing_hda.type().name() if containing_hda is not None else None
        ),
    }

    # Rule order matters: report the most specific reason first so the
    # caller can act on it. The ordering below mirrors the skill rules.

    if _is_root_or_manager(node):
        return {**base_payload, "allowed": False, "reason": "is_root_or_manager"}

    if _is_container_hda_wrapper(node):
        # The node itself IS the asset wrapper. Its name carries asset-contract
        # meaning ($OS in primpath defaults, output filenames, USD prim paths
        # for Component Builder, etc.). See /nodes/lop/sopcreate.html and
        # /solaris/component_builder.
        return {
            **base_payload,
            "allowed": False,
            "reason": "is_container_hda_wrapper",
            "containing_asset_path": node.path(),
            "containing_asset_type": node.type().name(),
        }

    if containing_hda is not None:
        # Rule 3: an ancestor is a container HDA wrapper, so this node is
        # inside that asset's editable contents. The asset's internal
        # references (e.g. ``sopimport.soppath = "../sopnet"``) depend on
        # the names here, and the asset definition can be re-saved at any
        # time wiping the changes.
        return {
            **base_payload,
            "allowed": False,
            "reason": "inside_hda_contents",
        }

    if is_inside_locked_hda:
        # Locked HDA contents — Houdini also raises hou.OperationFailed at
        # the engine level via setName, but reporting a clean reason is
        # better than letting the rename attempt blow up.
        return {**base_payload, "allowed": False, "reason": "inside_locked_hda"}

    if not is_editable:
        # Catch-all: covers e.g. "inside locked HDA but not in an editable
        # subnet" cases that the heuristic above would also reach via
        # is_inside_locked_hda, plus any future engine state we haven't
        # enumerated.
        return {**base_payload, "allowed": False, "reason": "not_editable"}

    return {**base_payload, "allowed": True, "reason": "ok"}


###### nodes.bulk_rename_nodes

# A Houdini node name must be a valid identifier: letters, digits, underscores,
# starting with a letter or underscore. ``hou.NetworkMovableItem.setName``
# rejects anything else. Validating up front lets us return a structured
# error instead of letting setName raise mid-batch.
_VALID_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PLACEHOLDER_PREFIX = "__fxh_rename"

# Reference patterns we scan parameter raw values for during the cascade
# scan. These are conservative substring / regex hooks — finding a hit just
# emits a *warning*, never a blocker, because we cannot reliably tell from
# a regex match alone whether a hit is a true reference or a coincidence.
#
# Patterns scanned (per old child base name N):
#   ch("...N..."), chs("...N..."), op:/.../N, opdigits("...N..."),
#   opfullpath("...N..."), and raw ../N/ or /N substrings in any string parm.
# We also report when the parm's expression() (HScript or Python) literally
# contains the old name as a word.


def _common_parent_path(paths: list[str]) -> str | None:
    """Return the deepest common parent path of *paths*, or None if there
    are no paths or they live in different roots."""
    if not paths:
        return None
    split = [p.rstrip("/").split("/") for p in paths]
    # All paths should be absolute (start with "/"), so split[0][0] == "".
    common: list[str] = []
    for parts in zip(*split):
        if all(p == parts[0] for p in parts):
            common.append(parts[0])
        else:
            break
    if len(common) <= 1:
        return "/"
    # We want the *parent* of the common path (since the input paths are
    # the items being renamed — their common parent is one level up unless
    # they have varying depth, in which case we already trimmed).
    parent = "/".join(common)
    return parent or "/"


def _collect_string_parms(root: hou.Node, max_nodes: int = 5000):
    """Yield (node, parm) for every string-bearing parameter under *root*.

    Scans ``root`` and all its descendants. Bounded by *max_nodes* to avoid
    runaway scans on huge scenes — if the cap is hit, the cascade scan is
    marked truncated and the caller surfaces that to the user.
    """
    visited = 0
    stack = [root]
    while stack:
        node = stack.pop()
        visited += 1
        if visited > max_nodes:
            return
        try:
            for parm in node.parms():
                try:
                    pt = parm.parmTemplate()
                    # hou.parmTemplateType.String covers string parms; we
                    # also include Menu / FolderSet etc. that store strings.
                    if pt.dataType() != hou.parmData.String:
                        continue
                except (hou.OperationFailed, AttributeError):
                    continue
                yield node, parm
        except (hou.OperationFailed, hou.ObjectWasDeleted, AttributeError):
            pass
        try:
            for child in node.children():
                stack.append(child)
        except (hou.OperationFailed, hou.ObjectWasDeleted, AttributeError):
            pass


def _build_cascade_patterns(old_names: list[str]) -> list:
    """Build a single compiled regex per old name that catches all reference
    patterns we care about. Returns a list of (old_name, compiled_pattern)
    tuples. Pattern matches are reported as warnings.

    Reference shapes scanned (where N is an old child base name; matched
    case-sensitively because Houdini node names are case-sensitive):

      * ``ch("...N...")``, ``chs(...)``, ``chsop(...)``, ``opdigits(...)``,
        ``opfullpath(...)`` — HScript channel / op-reference functions.
      * ``op:/path/N`` and ``op:'/path/N'`` — old-style op references.
      * ``../N/`` and ``/N/`` — raw relative or absolute path fragments
        embedded in any string parameter (USD primpath, soppath, looppath,
        Stage Manager paths, etc.).
      * Bare word boundary occurrence of N — catches plain references in
        VEX snippets like ``chs("../N/foo")`` (already caught by the chs
        pattern) and Python-language expressions.

    The patterns are intentionally permissive — we'd rather over-report
    than miss a true reference and let it cascade-break.
    """
    patterns = []
    for name in old_names:
        if not name:
            continue
        n = re.escape(name)
        # Use a non-capturing alternation; \b for word boundary on the
        # bare-name case avoids matching names that are substrings of
        # other identifiers.
        pat = re.compile(
            r"(?:"
            r"ch[a-z]*\([^)]*\b" + n + r"\b[^)]*\)"
            r"|op:[^\s\"']*[/']" + n + r"\b"
            r"|\.\./" + n + r"(?:/|\b)"
            r"|/" + n + r"/"
            r"|\b" + n + r"\b"
            r")"
        )
        patterns.append((name, pat))
    return patterns


def _scan_cascade_references(
    network_scope: hou.Node,
    old_names: list[str],
    rename_map: dict[str, str],
    skip_node_paths: set[str],
) -> tuple[list[dict], bool]:
    """Walk every string parameter under *network_scope* and report any
    reference to an old child base name.

    Args:
        network_scope: Root node to scan from. The caller picks this
            (defaults to the common parent of the rename plan).
        old_names: List of old node base names being renamed.
        rename_map: ``{old_name: new_name}`` for inclusion in each warning.
        skip_node_paths: Paths whose parameters we should *not* report on,
            because those nodes are themselves being renamed in this batch
            and any internal references will move with them.

    Returns:
        (warnings, truncated) where warnings is a list of dicts and
        truncated indicates the scan exceeded its node budget.
    """
    if not old_names:
        return [], False

    patterns = _build_cascade_patterns(old_names)
    warnings: list[dict] = []
    truncated = False
    nodes_seen = 0

    for node, parm in _collect_string_parms(network_scope):
        nodes_seen += 1
        if nodes_seen > 5000:
            truncated = True
            break
        node_path = node.path()
        if node_path in skip_node_paths:
            continue
        try:
            raw = parm.rawValue()
        except (hou.OperationFailed, AttributeError):
            raw = None
        try:
            expr = parm.expression()
        except hou.OperationFailed:
            expr = None
        except AttributeError:
            expr = None

        for old_name, pat in patterns:
            for haystack_label, haystack in (("raw_value", raw), ("expression", expr)):
                if not haystack:
                    continue
                m = pat.search(haystack)
                if not m:
                    continue
                warnings.append({
                    "referrer_path": node_path,
                    "param": parm.name(),
                    "matched_in": haystack_label,
                    "matched_text": m.group(0),
                    "old_name": old_name,
                    "new_name": rename_map.get(old_name),
                })
                # One warning per (parm, old_name) pair is enough.
                break

    return warnings, truncated


def _validate_plan_entry(entry: dict) -> tuple[str, str] | dict:
    """Return (node_path, new_name) on success, or a blocker dict on failure."""
    if not isinstance(entry, dict):
        return {"reason": "invalid_entry", "details": {"entry": repr(entry)}}
    node_path = entry.get("node_path")
    new_name = entry.get("new_name")
    if not node_path or not isinstance(node_path, str):
        return {
            "reason": "invalid_entry",
            "details": {"missing": "node_path", "entry": entry},
        }
    if not new_name or not isinstance(new_name, str):
        return {
            "node_path": node_path,
            "reason": "invalid_entry",
            "details": {"missing": "new_name", "entry": entry},
        }
    if not _VALID_NAME_RE.match(new_name):
        return {
            "node_path": node_path,
            "reason": "invalid_name",
            "details": {
                "new_name": new_name,
                "rule": (
                    "Houdini identifiers must match ^[A-Za-z_][A-Za-z0-9_]*$ "
                    "(letters, digits, underscores; cannot start with a digit)."
                ),
            },
        }
    return node_path, new_name


def bulk_rename_nodes(
    plan: list = None,
    enforce_safety: bool = True,
    trust_selection: bool = False,
    scan_cascades: bool = True,
    dry_run: bool = False,
    network_scope: str = None,
) -> dict:
    """Rename multiple nodes atomically, with safety pre-flight and an
    optional cascade-impact scan.

    Designed to replace the per-node ``rename_node`` loop used in the
    houdini-cleanup skill workflow. Closes several failure modes that
    rule-only enforcement leaves open:

      * Atomicity — the whole plan applies or nothing applies. If any
        rename fails mid-batch, every rename already applied is rolled
        back via a placeholder pass.
      * Collisions — pre-flight detects intra-batch collisions and
        out-of-batch collisions with siblings. The execution phase
        renames every entry to a unique placeholder first, then to its
        final name, which lets cycles like A↔B succeed.
      * Safety — when ``enforce_safety=True`` (the default), every entry
        is run through ``classify_node_for_rename``; any verdict other
        than ``ok`` blocks the whole batch.
      * Cascade impact — when ``scan_cascades=True`` (the default), every
        string parameter under *network_scope* is scanned for references
        to the old base names. Hits are reported as **warnings** (not
        blockers) so the user can decide whether to proceed.

    The mixed-parent guard (independent of every flag below) refuses any
    plan whose entries don't all share the same immediate parent. This
    enforces "cleanup touches one network at a time" at the API level;
    the failure shape is a single top-level ``mixed_parents`` blocker
    rather than per-entry blockers.

    Args:
        plan: List of dicts with ``node_path`` (str) and ``new_name`` (str).
        enforce_safety: If True, refuse to apply any rename whose source
            node fails ``classify_node_for_rename``. Default True.
        trust_selection: If True, the verdicts ``is_container_hda_wrapper``
            and ``inside_hda_contents`` are silently treated as ``ok`` —
            they do NOT appear in ``blocked`` and they do NOT generate any
            warning. Use this when the rename targets came from an explicit
            user selection (the user is the source of truth in that case).
            All other verdicts (``inside_locked_hda``, ``not_editable``,
            ``is_root_or_manager``, ``node_not_found``) remain hard
            blockers. Default False. Has no effect when
            ``enforce_safety=False``.
        scan_cascades: If True, scan parameters under *network_scope* for
            ``ch()`` / ``chs()`` / ``op:`` / ``soppath`` / raw path
            references to old base names. Default True.
        dry_run: If True, run pre-flight + cascade scan only — never
            mutate the scene. Returns the same shape as a real run, but
            with ``applied: False`` and the per-entry ``planned`` field
            set instead of ``new_name_actual``.
        network_scope: Root path for the cascade scan. Defaults to the
            deepest common parent of the plan's node paths.

    Returns:
        Dict with:
            applied: True if every rename succeeded (and was committed),
                False if pre-flight or execution blocked the batch (or
                dry_run was True).
            results: Per-entry ``{node_path, old_name,
                new_name_requested, new_name_actual, succeeded}``.
            blocked: List of pre-flight blockers
                ``{node_path, reason, details}``. The single
                ``mixed_parents`` case has ``node_path: None`` and
                ``details: {"parent_paths": [...]}``.
            cascade_warnings: List of cascade-impact warnings
                ``{referrer_path, param, matched_in, matched_text,
                old_name, new_name}``.
            cascade_truncated: True if the cascade scan exceeded its
                node budget and may have missed some references.
            rollback: When applied=False because of an execution-phase
                failure, describes whether the rollback completed
                cleanly. Absent on a clean dry_run / clean pre-flight
                block.
    """
    if plan is None:
        plan = []
    if not isinstance(plan, list):
        raise ValueError("plan must be a list of {node_path, new_name} dicts")

    blocked: list[dict] = []
    normalised: list[dict] = []  # entries that pass shape validation
    seen_paths: set[str] = set()

    # -------- Phase 0: shape + name validation, dedupe --------
    for raw_entry in plan:
        validated = _validate_plan_entry(raw_entry)
        if isinstance(validated, dict):
            blocked.append(validated)
            continue
        node_path, new_name = validated
        if node_path in seen_paths:
            blocked.append({
                "node_path": node_path,
                "reason": "duplicate_entry",
                "details": {"node_path": node_path},
            })
            continue
        seen_paths.add(node_path)
        normalised.append({"node_path": node_path, "new_name": new_name})

    # Resolve nodes
    resolved: list[dict] = []
    for entry in normalised:
        node = hou.node(entry["node_path"])
        if node is None:
            blocked.append({
                "node_path": entry["node_path"],
                "reason": "node_not_found",
                "details": {},
            })
            continue
        try:
            old_name = node.name()
            parent = node.parent()
            parent_path = parent.path() if parent is not None else None
        except (hou.OperationFailed, hou.ObjectWasDeleted, AttributeError) as exc:
            blocked.append({
                "node_path": entry["node_path"],
                "reason": "node_not_found",
                "details": {"error": str(exc)},
            })
            continue
        resolved.append({
            "node": node,
            "node_path": entry["node_path"],
            "old_name": old_name,
            "new_name": entry["new_name"],
            "parent_path": parent_path,
        })

    # -------- Mixed-parent guard --------
    # Cleanup must touch one network at a time. If the resolved entries
    # span multiple immediate parents, refuse the whole batch with a
    # single top-level blocker (rather than per-entry noise). Runs even
    # when enforce_safety=False — this is a structural rule about what a
    # cleanup batch is, not a safety rule about what's renameable.
    distinct_parents = sorted({r["parent_path"] for r in resolved if r["parent_path"] is not None})
    if len(distinct_parents) > 1:
        blocked.append({
            "node_path": None,
            "reason": "mixed_parents",
            "details": {
                "parent_paths": distinct_parents,
                "message": (
                    "Cleanup must target a single network. The plan's nodes "
                    "live under multiple parents; ask the user to narrow the "
                    "selection to one network and try again."
                ),
            },
        })
        # Short-circuit: do not run further pre-flight passes — the agent
        # needs to fix the input before anything else matters.
        results = []
        for r in resolved:
            results.append({
                "node_path": r["node_path"],
                "old_name": r["old_name"],
                "new_name_requested": r["new_name"],
                "new_name_actual": None,
                "planned": True,
                "succeeded": False,
            })
        return {
            "applied": False,
            "dry_run": bool(dry_run),
            "results": results,
            "blocked": blocked,
            "cascade_warnings": [],
            "cascade_truncated": False,
        }

    # -------- Phase 1: safety classification --------
    # When trust_selection is True, the user has explicitly picked these
    # nodes — we silently allow the verdicts that exist purely to protect
    # asset-contract names (`is_container_hda_wrapper`, `inside_hda_contents`).
    # Engine-level guards (`inside_locked_hda`, `not_editable`,
    # `is_root_or_manager`, `node_not_found`) remain hard blockers because
    # they reflect Houdini state that would make the rename fail anyway.
    _SOFT_VERDICTS = {"is_container_hda_wrapper", "inside_hda_contents"}
    if enforce_safety:
        for r in resolved:
            verdict = classify_node_for_rename(r["node_path"])
            if verdict.get("allowed"):
                continue
            reason = verdict.get("reason", "not_allowed")
            if trust_selection and reason in _SOFT_VERDICTS:
                # Silent pass-through: do NOT add to blocked, do NOT add to
                # any warning list. The user picked it; honour the pick.
                continue
            blocked.append({
                "node_path": r["node_path"],
                "reason": reason,
                "details": {
                    "containing_asset_path": verdict.get("containing_asset_path"),
                    "containing_asset_type": verdict.get("containing_asset_type"),
                    "is_editable": verdict.get("is_editable"),
                    "is_inside_locked_hda": verdict.get("is_inside_locked_hda"),
                },
            })
        # Drop blocked entries from the executable set so the collision
        # check below operates on what would actually run.
        blocked_paths = {b.get("node_path") for b in blocked if b.get("node_path")}
        resolved = [r for r in resolved if r["node_path"] not in blocked_paths]

    # -------- Phase 2: collision detection --------
    # (a) Intra-batch: two entries map to the same final name in the same parent.
    by_parent_target: dict[tuple[str | None, str], list[str]] = {}
    for r in resolved:
        key = (r["parent_path"], r["new_name"])
        by_parent_target.setdefault(key, []).append(r["node_path"])
    for (parent_path, new_name), paths in by_parent_target.items():
        if len(paths) > 1:
            for p in paths:
                blocked.append({
                    "node_path": p,
                    "reason": "intra_batch_collision",
                    "details": {
                        "parent_path": parent_path,
                        "new_name": new_name,
                        "conflicts_with": [x for x in paths if x != p],
                    },
                })
    blocked_paths = {b.get("node_path") for b in blocked if b.get("node_path")}
    resolved = [r for r in resolved if r["node_path"] not in blocked_paths]

    # (b) Out-of-batch: an existing sibling already owns the target name and
    # is NOT itself being renamed away.
    batch_paths = {r["node_path"] for r in resolved}
    for r in resolved:
        parent = r["node"].parent()
        if parent is None:
            continue
        try:
            existing = parent.node(r["new_name"])
        except (hou.OperationFailed, AttributeError):
            existing = None
        if existing is None or existing.path() == r["node_path"]:
            continue
        if existing.path() in batch_paths:
            # The colliding sibling is also being renamed away in this batch,
            # so the placeholder phase will free the name in time.
            continue
        blocked.append({
            "node_path": r["node_path"],
            "reason": "external_collision",
            "details": {
                "new_name": r["new_name"],
                "existing_sibling_path": existing.path(),
            },
        })
    blocked_paths = {b.get("node_path") for b in blocked if b.get("node_path")}
    resolved = [r for r in resolved if r["node_path"] not in blocked_paths]

    # -------- Phase 3: cascade scan (warnings only) --------
    cascade_warnings: list[dict] = []
    cascade_truncated = False
    if scan_cascades and resolved:
        if network_scope is not None:
            scope_node = hou.node(network_scope)
            if scope_node is None:
                blocked.append({
                    "node_path": None,
                    "reason": "network_scope_not_found",
                    "details": {"network_scope": network_scope},
                })
        else:
            common = _common_parent_path([r["node_path"] for r in resolved])
            scope_node = hou.node(common) if common else hou.node("/")
            if scope_node is None:
                scope_node = hou.node("/")
        if scope_node is not None:
            old_names = [r["old_name"] for r in resolved]
            rename_map = {r["old_name"]: r["new_name"] for r in resolved}
            cascade_warnings, cascade_truncated = _scan_cascade_references(
                scope_node,
                old_names,
                rename_map,
                skip_node_paths={r["node_path"] for r in resolved},
            )

    # -------- Decide whether to apply --------
    # If there are blockers, never apply. If dry_run, never apply but still
    # report the plan that would have run.
    if blocked or dry_run:
        results = []
        for r in resolved:
            results.append({
                "node_path": r["node_path"],
                "old_name": r["old_name"],
                "new_name_requested": r["new_name"],
                "new_name_actual": None,
                "planned": True,
                "succeeded": False,
            })
        return {
            "applied": False,
            "dry_run": bool(dry_run),
            "results": results,
            "blocked": blocked,
            "cascade_warnings": cascade_warnings,
            "cascade_truncated": cascade_truncated,
        }

    # -------- Phase 4: atomic execution (placeholder pass + final pass) --------
    # Step 1: rename every node to a unique placeholder. Track applied
    # renames in a stack so we can roll back on failure.
    placeholder_stack: list[tuple[hou.Node, str, str]] = []  # (node, original_name, placeholder)
    final_results: list[dict] = []
    rollback_info: dict | None = None

    try:
        for idx, r in enumerate(resolved):
            placeholder = f"{_PLACEHOLDER_PREFIX}_{idx}_{abs(id(r))}"
            try:
                # unique_name=False so we get a real exception on collision
                # (placeholders are unique-by-construction; if this raises
                # something is genuinely wrong).
                r["node"].setName(placeholder, unique_name=False)
            except hou.OperationFailed as exc:
                # Couldn't even apply the placeholder — record and roll back.
                raise _BulkRenameError(
                    phase="placeholder",
                    failing_path=r["node_path"],
                    failing_target=placeholder,
                    underlying=str(exc),
                ) from exc
            placeholder_stack.append((r["node"], r["old_name"], placeholder))

        # Step 2: rename each placeholder to the requested final name. We
        # use unique_name=False so external collisions (which Phase 2
        # should have caught, but guard anyway) raise instead of silently
        # mangling the name.
        for r in resolved:
            try:
                r["node"].setName(r["new_name"], unique_name=False)
            except hou.OperationFailed as exc:
                raise _BulkRenameError(
                    phase="final",
                    failing_path=r["node"].path(),
                    failing_target=r["new_name"],
                    underlying=str(exc),
                ) from exc
            final_results.append({
                "node_path": r["node_path"],
                "old_name": r["old_name"],
                "new_name_requested": r["new_name"],
                "new_name_actual": r["node"].name(),
                "planned": False,
                "succeeded": True,
            })

    except _BulkRenameError as failure:
        # Rollback: walk the placeholder_stack in reverse, restoring
        # original names. If any rollback step itself fails, surface that
        # — never silently leave the scene broken.
        rollback_failures: list[dict] = []
        for node, original_name, _placeholder in reversed(placeholder_stack):
            try:
                node.setName(original_name, unique_name=False)
            except hou.OperationFailed as rb_exc:
                # Best effort: try with unique_name=True so we at least
                # don't leave the placeholder name in place.
                try:
                    node.setName(original_name, unique_name=True)
                    rollback_failures.append({
                        "node_path": node.path(),
                        "intended_name": original_name,
                        "fallback_name": node.name(),
                        "underlying": str(rb_exc),
                    })
                except hou.OperationFailed as rb_exc2:
                    rollback_failures.append({
                        "node_path": node.path(),
                        "intended_name": original_name,
                        "fallback_name": None,
                        "underlying": str(rb_exc2),
                    })

        rollback_info = {
            "completed_cleanly": len(rollback_failures) == 0,
            "failures": rollback_failures,
            "failing_phase": failure.phase,
            "failing_path": failure.failing_path,
            "failing_target": failure.failing_target,
            "underlying_error": failure.underlying,
        }

        # Mark every entry as failed.
        results = []
        for r in resolved:
            results.append({
                "node_path": r["node_path"],
                "old_name": r["old_name"],
                "new_name_requested": r["new_name"],
                "new_name_actual": None,
                "planned": True,
                "succeeded": False,
            })
        return {
            "applied": False,
            "dry_run": False,
            "results": results,
            "blocked": blocked,
            "cascade_warnings": cascade_warnings,
            "cascade_truncated": cascade_truncated,
            "rollback": rollback_info,
        }

    return {
        "applied": True,
        "dry_run": False,
        "results": final_results,
        "blocked": blocked,  # always empty in the success path, but keep the key for shape stability
        "cascade_warnings": cascade_warnings,
        "cascade_truncated": cascade_truncated,
    }


class _BulkRenameError(Exception):
    """Internal sentinel raised mid-execution to trigger placeholder rollback.

    Carries enough context to populate the structured ``rollback`` section
    of the bulk_rename_nodes response.
    """

    def __init__(self, phase: str, failing_path: str, failing_target: str, underlying: str):
        super().__init__(f"{phase} phase failed for {failing_path} -> {failing_target}: {underlying}")
        self.phase = phase
        self.failing_path = failing_path
        self.failing_target = failing_target
        self.underlying = underlying


###### nodes.copy_node

def copy_node(
    node_path: str,
    dest_parent: str = None,
    new_name: str = None,
) -> dict:
    """Copy a node, optionally into a different parent network.

    Args:
        node_path: Path to the source node.
        dest_parent: Destination parent path. If None, copies within the same parent.
        new_name: Optional name for the copied node.
    """
    node = _get_node(node_path)
    parent = _get_node(dest_parent) if dest_parent else node.parent()

    copied = hou.copyNodesTo([node], parent)[0]

    if new_name:
        copied.setName(new_name, unique_name=True)

    return {
        "success": True,
        "source_path": node_path,
        "copied_path": copied.path(),
        "name": copied.name(),
    }


###### nodes.move_node

def move_node(node_path: str, dest_parent: str) -> dict:
    """Move a node to a different parent network.

    Args:
        node_path: Path to the node to move.
        dest_parent: Destination parent network path.
    """
    node = _get_node(node_path)
    dest = _get_node(dest_parent)

    moved = hou.moveNodesTo([node], dest)[0]

    return {
        "success": True,
        "original_path": node_path,
        "new_path": moved.path(),
        "name": moved.name(),
    }


###### nodes.get_node_info

def get_node_info(node_path: str) -> dict:
    """Return comprehensive information about a node.

    Includes type, parameters summary, inputs, outputs, flags,
    errors, warnings, and cook time.

    Args:
        node_path: Absolute path to the node.
    """
    node = _get_node(node_path)

    # Only return parameters that differ from their defaults — this keeps
    # the response compact (a complex node can have 500+ parms, most at default).
    # Use get_parameter_schema to inspect the full parameter list.
    all_parms = node.parms()
    parms_summary = []
    for parm in all_parms:
        try:
            val = parm.eval()
        except Exception:
            continue
        try:
            default = parm.parmTemplate().defaultValue()
            if isinstance(default, tuple) and len(default) == 1:
                default = default[0]
        except Exception:
            default = None
        if val == default:
            continue
        parms_summary.append({
            "name": parm.name(),
            "label": parm.description(),
            "value": val if not isinstance(val, (hou.Vector2, hou.Vector3, hou.Vector4)) else list(val),
            "default": default if not isinstance(default, tuple) else list(default),
            "type": parm.parmTemplate().type().name(),
        })

    # Inputs
    inputs = []
    for i, conn in enumerate(node.inputs()):
        if conn is not None:
            inputs.append({
                "index": i,
                "node_path": conn.path(),
                "node_name": conn.name(),
            })
        else:
            inputs.append({"index": i, "node_path": None, "node_name": None})

    # Outputs
    outputs = []
    for conn in node.outputs():
        outputs.append({
            "node_path": conn.path(),
            "node_name": conn.name(),
        })

    # Flags
    flags = {}
    try:
        flags["display"] = node.isDisplayFlagSet()
    except Exception:
        pass
    try:
        flags["render"] = node.isRenderFlagSet()
    except Exception:
        pass
    try:
        flags["bypass"] = node.isBypassed()
    except Exception:
        pass
    try:
        flags["template"] = node.isTemplateFlagSet()
    except Exception:
        pass
    try:
        flags["lock"] = node.isHardLocked()
    except Exception:
        pass

    # Errors and warnings
    try:
        errors = list(node.errors())
    except Exception:
        errors = []
    try:
        warnings = list(node.warnings())
    except Exception:
        warnings = []

    # Cook time
    try:
        cook_time = node.cookTime()
    except Exception:
        cook_time = None

    # Type info — icon omitted (string path, useless to LLM)
    node_type = node.type()
    type_info = {
        "name": node_type.name(),
        "label": node_type.description(),
        "category": node_type.category().name(),
    }

    return {
        "node_path": node.path(),
        "name": node.name(),
        "type": type_info,
        "total_param_count": len(all_parms),
        "non_default_parameters": parms_summary,
        "input_connectors": node.type().maxNumInputs(),
        "inputs": inputs,
        "outputs": outputs,
        "flags": flags,
        "errors": errors,
        "warnings": warnings,
        "cook_time": cook_time,
        "comment": node.comment(),
        "position": list(node.position()),
        "color": list(node.color().rgb()),
    }


###### nodes.list_children

def list_children(
    parent_path: str,
    recursive: bool = False,
    filter_type: str = None,
) -> dict:
    """List children of a network node.

    Args:
        parent_path: Path to the parent network.
        recursive: If True, list all descendants, not just direct children.
        filter_type: Optional node type name to filter by (e.g. "box", "merge").
    """
    parent = _get_node(parent_path)

    if recursive:
        children = parent.allSubChildren()
    else:
        children = parent.children()

    _MAX_CHILDREN = 500
    results = []
    for child in children:
        if filter_type and child.type().name() != filter_type:
            continue
        results.append(_node_summary(child))
        if len(results) >= _MAX_CHILDREN:
            break

    return {
        "parent_path": parent_path,
        "count": len(results),
        "truncated": len(results) >= _MAX_CHILDREN,
        "children": results,
    }


###### nodes.find_nodes

def find_nodes(
    pattern: str = None,
    node_type: str = None,
    context: str = None,
    inside: str = "/",
) -> dict:
    """Search for nodes by name pattern and/or type.

    Args:
        pattern: Glob pattern for node names (e.g. "box*", "*merge*").
        node_type: Filter by node type name (e.g. "box", "null").
        context: Filter by node category name (e.g. "Sop", "Object").
        inside: Root path to search within.
    """
    root = _get_node(inside)
    all_nodes = root.allSubChildren()

    _MAX_RESULTS = 500
    results = []
    for node in all_nodes:
        # Filter by name pattern
        if pattern is not None:
            import fnmatch
            if not fnmatch.fnmatch(node.name(), pattern):
                continue

        # Filter by type
        if node_type is not None:
            if node.type().name() != node_type:
                continue

        # Filter by category/context
        if context is not None:
            if node.type().category().name() != context:
                continue

        results.append(_node_summary(node))
        if len(results) >= _MAX_RESULTS:
            break

    return {
        "count": len(results),
        "truncated": len(results) >= _MAX_RESULTS,
        "nodes": results,
    }


###### nodes.list_node_types

def list_node_types(
    context: str,
    filter: str = None,
    limit: int = 200,
    **_,
) -> dict:
    """List available node types in a given context category.

    Args:
        context: Category name, e.g. "Sop", "Lop", "Dop", "Top",
                 "Cop2", "Object", "Driver".
        filter: Optional substring to filter by type name or label
                (case-insensitive). Use this to avoid dumping all types.
        limit: Maximum number of types to return (default 200).
    """
    categories = hou.nodeTypeCategories()
    category = categories.get(context)
    if category is None:
        available = sorted(categories.keys())
        raise ValueError(
            f"Unknown node type category: '{context}'. "
            f"Available categories: {available}"
        )

    types_dict = category.nodeTypes()
    type_list = []
    for type_name, node_type in sorted(types_dict.items()):
        # Skip hidden/deprecated types
        try:
            if node_type.hidden():
                continue
        except Exception:
            pass
        type_list.append({
            "name": type_name,
            "label": node_type.description(),
        })

    if filter:
        f = filter.lower()
        type_list = [
            t for t in type_list
            if f in t["name"].lower() or f in t["label"].lower()
        ]

    total = len(type_list)
    type_list = type_list[:limit]
    return {
        "context": context,
        "total_count": total,
        "returned_count": len(type_list),
        "truncated": total > limit,
        "types": type_list,
    }


###### nodes.connect_nodes

def connect_nodes(
    source_path: str,
    dest_path: str,
    output_index: int = 0,
    input_index: int = 0,
) -> dict:
    """Wire two nodes together.

    Args:
        source_path: Path to the source (upstream) node.
        dest_path: Path to the destination (downstream) node.
        output_index: Output connector index on the source node.
        input_index: Input connector index on the destination node.
    """
    source = _get_node(source_path)
    dest = _get_node(dest_path)

    dest.setInput(input_index, source, output_index)

    _focus_network_editor(dest)

    return {
        "success": True,
        "source_path": source.path(),
        "dest_path": dest.path(),
        "output_index": output_index,
        "input_index": input_index,
    }


###### nodes.connect_nodes_batch

def connect_nodes_batch(
    connections: list,
) -> dict:
    """Wire multiple node pairs in a single call.

    Args:
        connections: List of dicts, each with keys:
            source_path, dest_path, output_index (default 0), input_index (default 0).
    """
    results = []
    errors = []

    last_dest = None
    for conn in connections:
        src_path = conn["source_path"]
        dst_path = conn["dest_path"]
        out_idx = int(conn.get("output_index", 0))
        in_idx = int(conn.get("input_index", 0))
        try:
            source = _get_node(src_path)
            dest = _get_node(dst_path)
            dest.setInput(in_idx, source, out_idx)
            last_dest = dest
            results.append({
                "source_path": source.path(),
                "dest_path": dest.path(),
                "output_index": out_idx,
                "input_index": in_idx,
            })
        except Exception as exc:
            errors.append({
                "source_path": src_path,
                "dest_path": dst_path,
                "error": str(exc),
            })

    if last_dest is not None:
        _focus_network_editor(last_dest)

    return {
        "success": len(errors) == 0,
        "connected": results,
        "errors": errors,
    }


###### nodes.disconnect_node

def disconnect_node(
    node_path: str,
    input_index: int = None,
    disconnect_all: bool = False,
) -> dict:
    """Disconnect one or all inputs of a node.

    Args:
        node_path: Path to the node whose inputs to disconnect.
        input_index: Specific input index to disconnect. Ignored if disconnect_all is True.
        disconnect_all: If True, disconnect all inputs.
    """
    node = _get_node(node_path)
    disconnected = []

    if disconnect_all:
        for i in range(len(node.inputs())):
            if node.inputs()[i] is not None:
                node.setInput(i, None)
                disconnected.append(i)
    elif input_index is not None:
        current_inputs = node.inputs()
        if input_index < len(current_inputs) and current_inputs[input_index] is not None:
            node.setInput(input_index, None)
            disconnected.append(input_index)
        else:
            raise ValueError(
                f"Input index {input_index} is out of range or already disconnected "
                f"on node {node_path}."
            )
    else:
        raise ValueError("Provide either input_index or set disconnect_all=True.")

    return {
        "success": True,
        "node_path": node_path,
        "disconnected_inputs": disconnected,
    }


###### nodes.reorder_inputs

def reorder_inputs(node_path: str, new_order: list) -> dict:
    """Reorder the input connections of a node.

    Args:
        node_path: Path to the node.
        new_order: List of integers representing the new input ordering.
                   For example, [1, 0] swaps the first two inputs.
    """
    node = _get_node(node_path)
    current_inputs = list(node.inputs())

    if len(new_order) > len(current_inputs):
        raise ValueError(
            f"new_order has {len(new_order)} entries but node only has "
            f"{len(current_inputs)} inputs."
        )

    # Disconnect all first
    for i in range(len(current_inputs)):
        node.setInput(i, None)

    # Reconnect in the new order
    for new_idx, old_idx in enumerate(new_order):
        if old_idx < len(current_inputs) and current_inputs[old_idx] is not None:
            node.setInput(new_idx, current_inputs[old_idx])

    return {
        "success": True,
        "node_path": node_path,
        "new_order": new_order,
    }


###### nodes.set_node_flags

def set_node_flags(
    node_path: str,
    display: bool = None,
    render: bool = None,
    bypass: bool = None,
    template: bool = None,
    lock: bool = None,
) -> dict:
    """Set one or more flags on a node.

    Args:
        node_path: Path to the node.
        display: Set the display flag.
        render: Set the render flag.
        bypass: Set the bypass flag.
        template: Set the template flag.
        lock: Set the hard-lock flag.
    """
    node = _get_node(node_path)
    changed = {}

    if display is not None:
        try:
            node.setDisplayFlag(display)
            changed["display"] = display
        except hou.OperationFailed:
            pass  # Some node types don't support display flag

    if render is not None:
        try:
            node.setRenderFlag(render)
            changed["render"] = render
        except hou.OperationFailed:
            pass

    if bypass is not None:
        try:
            node.bypass(bypass)
            changed["bypass"] = bypass
        except hou.OperationFailed:
            pass

    if template is not None:
        try:
            node.setTemplateFlag(template)
            changed["template"] = template
        except hou.OperationFailed:
            pass

    if lock is not None:
        try:
            node.setHardLocked(lock)
            changed["lock"] = lock
        except hou.OperationFailed:
            pass

    if not changed:
        raise ValueError(
            "No flags were changed. Either no flags were specified or "
            "the node does not support the requested flags."
        )

    if changed.get("display"):
        _focus_network_editor(node)

    return {
        "success": True,
        "node_path": node_path,
        "changed_flags": changed,
    }


###### nodes.layout_children

def layout_children(parent_path: str, spacing: float = None) -> dict:
    """Auto-layout the children of a network node.

    Args:
        parent_path: Path to the parent network.
        spacing: Optional spacing multiplier between nodes.
    """
    if not auto_layout_enabled():
        return {
            "success": False,
            "skipped": True,
            "reason": "Auto-layout is disabled (FXHOUDINIMCP_AUTO_LAYOUT=0).",
        }

    parent = _get_node(parent_path)

    if spacing is not None:
        parent.layoutChildren(horizontal_spacing=spacing, vertical_spacing=spacing)
    else:
        parent.layoutChildren()

    children_paths = [c.path() for c in parent.children()]

    return {
        "success": True,
        "parent_path": parent_path,
        "laid_out_count": len(children_paths),
    }


###### nodes.set_node_position

def set_node_position(node_path: str, x: float, y: float) -> dict:
    """Set the position of a node in the network editor.

    Args:
        node_path: Path to the node.
        x: Horizontal position.
        y: Vertical position.
    """
    node = _get_node(node_path)
    node.setPosition(hou.Vector2(x, y))

    return {
        "success": True,
        "node_path": node_path,
        "position": [x, y],
    }


###### nodes.set_node_color

def set_node_color(node_path: str, r: float, g: float, b: float) -> dict:
    """Set the color of a node in the network editor.

    Args:
        node_path: Path to the node.
        r: Red component (0.0 to 1.0).
        g: Green component (0.0 to 1.0).
        b: Blue component (0.0 to 1.0).
    """
    node = _get_node(node_path)
    color = hou.Color((r, g, b))
    node.setColor(color)

    return {
        "success": True,
        "node_path": node_path,
        "color": [r, g, b],
    }


###### Registration

register_handler("nodes.create_node", create_node)
register_handler("nodes.delete_node", delete_node)
register_handler("nodes.rename_node", rename_node)
register_handler("nodes.classify_node_for_rename", classify_node_for_rename)
register_handler("nodes.bulk_rename_nodes", bulk_rename_nodes)
register_handler("nodes.copy_node", copy_node)
register_handler("nodes.move_node", move_node)
register_handler("nodes.get_node_info", get_node_info)
register_handler("nodes.list_children", list_children)
register_handler("nodes.find_nodes", find_nodes)
register_handler("nodes.list_node_types", list_node_types)
register_handler("nodes.connect_nodes", connect_nodes)
register_handler("nodes.connect_nodes_batch", connect_nodes_batch)
register_handler("nodes.disconnect_node", disconnect_node)
register_handler("nodes.reorder_inputs", reorder_inputs)
register_handler("nodes.set_node_flags", set_node_flags)
register_handler("nodes.layout_children", layout_children)
register_handler("nodes.set_node_position", set_node_position)
register_handler("nodes.set_node_color", set_node_color)
