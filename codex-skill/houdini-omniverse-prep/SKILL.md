---
name: houdini-omniverse-prep
description: Use when the user is preparing a Houdini scene for export to NVIDIA Omniverse (USD Composer, USD Explorer, Isaac Sim, etc.) or troubleshooting Omniverse ingest issues. Triggers include requests mentioning Omniverse, USD Composer, Isaac Sim, "Cannot find node" or "Ill-formed SdfPath" errors in Composer's log, MaterialX rendering wrong in Omniverse, dual-surface or auto-generated UsdPreviewSurface problems, empty displacement chains, or pre-flight validation of a Solaris MaterialX network before USD ROP export.
---

# Houdini Omniverse Prep

Use this skill when prepping a Houdini Solaris/LOPs scene for ingest into NVIDIA Omniverse, or when debugging why a USD that cooks cleanly in Houdini renders broken materials in Composer/Isaac Sim.

If the Houdini MCP tools are unavailable, say so briefly and continue only with USD/log guidance.

## Core principle

**`find_error_nodes` is necessary but not sufficient.** Houdini will report a clean scene while still authoring USD that omni.materialx rejects. Always also verify what gets *authored* into the exported USD against what's *live* in the LOP network.

## Pre-flight checklist (run BEFORE every Omniverse export)

Run in order. Skip nothing.

1. **Houdini errors:** `find_error_nodes(root_path="/stage")`. Resolve any `error_count > 0`. Note warnings but they're usually fine.
2. **Disable preview-shader auto-gen** on every `materiallibrary` LOP. Check with `get_parameter_schema(node, filter="preview")`; the `genpreviewshaders` toggle defaults to `1` and silently authors a duplicate UsdPreviewSurface fallback shader plus a second `outputs:surface` connection on the Material — confuses omni.materialx. Fix with `set_parameter(node, "genpreviewshaders", 0)` (integer, not bool).
3. **Walk every MaterialX subnet for orphans.** For each `subnetconnector` inside the subnet, follow `inputs[]` upstream. An orphan is any node with empty `inputs: []` AND default-zero parameters — it'll export as an empty Shader prim and produce `Cannot find node: ''` / `Ill-formed SdfPath <>` in Composer. Fix by `disconnect_node` from the subnetconnector, `delete_node`, or wiring real inputs.
4. **Verify authored USD prims** with `find_usd_prims(materiallibrary_node, "/materials/**")`. Expected: one Material prim plus one Shader per active VOP node. No extras, no orphans.
5. **Confirm the Material's outputs.** Exactly one `outputs:mtlx:surface`, optionally `outputs:mtlx:displacement`/`volume` if those targets are real wired shaders. Never both `outputs:surface` and `outputs:mtlx:surface`.
6. **Cook the USD ROP and re-verify on disk** if needed. Houdini's `usdcat --flatten input.usd -o readable.usda` (under `<houdini_install>/bin/`) converts USDC to ASCII for grep-able inspection.

## Reading the Omniverse log

Many `[Warning]` lines are **proof of success**, not failure. Group by what they indicate:

- **Real errors that must be fixed:**
  - `[omni.materialx] Cannot find node: ''` → orphan in the network (steps 2/3)
  - `[omni.usd] Ill-formed SdfPath <>` → same root cause
  - `placeholder_attribute customData.default not found ... material:binding` → downstream symptom of the above
- **Cleanup noise (ignore):**
  - `[omni.fabric.plugin] getAttributeCount/getTypes/removePath called on non-existent path` → Composer cleaning up a prim that was removed in a re-export. *Good* sign — proves the new file no longer has it.
  - `Source: omni.materialx was already registered` → cosmetic double-registration
  - `gpu.foundation.plugin acquired ... N times` → NVIDIA-internal performance hint
- **Proof MaterialX is working (good):**
  - `[MDLC:COMPILER] C183 unused parameter 'transmission_*'`
  - `[MDLC:COMPILER] C350 unused let temporary 'c_box_filter_weights'` etc.
  - These mean Composer translated MaterialX → MDL and compiled successfully.

**Composer's log is cumulative.** Lines from a pre-fix load stay forever. Compare timestamps `[<ms>ms]` — if the original error doesn't reappear at recent timestamps after re-export, the fix held.

## When the error appears to persist after re-export

1. `File → New` in Composer (close the stage entirely), then `File → Open` the `.usd`. A reference reload is **not enough** — omni.materialx caches compiled material networks per stage.
2. If still failing, **fully restart Composer**. That clears the compiled-shader cache and the MDL scratch dir at `%TEMP%/x18p8.1/...`.
3. If it persists after restart, the fix didn't land in the export. Re-run pre-flight 2–4 against the live LOP network.

## Houdini-Solaris quirks that look wrong but are fine

- Per-Shader `rel material:binding` rels — Houdini convention, harmless.
- `apiSchemas = ["MaterialBindingAPI"]` on Shaders — same.
- `string config:mtlx:version = "1.39"` on Materials — metadata only.

## Anti-patterns specific to Omniverse export

- Leaving `genpreviewshaders=1` on a materiallibrary LOP targeting Omniverse.
- Wiring a zero-default node (e.g. unused `mtlxdisplacement`) into a subnet's `displacement_output`.
- Using `karma_mtlxstandard_surface` (Karma-wrapped) and exporting for an RTX renderer.
- Trusting `find_error_nodes` alone before exporting.
- Reloading via reference/sublayer after a material fix instead of `File → New` + reopen.

## Network housekeeping (ALWAYS follow these)

- Call `log_status` at the start of every major step (creating geometry, wiring the chain, setting up materials, etc.) so the user can see what you are doing in Houdini's status bar without inspecting tool call logs. Keep messages short: "Creating source geometry...", "Wiring SOP chain...", "Done — display flag set on output node."
- Call `set_current_network` on the parent network you are building in so the user can see your work in the network editor. Do this BEFORE you start creating nodes, and again whenever you move to a different network level.
- Preserve existing node positions. Do not call `layout_children` as routine cleanup after edits. Only use it when the user explicitly asks for layout/cleanup, or on a newly created isolated parent network/subnet where it will not move existing user nodes.
