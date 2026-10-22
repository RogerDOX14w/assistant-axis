#!/usr/bin/env bash
# Pod start command for the assistant-axis extraction (RunPod; 2026-10-22,
# replacing runpod_workspace/qwen/startup/start.sh of April, without the idle
# watchdog, which Roger retired).
#
# The pod template's start command, once the checkout is on the network volume:
#   bash -c 'S=/workspace/assistant-axis/pipeline/pod/start.sh; if [ -x "$S" ]; then exec "$S"; else exec /start.sh; fi'
# The first pod on a new volume therefore boots the image's own /start.sh;
# clone the repository then (it is public, no token needed).  Name the branch:
# GitHub's default is master, over a thousand commits behind the working branch.
#   git clone -b anthropic-vllm-uv https://github.com/RogerDOX14w/assistant-axis.git /workspace/assistant-axis
# and every later boot runs this script.
#
# Setup runs in the background, logged to /workspace/pod_setup.log, while the
# image's /start.sh (SSH, Jupyter) takes over the foreground at once, so a slow
# or failed setup never keeps SSH from coming up.  (April's script ran uv sync
# first, under set -e, before SSH started.)
#
# Environment: set these as the template's environment variables, not only
# here, so that SSH sessions see them too (an interactive `uv run` without
# UV_PROJECT_ENVIRONMENT would build a second venv on the network volume).
# The defaults below apply when one is unset.
#   HF_HOME                 /workspace/.cache/huggingface   model cache, persistent
#   UV_CACHE_DIR            /workspace/.uv-cache             wheel cache, persistent
#   UV_PROJECT_ENVIRONMENT  /root/venvs/assistant-axis       the venv, off the network
#                           volume (pod TODO item 3: time the torch import here
#                           against a venv on /workspace before settling it)
#   UV_LINK_MODE            copy                             cache and venv sit on
#                           different filesystems, so uv cannot hard-link
# Secrets (OPENAI_API_KEY, HF_TOKEN) come from RunPod's secret store through
# the template's environment variables; nothing here reads or prints them.
set -uo pipefail

REPO=/workspace/assistant-axis
LOG=/workspace/pod_setup.log

export HF_HOME="${HF_HOME:-/workspace/.cache/huggingface}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/workspace/.uv-cache}"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-/root/venvs/assistant-axis}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"

setup() {
    echo "[$(date -u +%FT%TZ)] pod setup: start"
    if ! command -v tmux >/dev/null || ! command -v rsync >/dev/null; then
        apt-get update -qq && apt-get install -y -qq tmux rsync vim-tiny
    fi
    if ! command -v uv >/dev/null && [ ! -x "$HOME/.local/bin/uv" ]; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    export PATH="$HOME/.local/bin:$PATH"
    if [ ! -d "$REPO/.git" ]; then
        echo "no checkout at $REPO: clone it (see the header), then rerun this script"
        return 1
    fi
    mkdir -p "$(dirname "$UV_PROJECT_ENVIRONMENT")"
    local t0=$SECONDS
    if ! (cd "$REPO" && uv sync --frozen); then
        echo "uv sync failed"
        return 1
    fi
    echo "uv sync: $((SECONDS - t0)) s into $UV_PROJECT_ENVIRONMENT"
    t0=$SECONDS
    "$UV_PROJECT_ENVIRONMENT/bin/python" -c \
        "import torch, vllm; print('torch', torch.__version__, 'cuda', torch.version.cuda, 'vllm', vllm.__version__, 'gpus', torch.cuda.device_count())"
    echo "import torch and vllm: $((SECONDS - t0)) s"
    echo "free space and mounts:"
    df -h /dev/shm /workspace / 2>&1 | sed 's/^/  /'
    mount | grep -E ' /dev/shm | /workspace ' | sed 's/^/  /'
    echo "[$(date -u +%FT%TZ)] pod setup: done"
}

# One setup at a time; the lock lives on the container disk, so a new boot
# starts clean.
(
    flock -n 9 || { echo "pod setup already running"; exit 0; }
    setup
) 9>/tmp/pod_setup.lock >>"$LOG" 2>&1 &

exec /start.sh
