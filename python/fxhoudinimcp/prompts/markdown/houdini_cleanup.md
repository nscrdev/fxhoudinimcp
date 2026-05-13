You are doing **Houdini graph cleanup**: rename nodes so the next person can read the network (handoff-ready names only — no behavior changes, no new nodes, no subnet Comment fields unless the user asks).

**Target network:** `{network_path}`  
**Scope:** `{scope}` — use `top_level_only` to rename only direct children of that network; use `include_subnets` only if the user wants internals of nested subnetworks renamed too (can be large).

## Workflow

1. **log_status** — e.g. `Houdini cleanup: renaming nodes in {network_path}`.
2. **get_network_overview** — `path={network_path}`, `depth` 2–3 if subnets are in scope; read `ascii_flow` and node list.
3. **Infer names** from wiring, node type, and (for wrangles) **vexsnippet** on the inner `attribvop1` so names match what the node actually does.
4. **rename_node** for each change (`node_path`, `new_name`). Do **not** use `execute_python` to rename.
5. **Optional:** scan parameters on nodes in that network for **channel expressions** that still reference **old base node names**; report any hits so the user can fix `ch()` / `op:` paths.
6. Reply with a concise **old → new** rename table.

## Naming rules

- **snake_case**, Houdini-safe identifiers.
- Name by **role in the graph**, not generic type suffixes (`attribwrangle7` → something like `curveu_project_on_path`).
- Final output null/output node: prefer **`OUT`** when it is the subnet exit.
- If two nodes share a role, distinguish by stage (e.g. `profile_to_polyline` vs `closed_curve_to_polyline`).
- Default **top-level only**; subnet internals (e.g. inside Convert Line) are a **second pass** only on request.

## Optional

- **layout_children** on the parent if the graph is messy and the user wants it.

For natural-language triggering in Cursor, the user may also use the **houdini-cleanup** skill at `~/.cursor/skills/houdini-cleanup/SKILL.md`.

{network_housekeeping}
