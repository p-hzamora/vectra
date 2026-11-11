#!/bin/sh
# Install the `vectra` command.
#
#   curl -LsSf https://raw.githubusercontent.com/p-hzamora/vectra/main/install.sh | sh
#   ./install.sh                 # from a checkout: installs that checkout
#   ./install.sh --uninstall
#
# It uses the first installer it finds: uv, then pipx, then a private virtual environment
# built with Python 3.14+. Environment variables:
#   VECTRA_SOURCE       what to install: a git URL or a local path (default: this checkout
#                       when run from one, else the GitHub repository)
#   VECTRA_REF          git branch, tag or commit for a git source (default: main)
#   VECTRA_INSTALLER    force one of: uv, pipx, venv
#   VECTRA_HOME         venv installer only: where the venv lives (default: ~/.local/share/vectra)
#   VECTRA_BIN_DIR      venv installer only: where the launcher goes (default: ~/.local/bin)
set -eu

REPO_URL="https://github.com/p-hzamora/vectra"
VECTRA_REF="${VECTRA_REF:-main}"
VECTRA_HOME="${VECTRA_HOME:-$HOME/.local/share/vectra}"
VECTRA_BIN_DIR="${VECTRA_BIN_DIR:-$HOME/.local/bin}"

say() { printf 'vectra-install: %s\n' "$*"; }
die() { printf 'vectra-install: error: %s\n' "$*" >&2; exit 1; }
has() { command -v "$1" >/dev/null 2>&1; }

# Default source: the checkout this script sits in, otherwise the repository at VECTRA_REF.
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" 2>/dev/null && pwd) || script_dir=""
if [ -z "${VECTRA_SOURCE:-}" ]; then
    if [ -n "$script_dir" ] && grep -qs '^name = "vectra"' "$script_dir/pyproject.toml"; then
        VECTRA_SOURCE="$script_dir"
    else
        VECTRA_SOURCE="$REPO_URL"
    fi
fi

case "$VECTRA_SOURCE" in
    http://* | https://* | git@* | ssh://*) spec="git+${VECTRA_SOURCE}@${VECTRA_REF}" ;;
    *) [ -f "$VECTRA_SOURCE/pyproject.toml" ] || die "no pyproject.toml in $VECTRA_SOURCE"
       spec="$VECTRA_SOURCE" ;;
esac

find_python() {
    for candidate in python3.14 python3 python; do
        if has "$candidate" && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 14))' 2>/dev/null; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

pick_installer() {
    if [ -n "${VECTRA_INSTALLER:-}" ]; then
        echo "$VECTRA_INSTALLER"
    elif has uv; then
        echo uv
    elif has pipx && find_python >/dev/null; then
        echo pipx
    else
        echo venv
    fi
}

uninstall() {
    removed=0
    want="${VECTRA_INSTALLER:-}"
    if [ -z "$want" -o "$want" = uv ] && has uv && uv tool list 2>/dev/null | grep -q '^vectra '; then
        uv tool uninstall vectra && removed=1
    fi
    if [ -z "$want" -o "$want" = pipx ] && has pipx && pipx list --short 2>/dev/null | grep -q '^vectra '; then
        pipx uninstall vectra && removed=1
    fi
    if [ -z "$want" -o "$want" = venv ] && [ -d "$VECTRA_HOME/venv" ]; then
        rm -rf "$VECTRA_HOME/venv"
        [ -L "$VECTRA_BIN_DIR/vectra" ] && rm -f "$VECTRA_BIN_DIR/vectra"
        removed=1
    fi
    [ "$removed" = 1 ] && say "vectra removed (config in ~/.config/vectra and your indexes are kept)" \
        || say "vectra is not installed"
}

install() {
    has git || case "$spec" in git+*) die "git is required to install from $VECTRA_SOURCE" ;; esac
    installer=$(pick_installer)
    say "installing $spec with $installer"
    case "$installer" in
        uv)
            # uv downloads Python 3.14 itself when the system has none.
            uv tool install --force --python '>=3.14' "$spec"
            ;;
        pipx)
            python=$(find_python) || die "pipx needs Python 3.14+; install it or use uv"
            pipx install --force --python "$python" "$spec"
            ;;
        venv)
            python=$(find_python) || die "Python 3.14+ not found. Install it, or install uv: https://docs.astral.sh/uv/"
            mkdir -p "$VECTRA_HOME" "$VECTRA_BIN_DIR"
            rm -rf "$VECTRA_HOME/venv"
            "$python" -m venv "$VECTRA_HOME/venv"
            "$VECTRA_HOME/venv/bin/python" -m pip install --quiet --upgrade pip
            "$VECTRA_HOME/venv/bin/python" -m pip install --quiet "$spec"
            ln -sf "$VECTRA_HOME/venv/bin/vectra" "$VECTRA_BIN_DIR/vectra"
            ;;
        *) die "unknown installer '$installer' (use uv, pipx or venv)" ;;
    esac

    if [ "$installer" = venv ]; then
        say "installed $("$VECTRA_BIN_DIR/vectra" --version)"
    fi
    if ! has vectra; then
        say "installed, but 'vectra' is not on your PATH. Add this to your shell profile:"
        say "  export PATH=\"\$HOME/.local/bin:\$PATH\"   (or the bin dir your installer printed)"
    fi
    say "next: vectra config show && vectra sync <name> <folder> --dry-run"
}

case "${1:-}" in
    --uninstall) uninstall ;;
    "") install ;;
    -h | --help) sed -n '2,16p' "$0" 2>/dev/null || say "see $REPO_URL" ;;
    *) die "unknown option '$1' (use --uninstall or --help)" ;;
esac
