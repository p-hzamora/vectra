# vectra: guide for agents

vectra chunks files, embeds the chunks into a vector store, and answers semantic searches.
This guide matches the installed vectra version. Use `vectra <command> --help` for anything
not covered here.

## Rules

- Always add `--json`. Parse the envelope: `{"ok": true, "result": ...}` or
  `{"ok": false, "error": {"code", "message", "next_steps"}}`. Branch on `error.code`.
- Exit codes: 0 ok, 1 the operation failed, 2 invalid command line.
- Never guess commands or flags. If something is not in this guide, run `--help`.

## Commands

- `vectra config show --json`: the configuration file read and the data folder.
- `vectra skills list --json` / `vectra skills get <name> --json`: the guides this version ships.
