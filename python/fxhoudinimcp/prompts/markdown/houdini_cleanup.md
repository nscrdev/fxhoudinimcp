You are doing **Houdini graph cleanup**: rename nodes the user has selected so the next person can read the network. Rename-only — no behavior changes, no new nodes, no rewiring, no parameter edits, no subnet Comment fields.

**User-supplied target hint (optional):** `{network_path}`

This skill is **selection-driven**. The user's current node selection is the definitive list of nodes to rename. The skill does not search the scene, does not pick targets heuristically, and does not second-guess the selection by HDA membership or container detection.

## Hard rules (must follow — non-negotiable)

### Rule 1 — Selection IS the contract

The set of nodes you rename is exactly the set of nodes the user selected — nothing more, nothing less. If the user selected a SOP Create wrapper, you rename it. If the user selected a node inside an unlocked Component Geometry's `sopnet`, you rename it. The user is the authority on intent; the skill's job is to execute, not to re-litigate.

The only renames you refuse are ones that the Houdini engine itself cannot execute — those are returned as `blocked` entries by `bulk_rename_nodes(..., trust_selection=True)`. See Rule 4.

### Rule 2 — Empty selection means stop and ask

If `get_selection` returns no nodes, stop and ask the user to select the nodes they want renamed. Do not call `get_scene_summary`, `get_current_network_path`, or `get_network_overview` to guess. Do not propose candidate networks. Just ask.

### Rule 3 — One network at a time (mixed-parent refusal)

Cleanup touches a single network per run. If the selected nodes do not all share the same immediate parent (e.g. one in `/stage/foo` and one in `/obj/geo1`), refuse the run and ask the user to narrow the selection to one network. Detect this **before** calling `bulk_rename_nodes` — compute the parent path for every selected node and confirm they're equal. ``bulk_rename_nodes`` itself will also refuse with a single ``mixed_parents`` blocker, but treat that as a backstop, not the primary path.

### Rule 4 — Always use `bulk_rename_nodes` with `trust_selection=True`

For every cleanup run, call:

```
bulk_rename_nodes(
    plan=plan,
    enforce_safety=True,
    trust_selection=True,
    scan_cascades=True,
    dry_run=True,         # first call
    network_scope=<the shared parent path>,
)
```

`trust_selection=True` silently downgrades the `is_container_hda_wrapper` and `inside_hda_contents` verdicts to a no-op (no `blocked` entry, no warning). The remaining verdicts — `inside_locked_hda`, `not_editable`, `is_root_or_manager`, `node_not_found` — stay as hard blockers because they reflect Houdini state that would make the rename fail at the engine level.

Never call `rename_node` for cleanup; always go through `bulk_rename_nodes`.

### Rule 5 — Show the plan, get approval, then apply

After the dry run, present the user with: the old → new rename table, any cascade warnings (`ch()` / `chs()` / `op:` / raw path references to old names that will dangle), and any hard blockers. Wait for explicit approval. Then call again with `dry_run=False` and the same other arguments.

If the dry run reports `blocked`, you must surface it. Do not silently drop blocked entries and proceed with the rest. Either fix the plan (e.g. rename collisions, choose different names) or stop and report.

## Workflow

1. **`log_status`** — short message, e.g. `Houdini cleanup: reading selection`.
2. **Get the selection.** Call `get_selection`. If `nodes` is empty → stop and ask the user to select the nodes they want renamed (Rule 2).
3. **Mixed-parent check.** Compute `parent_path` for every selected node (everything before the last `/` in `node_path`). If they are not all identical → stop and ask the user to narrow the selection to one network (Rule 3). List the distinct parents in your message so the user can see what spanned what.
4. **Inspect the network for naming context.** Call `set_current_network` on the shared parent so the user can see the work. Call `get_network_overview` with `path=<shared parent>` and `depth=1` to read `ascii_flow`, types, and connections. Use `get_node_info` and `get_parameter` for ambiguous cases. For wrangles, read `vexsnippet` on the inner `attribvop1` so the name reflects what the code actually does.
5. **Propose names.** For each selected node, infer a `snake_case` Houdini-safe identifier from wiring, type, and (for wrangles) the VEX snippet. See "Naming rules" below.
6. **Dry-run pre-flight.** Call `bulk_rename_nodes(plan, enforce_safety=True, trust_selection=True, scan_cascades=True, dry_run=True, network_scope=<shared parent>)`. Read `blocked`, `cascade_warnings`, `cascade_truncated`.
7. **Present the plan to the user.** Include the old → new table, every `cascade_warning` (referrer path, parameter, matched expression, old → new), and any `blocked` entries with their `reason`. Always require confirmation when:
   - `cascade_warnings` is non-empty.
   - The renamed-set is large (>10 nodes).
   - The shared parent is under `/stage` (USD prim-path risk on any LOP whose default uses `$OS`).
   Otherwise you may proceed directly. If `blocked` is non-empty, stop and report — do not try to apply a partial plan.
8. **Apply.** On user approval, call `bulk_rename_nodes` again with `dry_run=False` (same other args). The response's `applied: True` plus per-entry `succeeded` confirms the batch landed; `applied: False` with a populated `rollback` block means execution failed and the scene was rolled back to its prior state — surface the structured failure to the user.
9. **Optional `layout_children`** only if the user explicitly asked for layout/cleanup that includes layout. Preserve existing node positions otherwise.
10. **Reply.** A concise old → new rename table, any blocked entries (with `reason`), and any cascade warnings the user should manually inspect. The skill **does not** rewrite stale references.

## Naming rules

- `snake_case`, Houdini-safe identifiers (`^[A-Za-z_][A-Za-z0-9_]*$`), unique within the parent.
- Name by **role in the graph**, not by node type alone (`attribwrangle7` → `curveu_project_on_path`, not `attribwrangle_a`).
- Prefer **`OUT`** for the final output / null when it is the network's exit.
- If two nodes share a role, distinguish by stage (e.g. `profile_to_polyline` vs `closed_curve_to_polyline`).
- For LOPs, name by USD stage operation (`reference_city_set`, `assign_concrete_material`, `karma_render_settings`).
- For SOPs, name by geometry operation or data product (`scatter_tree_points`, `build_wall_panels`, `OUT`).
- For TOPs, name by work-item purpose (`wedge_material_variants`, `render_usd_frames`, `partition_by_asset`).
- Leave names alone when the current name is already descriptive and stable — but if the user selected it, presume they want it renamed and propose something better.

## What this skill does NOT do

- Does not rename anything the user did not select.
- Does not auto-pick a target network (no `get_scene_summary`, no `get_current_network_path`, no candidate lists).
- Does not edit parameters, expressions, wiring, flags, comments, or HDA definitions.
- Does not rewrite stale `ch()` / `op:` / `soppath` expressions — only **reports** them via the cascade scan.
- Does not silently drop entries from the rename plan; if `bulk_rename_nodes` returns blockers, surface them.
- Does not span multiple networks in one run; refuse mixed-parent selections (Rule 3).

For natural-language triggering in Cursor, the user may also use the **houdini-cleanup** skill at `~/.cursor/skills/houdini-cleanup/SKILL.md`. For Codex, the same content lives at `codex-skill/houdini-cleanup/SKILL.md` in the fxhoudinimcp repo.

{network_housekeeping}
