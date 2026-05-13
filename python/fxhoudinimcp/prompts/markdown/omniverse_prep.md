You are preparing a Houdini scene for export to NVIDIA Omniverse ({target_app}).

Goal: {scene_description}

## Why this prompt exists (READ THIS FIRST)

Omniverse's MaterialX / USD ingest is **stricter than Houdini's**. A scene that cooks cleanly in Houdini with zero error nodes can still produce `Cannot find node: ''`, `Ill-formed SdfPath <>`, and silent material-binding fallbacks once loaded in {target_app}. `find_error_nodes` alone is necessary but not sufficient — you must also verify what gets **authored into the exported USD**, not just what Houdini thinks is valid.

## Pre-flight checklist (run BEFORE every Omniverse export)

Run these in order. Skip nothing.

### 1. Resolve Houdini-side errors and known-bad warnings

- Call `find_error_nodes(root_path="/stage")`. Any `error_count > 0` blocks the export.
- Warnings are usually safe to leave (e.g. missing render camera on `karmarendersettings`), but record them so you can distinguish "expected" warnings from new ones after fixes.

### 2. Inspect every `materiallibrary` LOP

For each materiallibrary node in `/stage`:

- Call `get_parameter_schema(node, filter="preview")` and confirm **`genpreviewshaders=0`**.
- **The default is `1`**, which silently auto-generates a UsdPreviewSurface fallback shader (`mtlxstandard_preview`) AND a duplicate `outputs:surface` connection on the Material prim. omni.materialx walks both surface output targets and gets confused — often producing `Cannot find node: ''` in {target_app}.
- Fix with `set_parameter(node, "genpreviewshaders", 0)` (use the integer `0`, not boolean `false` — the toggle is a numeric parm).

### 3. Walk the MaterialX subnet for orphan shader nodes

Inside each MaterialX subnet under a materiallibrary (e.g. `materiallibrary1/sphere_mat`):

- Call `list_children` to find every `subnetconnector` — those are the subnet's surface / displacement / volume terminal outputs.
- For each subnetconnector, call `get_node_info` and check its `inputs[]` array. If a subnetconnector has an upstream node, recursively walk that node's inputs.
- An **orphan** is any node in the chain where:
  - `inputs: []` is empty, AND
  - Its `non_default_parameters` are all at zero / identity values.
- Orphans export as Shader prims with no connections. The Material's output connection to them ends up as `<>` (empty SdfPath), which is the literal cause of `Cannot find node: ''` and `Ill-formed SdfPath <>` warnings.
- Fix by **one** of: disconnect the orphan from the subnetconnector with `disconnect_node`, delete the orphan with `delete_node`, or wire real inputs into it.

### 4. Verify the authored USD prims live

- Call `find_usd_prims(materiallibrary_node, "/materials/**")`.
- Expected: **one Material prim plus one Shader prim per *active* VOP node in the MaterialX subnet**, no extras.
- If a Shader prim appears that has no corresponding live VOP, it's coming from auto-generation (see step 2).
- If a Shader prim exists for a VOP node that step 3 flagged as orphaned, it'll cause the empty-path error.

### 5. Confirm the Material's output connections

The Material prim should author **exactly one** of `outputs:mtlx:surface`, plus optionally `outputs:mtlx:displacement` or `outputs:mtlx:volume` IF those targets point at real, fully-wired shaders. **Never** allow both `outputs:surface` (UsdPreviewSurface) and `outputs:mtlx:surface` to coexist — that's the duplicate-surface trap from step 2.

### 6. Cook the USD ROP and re-verify on disk

- Trigger your USD ROP (e.g. `/stage/<name>` of type `usd_rop`).
- Optional belt-and-suspenders: re-read the resulting `.usd` to confirm. Houdini ships its own `usdcat` at `<houdini_install>/bin/usdcat.exe` — convert binary USDC to grep-able ASCII with:
  ```
  usdcat --flatten input.usd -o readable.usda
  ```

## Reading the {target_app} log

After loading a USD into {target_app}, scan its log. Group lines by what they indicate, not by their severity tag — many `[Warning]` lines are **proof of success**, not failure.

| Log line | Meaning | Action |
|---|---|---|
| `[omni.materialx] Cannot find node: '' in HdMaterialNetwork` | Empty SdfPath in material — orphan or duplicate-surface | Re-run pre-flight steps 2 and 3 |
| `[omni.usd] Ill-formed SdfPath <>` | Same root cause as above | Same |
| `[omni.kit.property.usd.placeholder_attribute] customData.default ... not found ... material:binding` | Material network failed to build → fell back to placeholder | Downstream symptom of an upstream materialx error |
| `[omni.fabric.plugin] getAttributeCount/getTypes/removePath called on non-existent path` | **GOOD** — Composer is cleaning up a prim that existed in a previous load but was removed in re-export. Cumulative log noise from the reimport. |
| `Source: omni.materialx was already registered` | Double-registration: `omni.materialx` and its schema package both register the source name. Cosmetic, ignore. |
| `gpu.foundation.plugin acquired ... N times` | Performance hint aimed at NVIDIA's renderer devs. Not actionable for users. |
| `[MDLC:COMPILER] C183 unused parameter 'transmission_*'` | **GOOD** — Composer just translated MaterialX → MDL and compiled successfully. The unused params are MaterialX standard_surface inputs that the MDL backend doesn't currently consume. |
| `[MDLC:COMPILER] C350 unused let temporary 'c_box_filter_weights'`, etc. | **GOOD** — same MDL translation, dead intermediates in the auto-generated code. |

### Reading log timestamps

The {target_app} log is **cumulative across reloads in the same session** — lines from the original (pre-fix) load stay visible forever. Compare timestamps `[<ms>ms]`:

- Lines at `<60,000ms` are usually from initial load.
- Lines after a re-import will have much larger timestamps (often `>1,000,000ms` if the session has been alive a while).
- If `Cannot find node: ''` doesn't reappear at recent timestamps after re-export, the fix held.

## When the error appears to persist

If after fixing and re-exporting the same error reappears at a **recent** log timestamp:

1. **`File → New`** in {target_app} (close the stage entirely), then **`File → Open`** the `.usd` again. A reference reload or hot-reload is **not enough** — omni.materialx caches the compiled material network per stage and a stale cache will replay the old error.
2. If the error still appears, **fully restart {target_app}**. Quit the app and relaunch. That clears omni.materialx's compiled-shader cache and the MDL scratch dir at `%TEMP%/x18p8.1/...`.
3. If it *still* appears after a clean restart, the fix didn't actually land in the exported `.usd`. Re-run the pre-flight checklist on the live LOP network and confirm with `find_usd_prims` before re-exporting.

## Houdini-Solaris quirks that look wrong but are fine in Omniverse

- Every Shader prim under a Material has `rel material:binding = </materials/yourmaterial>`. Houdini Solaris convention. Harmless.
- The Material prim itself also has `rel material:binding` to itself. Same reason.
- `apiSchemas = ["MaterialBindingAPI"]` on Shader prims. Same reason.
- `string config:mtlx:version = "1.39"` on the Material — fine, just metadata.

## Anti-patterns specific to Omniverse export

| BAD | USE INSTEAD |
|-----|-------------|
| Leaving `genpreviewshaders=1` on a materiallibrary LOP targeting Omniverse | Set to `0` so the MaterialX network is the only surface output authored |
| Wiring an empty `mtlxdisplacement` (or any zero-default node) into a subnet's `displacement_output` | Disconnect the subnetconnector, OR wire a real displacement input first |
| Using `karma_mtlxstandard_surface` (Karma-wrapped) and exporting for an RTX renderer like {target_app} | Use a plain MaterialX subnet with `mtlxstandard_surface` directly |
| Trusting `find_error_nodes` alone as the green light to export | Always also run pre-flight steps 2–4 against the authored USD |
| Reloading the `.usd` in {target_app} via reference / sublayer after a material fix | Close the stage with `File → New`, then re-open. Restart {target_app} entirely if errors persist. |

## Living document

This prompt is intended to grow as the team encounters more Omniverse-specific quirks. When a new ingest issue is discovered, log it under one of:

- **Pre-flight checklist** — if it can be detected and prevented in Houdini before export
- **Reading the log** — if it shows up as a specific log line in {target_app}
- **Anti-patterns** — if it's a workflow choice that creates the issue

{network_housekeeping}
