---
name: houdini-hda
description: Use when the user wants to create, package, or refine a Houdini Digital Asset, including turning a subnet into an HDA, promoting parameters, organizing tabs, inspecting asset sections, updating definitions, or adding help content. Triggers include requests like "turn this into an HDA", "make this reusable", "promote these parms", "package this as a digital asset", or "update the HDA definition".
---

# Houdini HDA Development

Use this skill for Houdini Digital Asset creation and refinement with the `fxhoudini` MCP server.

If the Houdini MCP tools are unavailable, say so briefly and continue only with planning or HDA design guidance.

## Core behavior

- Build clean subnet logic first, then package it.
- Prefer visible internal node networks over hidden wrangle-heavy logic.
- Promote parameters in batches and group them into sensible folders/tabs.

## Workflow

1. Build or inspect the internal subnet network.
2. Verify behavior with geometry or stage inspection tools before packaging.
3. Promote important controls with `create_spare_parameters`.
4. Convert the subnet with `create_hda`.
5. Inspect the definition with `get_hda_info` and `get_hda_sections`.
6. Add or refine help/documentation with `set_hda_section_content`.
7. Use `update_hda` after later changes.

## Guardrails

- Keep the internal network readable with labeled nulls and sensible structure.
- Avoid hardcoded paths and magic numbers; expose them as parameters.
- Use `list_node_types` if you need to avoid naming collisions.
- Favor SOP node chains and native constructs over VEX when the asset logic can stay visible and artist-friendly.

## Good HDA habits

- Clear input/output nodes
- Organized parameter tabs
- Reusable defaults
- Internal network that can still be debugged later
- Help content that explains what the asset expects and produces

## Session hygiene

- Call `log_status` at major milestones.
- Call `set_current_network` before editing the subnet or asset context.
- Call `layout_children` frequently so the internal network remains maintainable.
