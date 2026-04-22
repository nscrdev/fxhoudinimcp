---
name: houdini-pdg
description: Use when the user wants to build or debug a Houdini PDG/TOPs pipeline, including wedges, batch renders, file processing graphs, HDA Processor flows, ROP Fetch orchestration, partitioning, FFmpeg encoding, cache post-processing, or distributed task graphs. Triggers include PDG, TOPs, /tasks, wedge studies, batch export, render pipeline, work items, partitioning, or automation across many files or frames.
---

# Houdini PDG

Use this skill for TOPs and PDG pipeline work with the `fxhoudini` MCP server.

If the Houdini MCP tools are unavailable, say so briefly and continue only with pipeline planning.

## Core behavior

- Prefer dedicated TOP nodes over custom Python processors whenever possible.
- Plan the dependency graph before creating nodes.
- Use generation and inspection tools before blindly cooking large graphs.

## Workflow

1. Switch to `/tasks` with `set_current_network`.
2. Plan the dependency graph in plain language.
3. Create the required TOP nodes.
4. Wire the graph cleanly.
5. Preview work items with `generate_static_items`.
6. Inspect status with `get_work_item_states` and `get_work_item_info`.
7. Cook intentionally with `cook_top_node`.

## Guardrails

- Before using a Python Processor or Python Script, call `list_node_types` with `context="Top"` and check whether a native TOP node exists.
- Prefer native nodes for file discovery, file copying, partitioning, CSV/JSON I/O, ROP execution, FFmpeg encoding, and wedge generation.
- Use synchronization nodes like partitioners or wait-for-all patterns instead of ad-hoc merge assumptions.

## Common patterns

- Wedge study:
  `wedge -> rop fetch -> wait/partition -> downstream post`
- Batch export:
  `file pattern -> HDA/ROP processing -> aggregation`
- Post-processing:
  `file pattern -> partition -> compositing/encoding`

## Session hygiene

- Call `log_status` at major milestones.
- Call `set_current_network` before building or inspecting `/tasks`.
- Call `layout_children` regularly so the task graph stays readable.
