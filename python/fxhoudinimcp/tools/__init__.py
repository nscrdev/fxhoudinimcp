"""MCP tool modules for FXHoudini-MCP.

Importing this package registers all MCP tools with the FastMCP server.
Each submodule uses the ``@mcp.tool()`` decorator at import time.
"""

from __future__ import annotations

# Internal
from . import scene  # noqa: F401
from . import nodes  # noqa: F401
from . import parameters  # noqa: F401
from . import code  # noqa: F401
from . import dops  # noqa: F401
from . import animation  # noqa: F401
from . import rendering  # noqa: F401
from . import viewport  # noqa: F401
from . import tops  # noqa: F401
from . import cops  # noqa: F401
from . import hda  # noqa: F401
from . import vex  # noqa: F401
from . import geometry  # noqa: F401
from . import lops  # noqa: F401
from . import context  # noqa: F401
from . import workflows  # noqa: F401
from . import materials  # noqa: F401
from . import chops  # noqa: F401
from . import cache  # noqa: F401
from . import takes  # noqa: F401
