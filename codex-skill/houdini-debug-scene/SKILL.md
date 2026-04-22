---
name: houdini-debug-scene
description: Use when the user wants to debug a Houdini scene or network, including cooking errors, missing geometry, broken materials, bad references, simulation instability, empty outputs, or general "what is wrong with this scene" requests. Triggers include "debug this Houdini file", "nothing is showing", "the sim is exploding", "find the error nodes", "why is this empty", or "materials are not showing up".
---

# Houdini Debug Scene

Use this skill for structured Houdini troubleshooting with the `fxhoudini` MCP server.

If the Houdini MCP tools are unavailable, say so briefly and continue only with reasoning from the user's description.

## Core behavior

- Debug systematically, not by random retries.
- Start broad, then narrow to the failing node, input, parameter, or context.
- Check upstream dependencies before patching downstream nodes.

## Workflow

1. Call `get_scene_info`.
2. Call `find_error_nodes`.
3. For each suspect node, call `get_node_info`.
4. Inspect parameter schemas and values where needed.
5. Inspect geometry, USD stage, or simulation state depending on the failure mode.
6. Use bypass flags strategically to isolate the failing part of the network.
7. Check broken expressions or bad references explicitly.

## Common failure modes

- Missing or wrong inputs
- Bad parameter values
- Upstream cooking failures
- Empty geometry after filtering or deletion
- Simulation instability from timestep, collisions, or source issues
- Material assignment or viewport renderer mismatches
- USD composition problems from layer stacking, references, payloads, or variants
- Invalid node type names or stale assumptions about available nodes

## Guardrails

- Do not keep re-running the same inspection hoping for a different answer.
- When VEX is involved, validate it directly instead of inferring from downstream symptoms.
- For simulation issues, inspect object state and reset intentionally after major changes.
- For stage issues, use USD inspection tools instead of guessing.

## Session hygiene

- Call `log_status` for each major diagnosis step.
- Call `set_current_network` when changing debugging context.
- Call `layout_children` after cleanup or rewiring so the repaired graph remains readable.
