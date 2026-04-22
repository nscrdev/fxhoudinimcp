---
name: houdini-procedural-modeling
description: Use when the user wants to build procedural geometry in Houdini SOPs, including modeling props, terrain, scattering, copy-to-points setups, boolean modeling, UV prep, or visible node-based geometry networks. Triggers include requests like "build a procedural terrain", "make a rock generator", "scatter trees", "model this in SOPs", "make an AC unit", or any request where a Houdini node chain should be built instead of writing VEX first.
---

# Houdini Procedural Modeling

Use this skill for SOP-focused geometry construction with the `fxhoudini` MCP server.

If the Houdini MCP tools are unavailable, say so briefly and continue only with planning or guidance.

## Core behavior

- Prefer visible SOP node chains over VEX.
- Treat wrangles as a last resort for logic no built-in SOP can express.
- Plan the node chain before creating nodes.
- Keep the network legible while working: update the current network, log major steps, and lay out nodes regularly.

## Workflow

1. Call `get_scene_info` to understand the current scene.
2. Create or choose the target geometry container in the requested context, usually `/obj`.
3. Plan the SOP chain in plain language before building it.
4. Build with native SOPs first:
   `Box`, `Sphere`, `Grid`, `Circle`, `PolyExtrude`, `PolyBevel`, `Boolean`, `Transform`, `Scatter`, `Copy to Points`, `Attribute Randomize`, `Fuse`, `Clean`, `Null`, `For-Each`, and related SOPs.
5. Set display/render flags on the intended output node.
6. Verify the result with `get_geometry_info`.

## Guardrails

- Before inventing a custom wrangle, call `list_node_types` with `context="Sop"` to confirm a native node does not already solve the problem.
- Do not use wrangles for common tasks such as creating primitives, scattering, deleting by group, randomizing attributes, booleans, extrusion, or copying.
- If you do create or edit VEX, immediately validate it with `validate_vex`.
- If something fails twice, switch strategies:
  inspect node errors, inspect geometry upstream, or use Python inspection tools instead of retrying blindly.

## Handy SOP patterns

- Hard-surface prop:
  base primitive -> bevel/extrude -> boolean cutouts -> scatter/copy details -> null output
- Terrain:
  grid -> mountain/noise -> scatter points -> copy instances -> null output
- Repeated assembly:
  create source module -> create points -> copy to points -> variation/randomization -> merge -> null output

## Session hygiene

- Call `log_status` at major milestones.
- Call `set_current_network` before building in a network.
- Call `layout_children` every few nodes so the graph stays readable.
