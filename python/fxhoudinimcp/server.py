"""FastMCP server definition for FXHoudini-MCP."""

from __future__ import annotations

# Built-in
import logging
import os
from contextlib import asynccontextmanager

# Third-party
from mcp.server.fastmcp import FastMCP

# Internal
from fxhoudinimcp.bridge import HoudiniBridge

logger = logging.getLogger(__name__)


def _get_bridge(ctx) -> HoudiniBridge:
    """Extract the HoudiniBridge from the MCP context."""
    return ctx.request_context.lifespan_context["bridge"]


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Manage the Houdini bridge connection lifecycle."""
    host = os.getenv("HOUDINI_HOST", "localhost")
    port = int(os.getenv("HOUDINI_PORT", "8100"))

    bridge = HoudiniBridge(host=host, port=port)

    try:
        info = await bridge.health_check()
        logger.info(
            "Connected to Houdini %s", info.get("houdini_version", "unknown")
        )
    except Exception as e:
        logger.warning("Cannot reach Houdini at startup: %s", e)
        logger.warning("Tools will attempt to connect on first use.")

    try:
        yield {"bridge": bridge}
    finally:
        await bridge.close()


mcp = FastMCP(
    name="FXHoudini",
    instructions=(
        "MCP server for SideFX Houdini with 156 tools across 20 categories.\n\n"
        "IMPORTANT WORKFLOW RULES:\n"
        "- For procedural geometry, ALWAYS prefer VEX wrangles (create_wrangle + "
        "set_wrangle_code) and native SOP nodes over execute_python. VEX is "
        "Houdini's native language for geometry manipulation and runs orders of "
        "magnitude faster than Python SOPs.\n"
        "- Use create_node to build SOP networks with standard nodes (box, grid, "
        "copy, transform, polyextrude, boolean, etc.) wired together.\n"
        "- Use create_wrangle for custom attribute logic, point/prim manipulation, "
        "and procedural generation. Write VEX code, not Python.\n"
        "- Reserve execute_python ONLY for scene-level scripting (creating node "
        "networks, setting up the scene, batch operations) where no dedicated "
        "tool exists.\n"
        "- Build node networks by creating nodes and connecting them, not by "
        "writing a single large Python script.\n"
        "- NEVER hardcode tweakable values in VEX or Python code. Instead, "
        "create a controller null (e.g. 'CTRL') with spare parameters "
        "(create_spare_parameter) for user-facing controls like counts, sizes, "
        "seeds, densities, and proportions. In VEX, read them with ch()/chf()/"
        "chi()/chs() pointing to the controller. This lets the user adjust "
        "the setup interactively without editing code.\n"
        "- Call layout_children regularly while building networks (every 5-10 "
        "nodes), not just at the end. This keeps the graph tidy as you work.\n"
        "- When a workflow tool exists (setup_pyro_sim, setup_rbd_sim, etc.), "
        "use it instead of building from scratch."
    ),
    lifespan=lifespan,
)
