"""MCP prompt templates for common Houdini workflows.

These prompts guide AI assistants through multi-step Houdini tasks.
"""

from __future__ import annotations

# Internal
from fxhoudinimcp._loader import load_markdown
from fxhoudinimcp.server import mcp


@mcp.prompt()
def procedural_modeling_workflow(
    description: str,
    output_context: str = "/obj",
) -> str:
    """Guide for building a procedural modeling network in SOPs.

    Args:
        description: What geometry to create (e.g. "a rocky terrain with scattered trees")
        output_context: Where to create the geo container
    """
    return load_markdown(
        "procedural_modeling.md",
        description=description,
        output_context=output_context,
    )


@mcp.prompt()
def usd_scene_assembly(
    scene_description: str,
) -> str:
    """Guide for building a USD scene in Houdini's LOPs/Solaris.

    Args:
        scene_description: Description of the USD scene to build
    """
    return load_markdown(
        "usd_scene_assembly.md",
        scene_description=scene_description,
    )


@mcp.prompt()
def simulation_setup(
    sim_type: str,
    description: str = "",
) -> str:
    """Guide for setting up a dynamics simulation.

    Args:
        sim_type: Type of simulation (pyro, flip, rbd, vellum, pop)
        description: Additional context about the simulation
    """
    return load_markdown(
        "simulation_setup.md",
        sim_type=sim_type,
        description=description or f"Create a {sim_type} simulation",
    )


@mcp.prompt()
def pdg_pipeline(
    task_description: str,
) -> str:
    """Guide for building a PDG/TOPs pipeline.

    Args:
        task_description: What the pipeline should accomplish
    """
    return load_markdown(
        "pdg_pipeline.md",
        task_description=task_description,
    )


@mcp.prompt()
def hda_development(
    asset_description: str,
    context: str = "Sop",
) -> str:
    """Guide for creating a Houdini Digital Asset.

    Args:
        asset_description: What the HDA should do
        context: Node context for the HDA (Sop, Lop, Object, etc.)
    """
    return load_markdown(
        "hda_development.md",
        asset_description=asset_description,
        context=context,
    )


@mcp.prompt()
def debug_scene(
    problem_description: str = "general issues",
) -> str:
    """Systematic approach to debugging a Houdini scene.

    Args:
        problem_description: What problem the user is experiencing
    """
    return load_markdown(
        "debug_scene.md",
        problem_description=problem_description,
    )
