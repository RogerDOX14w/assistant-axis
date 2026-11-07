#!/usr/bin/env bash
# Poll the sample pod's run until a pattern appears in run.log (exit 0), a
# failure shows (exit 3: "FAILED", a non-zero "exit N" line in run.log, or a
# Traceback in a step log), or the time runs out (exit 2).  Prints the tail of
# run.log, the responses present and the GPU state at the end.
#   bash watch_run.sh 'step 1 summary' 90        (pattern, minutes; polls every 3 min)
# Run from the repo root (the ssh config path is relative).  ssh -n: no stdin,
# so the session never waits on the detached run.
set -u
PATTERN=$1; MAXMIN=${2:-120}
SSH="ssh -n -F .secrets/runpod/ssh_config sample"
t0=$(date +%s)
while :; do
    out=$($SSH 'cat /root/sample_ids/run.log 2>/dev/null; echo "@@TB@@"; grep -l Traceback /root/sample_ids/logs/*.log 2>/dev/null' 2>&1)
    log=${out%%@@TB@@*}; tb=${out##*@@TB@@}
    if grep -qE "FAILED|^   exit [1-9]|a step failed" <<<"$log" || [ -n "$(tr -d '[:space:]' <<<"$tb")" ]; then
        echo "$(date -u +%FT%TZ) FAILURE"; echo "--- traceback in:"; echo "$tb"; echo "--- run.log tail"; tail -25 <<<"$log"
        $SSH 'for f in $(grep -l Traceback /root/sample_ids/logs/*.log 2>/dev/null); do echo "=== $f"; grep -n -B2 -A12 Traceback "$f" | tail -40; done' 2>&1 | cut -c1-300
        exit 3
    fi
    if grep -qE "$PATTERN" <<<"$log"; then
        echo "$(date -u +%FT%TZ) MATCH: $PATTERN"; echo "--- run.log tail"; tail -30 <<<"$log"
        $SSH 'echo "--- responses"; ls -la /root/sample_ids/responses 2>/dev/null | tail -25; echo "--- gpu"; nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader; echo "--- disk"; df -h / | tail -1' 2>&1
        exit 0
    fi
    if [ $(( $(date +%s) - t0 )) -ge $(( MAXMIN * 60 )) ]; then
        echo "$(date -u +%FT%TZ) TIMEOUT after $MAXMIN min without '$PATTERN'"; echo "--- run.log tail"; tail -20 <<<"$log"
        $SSH 'ls -la /root/sample_ids/responses 2>/dev/null | tail -25; nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader; for f in /root/sample_ids/logs/step*.log; do echo "== $f"; tail -3 "$f" | cut -c1-200; done' 2>&1
        exit 2
    fi
    sleep 180
done
