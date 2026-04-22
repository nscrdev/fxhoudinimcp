---
name: houdini-usd-solaris
description: Use when the user wants to build or edit a USD scene in Houdini Solaris/LOPs, including stage assembly, references, payloads, cameras, lights, material libraries, assign material workflows, Karma lookdev, or render settings. Triggers include requests mentioning Solaris, LOPs, USD, /stage, Karma lookdev, Material Library, dome lights, scene assembly, or USD-native material assignment.
---

# Houdini USD Solaris

Use this skill for `/stage` and USD-native scene work with the `fxhoudini` MCP server.

If the Houdini MCP tools are unavailable, say so briefly and continue only with planning or USD guidance.

## Core behavior

- Work in `/stage` and think in USD layers and prims.
- Prefer viewport-first lookdev:
  use Hydra viewport rendering and screenshots before disk renders.
- Create materials in `materiallibrary` LOPs, not in `/mat` for Solaris workflows.

## Workflow

1. Call `get_scene_info`.
2. Switch to `/stage` with `set_current_network`.
3. Set the viewport renderer for lookdev, such as Karma CPU or Storm.
4. Build the LOP chain with native nodes like `reference`, `sublayer`, `xform`, `camera`, `light`, `materiallibrary`, `assignmaterial`, and render-setting nodes.
5. Wire the chain cleanly.
6. Inspect visually with `capture_screenshot`.
7. Verify stage structure with `get_stage_info`, `list_usd_prims`, and `get_usd_materials`.

## Guardrails

- Do not use Python LOPs for work that standard LOP nodes already cover.
- Do not render to disk just to preview materials or lighting.
- Use `get_parameter_schema` before guessing parameter names on material or light nodes.
- Use USD inspection tools like `get_usd_layers` and `get_usd_composition` when composition issues appear.

## Common patterns

- Scene assembly:
  references/payloads -> transforms -> materials -> lighting -> render settings
- Lookdev:
  viewport renderer -> material library -> assign material -> screenshot validation
- Lighting:
  dome/distant/rect/sphere lights or a light rig preset, then validate in viewport

## Session hygiene

- Call `log_status` at major milestones.
- Call `set_current_network` before stage edits.
- Call `layout_children` regularly so the stage graph stays understandable.
