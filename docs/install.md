# Installing vectra

vectra comes in two parts that you install separately:

1. **The `vectra` command**, a Python 3.14+ package.
2. **The agent skill** (`skills/vectra/SKILL.md`), which tells coding agents how to use the
   command.

## 1. The command

### One-line installer

```bash
curl -LsSf https://raw.githubusercontent.com/p-hzamora/vectra/main/install.sh | sh
```

`install.sh` uses the first installer it finds:

| Installer | When | Where `vectra` goes |
|---|---|---|
| `uv tool install` | `uv` is on your `PATH` | uv's tool bin dir (usually `~/.local/bin`). uv downloads Python 3.14 if you don't have it. |
| `pipx install` | no `uv`, but `pipx` and Python 3.14+ are | pipx's bin dir (usually `~/.local/bin`) |
| a private venv | neither, but Python 3.14+ is | venv in `~/.local/share/vectra/venv`, launcher symlinked into `~/.local/bin` |

If none of these work, the script stops and says what is missing. Git is needed to install
from the repository.

Run from a checkout (`./install.sh`), it installs that checkout instead of the repository.

Settings (environment variables):

| Variable | Default | Meaning |
|---|---|---|
| `VECTRA_SOURCE` | this checkout, else `https://github.com/p-hzamora/vectra` | git URL or local path to install |
| `VECTRA_REF` | `main` | branch, tag or commit, for a git source |
| `VECTRA_INSTALLER` | auto | force `uv`, `pipx` or `venv` |
| `VECTRA_HOME` | `~/.local/share/vectra` | venv installer only: where the venv goes |
| `VECTRA_BIN_DIR` | `~/.local/bin` | venv installer only: where the launcher goes |

Example: to install a given commit with pipx:

```bash
curl -LsSf https://raw.githubusercontent.com/p-hzamora/vectra/main/install.sh \
  | VECTRA_REF=<commit-or-tag> VECTRA_INSTALLER=pipx sh
```

To upgrade, run the installer again; it replaces the existing install. To uninstall:

```bash
curl -LsSf https://raw.githubusercontent.com/p-hzamora/vectra/main/install.sh | sh -s -- --uninstall
```

Uninstalling removes the command only. Your config (`~/.config/vectra/`) and your indexes
(`~/.local/share/vectra/index/`) are kept.

### Manual install

You can also install with any of these:

```bash
uv tool install git+https://github.com/p-hzamora/vectra
pipx install --python python3.14 git+https://github.com/p-hzamora/vectra
python3.14 -m pip install --user git+https://github.com/p-hzamora/vectra
```

For development, `make install` does an editable `uv tool install` of your checkout, so
source edits apply at once.

### Configure and check

```bash
vectra config show                          # the env file read and the data folder
vectra sync notes ~/notes --dry-run         # lists what would be indexed; writes nothing
```

## 2. The agent skill

The skill is a small stub. It finds the `vectra` command and loads the guide that matches
the installed version (`vectra skills get vectra`), so it does not go out of date when you
upgrade the command. Install it with the [`skills`](https://github.com/vercel-labs/skills)
CLI (needs Node.js):

```bash
npx skills add p-hzamora/vectra --skill vectra -g     # every project, for your user
npx skills add p-hzamora/vectra --skill vectra        # this project only
npx skills add ./path/to/vectra --skill vectra -g     # from a local checkout
```

`-g` installs it for your user rather than for the current project. The CLI asks which
agents to install it for (Claude Code, Codex, Cursor and others).

Without Node.js, copy the folder yourself:

```bash
mkdir -p ~/.claude/skills && cp -R skills/vectra ~/.claude/skills/   # Claude Code, from a checkout
```
