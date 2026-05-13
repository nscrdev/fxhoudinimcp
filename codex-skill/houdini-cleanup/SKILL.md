---
name: houdini-cleanup
description: Use when the user wants to clean up a Houdini node graph for handoff by renaming nodes to descriptive Houdini-safe names without changing behavior. Triggers include Houdini cleanup, clean up this graph, rename nodes, make the network readable, descriptive node names, handoff-ready graph, organize this network, or requests to rename nodes in /obj, SOPs, /stage, LOPs, TOPs, or subnetworks.
---

# Houdini Cleanup

Use this skill for Houdini graph cleanup with the `fxhoudini` MCP server.
The task is rename-only cleanup: make the node graph readable for the next person without changing behavior.

If the Houdini MCP tools are unavailable, say so briefly and continue only with a rename plan from the user's description.

## Core Behavior

- Rename nodes by their role in the graph, not by generic type suffixes.
- Preserve behavior: no new nodes, rewiring, parameter edits, bypass changes, or subnet Comment fields unless the user explicitly asks.
- Prefer a focused top-level pass. Rename subnet internals only when the user asks for nested cleanup.
- Read wiring, node types, labels, and meaningful parameters before choosing names.
- For wrangles, inspect the relevant VEX snippet when available so the name reflects what the code actually does.

## Workflow

1. Identify the target network path from the user's request. If it is missing, inspect the current scene/network and ask only if the target is still ambiguous.
2. Call `log_status` with a short message such as `Houdini cleanup: renaming nodes in /obj/geo1`.
3. Call `set_current_network` on the parent network before inspecting or renaming.
4. Call `get_network_overview` for the target network. Use depth `1` for `top_level_only`; use depth `2` or `3` only when nested subnet cleanup is in scope.
5. Read `ascii_flow`, child node names, node types, and key parameters. Inspect individual nodes with `get_node_info` where the overview is not enough.
6. Infer proposed names from graph role and data flow.
7. Call `rename_node` for each change. Do not use `execute_python` for renaming.
8. Optionally scan parameters in the target network for channel expressions or `op:` paths that reference old base node names; report any hits instead of silently editing them.
9. Call `layout_children` on the parent network after a batch of renames if the graph needs it.
10. Reply with a concise old-to-new rename table and note anything intentionally left unchanged.

## Naming Rules

- Use `snake_case` Houdini-safe identifiers.
- Make names specific to graph role, such as `curveu_project_on_path`, not `attribwrangle7`.
- Use stage distinctions when roles repeat, such as `profile_to_polyline` and `closed_curve_to_polyline`.
- Prefer `OUT` for the final output null/output node when it is the subnet exit.
- Keep names stable and practical. Avoid clever names, comments embedded in names, and names that describe implementation details instead of purpose.
- Do not rename a node if the current name is already descriptive and stable.

## Scope Rules

- Default scope is direct children of the target network.
- Use nested cleanup only when the user asks for internals of subnetworks to be renamed too.
- Treat locked HDAs and third-party asset internals as read-only unless the user explicitly requests asset editing.
- For LOPs, name by USD stage operation: `reference_city_set`, `assign_concrete_material`, `karma_render_settings`.
- For SOPs, name by geometry operation or data product: `scatter_tree_points`, `build_wall_panels`, `OUT`.
- For TOPs, name by work-item purpose: `wedge_material_variants`, `render_usd_frames`, `partition_by_asset`.

## Network Housekeeping

- Call `log_status` at the start of every major step so the user can see progress in Houdini's status bar.
- Call `set_current_network` before inspecting or renaming nodes in a network.
- Call `layout_children` after cleanup batches when layout would make the graph easier to review.
