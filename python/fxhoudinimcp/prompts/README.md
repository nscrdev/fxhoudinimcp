# Prompts & Claude Code Skills

This folder holds the MCP prompt templates (`markdown/*.md` + `workflows.py`) that ship with `fxhoudinimcp`. They are exposed to any MCP client as slash commands — e.g. `/procedural_modeling_workflow` in Claude Desktop, Cursor, Claude Code, etc. The user must invoke them explicitly.

## Claude Code skill mirror (local only, not shipped)

To get **natural-language triggering** in Claude Code (so a phrase like *"build me a procedural terrain"* auto-loads the guidance without the user typing a slash command), the same content is mirrored as Claude Code skills at `~/.claude/skills/`.

Skills are a Claude Code-only feature — they are NOT part of this MCP package and do NOT ship to other users. They live entirely outside this repo.

### Mapping

| MCP prompt (`markdown/`)  | Mirrored skill (`~/.claude/skills/`)      | Triggers on                                                            |
|---------------------------|-------------------------------------------|------------------------------------------------------------------------|
| `procedural_modeling.md`  | `houdini-procedural-modeling/SKILL.md`    | build / scatter / extrude / fracture geometry                          |
| `simulation_setup.md`     | `houdini-simulation/SKILL.md`             | pyro, FLIP, RBD, Vellum, POP, crowds, "make X explode"                 |
| `usd_scene_assembly.md`   | `houdini-usd-solaris/SKILL.md`            | /stage, LOPs, Karma lookdev, materiallibrary, lighting rigs            |
| `debug_scene.md`          | `houdini-debug-scene/SKILL.md`            | "broken", "find errors", "nothing showing", "sim exploding"            |
| `hda_development.md`      | `houdini-hda/SKILL.md`                    | "turn this into an HDA", "promote parameters"                          |
| `pdg_pipeline.md`         | `houdini-pdg/SKILL.md`                    | /tasks, wedge, batch render, ROP Fetch, FFmpeg encode                  |
| `network_housekeeping.md` | *(inlined into each skill)*               | shared snippet — skills have no interpolation, so it's copy-pasted in  |
| `server_instructions.md`  | *(not mirrored)*                          | auto-loaded on every MCP session as the server's system instructions   |

### Sync rules

The MCP prompts are the **source of truth**. Skills drift out of sync if you edit the markdown here without updating the mirror. When updating a prompt:

1. Edit `markdown/<name>.md` in this folder.
2. Edit `~/.claude/skills/<skill-name>/SKILL.md` to match.
3. If you changed `network_housekeeping.md`, re-inline it into every skill (they each carry their own copy since Claude skills have no template interpolation).

If the drift becomes annoying, a sync script that regenerates all six `SKILL.md` files from the MCP prompt sources + a fixed frontmatter template would be straightforward to add.

### Why mirror at all?

MCP prompts and Claude Code skills trigger differently:

- **MCP prompts** — visible to me only when the user invokes them (`/procedural_modeling_workflow`). I cannot auto-load them from natural language. They work in **every** MCP client (Claude Desktop, Cursor, Claude Code, ChatGPT desktop).
- **Claude Code skills** — their `description` field is in my system prompt at session start, so I pattern-match against natural language and auto-invoke. They work **only in Claude Code**.

Both mechanisms coexist. The MCP prompts stay in this repo for portability; the skills are a Claude Code convenience layer on top.

## Codex skills

For Codex, the mirrored workflow skills live in the repo-local
[`codex-skill/`](../../../codex-skill/) folder instead of `~/.claude/skills/`.
They are discovered through the repo's `.agents/skills` path so the checked-in
repo copy stays the source of truth. See the Codex setup note in the main
[`README.md`](../../../README.md) installation section.
