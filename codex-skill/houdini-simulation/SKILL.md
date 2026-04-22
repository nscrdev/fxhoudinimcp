---
name: houdini-simulation
description: Use when the user wants to set up or refine a Houdini simulation, including Pyro, FLIP, RBD, Vellum, POP, whitewater, MPM, ripple, or shallow water workflows. Triggers include "make this explode", "set up a pyro sim", "do a FLIP tank", "create cloth", "fracture and sim", "vellum cloth", "sim smoke", or any request to build Houdini sim networks and sources.
---

# Houdini Simulation

Use this skill for dynamics and solver setup with the `fxhoudini` MCP server.

If the Houdini MCP tools are unavailable, say so briefly and continue only with planning or recommendations.

## Core behavior

- Prefer the high-level workflow tools first:
  `setup_pyro_sim`, `setup_rbd_sim`, `setup_flip_sim`, `setup_vellum_sim`.
- Build source geometry with SOP nodes, not ad-hoc wrangles.
- Use solver-native nodes and parameters before reaching for Python or VEX.

## Workflow

1. Call `get_scene_info`.
2. Build or inspect the source geometry in SOPs.
3. Use the appropriate workflow tool when it matches the task.
4. If no workflow tool fits, build the DOP or SOP-level solver network manually.
5. Inspect state with `get_simulation_info`.
6. Advance or test with `step_simulation`.
7. Inspect problem objects with `get_dop_object`.
8. Tune parameters with `set_parameter`.

## Guardrails

- Prefer dedicated SOP/DOP nodes over wrangles for sourcing, fracturing, constraints, particle forces, or common sim setup.
- Before custom work, call `list_node_types` for the relevant context to confirm whether a native node already exists.
- Verify source geometry before simming with `get_geometry_info`.
- After major solver changes, use `reset_simulation` before retesting.

## Modern preferences

- Pyro:
  use the Pyro workflow tools and source nodes before wiring sparse pyro manually.
- FLIP:
  use FLIP source/container patterns and mesh results with `Particle Fluid Surface`.
- RBD:
  fracture and configure pieces with native RBD tools, and pack geometry before bullet-style setups.
- Vellum:
  use Vellum constraints and drape/solver tools instead of building cloth logic from scratch.

## Session hygiene

- Call `log_status` at major milestones.
- Call `set_current_network` before switching between SOP, DOP, or stage-level work.
- Call `layout_children` regularly so the network stays readable while the user watches.
