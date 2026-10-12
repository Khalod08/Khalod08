#!/bin/bash
# Prepares a Claude Code on the web session for GoatVex: system tools for the videos
# (LaTeX, FFmpeg, Cairo/Pango) and the Python environment in goatvex-tutor/.venv.
# Idempotent: anything already installed is skipped (the container is cached afterwards).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0  # on your own PC, scripts/setup_windows.ps1 does this instead
fi

GOATVEX="$CLAUDE_PROJECT_DIR/goatvex-tutor"

need_apt=()
command -v latex >/dev/null 2>&1 || need_apt+=(texlive-latex-base texlive-latex-recommended texlive-latex-extra
                                             texlive-fonts-recommended texlive-pictures texlive-lang-greek)
command -v dvisvgm >/dev/null 2>&1 || need_apt+=(dvisvgm)
command -v ffmpeg >/dev/null 2>&1 || need_apt+=(ffmpeg)
pkg-config --exists pangocairo 2>/dev/null || need_apt+=(libcairo2-dev libpango1.0-dev pkg-config)
if [ ${#need_apt[@]} -gt 0 ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends "${need_apt[@]}" >/dev/null
fi
# offline voice for videos when Edge TTS can't be reached (optional: never fail the session over it)
if ! command -v pico2wave >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  { apt-get install -y -qq --no-install-recommends libttspico-utils >/dev/null 2>&1 ||
    { apt-get update -qq && apt-get install -y -qq --no-install-recommends libttspico-utils >/dev/null 2>&1; } ||
    apt-get install -y -qq --no-install-recommends espeak-ng >/dev/null 2>&1; } || true
fi

PY=python3.11
command -v "$PY" >/dev/null 2>&1 || PY=python3.12   # manim-voiceover needs audioop: not 3.13+
if [ ! -x "$GOATVEX/.venv/bin/python" ]; then
  "$PY" -m venv "$GOATVEX/.venv"
fi
"$GOATVEX/.venv/bin/python" -m pip install -q --upgrade pip
"$GOATVEX/.venv/bin/python" -m pip install -q -r "$GOATVEX/requirements.txt"

# every shell in the session uses GoatVex's environment; videos use Edge TTS if this environment's
# network settings allow speech.platform.bing.com, otherwise the offline voice
{
  echo "export VIRTUAL_ENV=\"$GOATVEX/.venv\""
  echo "export PATH=\"$GOATVEX/.venv/bin:\$PATH\""
  echo "export GOATVEX_VOICE=auto"
  echo "export GOATVEX_NO_BROWSER=1"
} >> "${CLAUDE_ENV_FILE:-/dev/null}"
