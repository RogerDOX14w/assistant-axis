#!/usr/bin/env bash
# The cap pilot's GPU work, in order (plan § 4): step 1 for every tree, then step 2 for every
# tree but cap1024, whose step 2 waits for --prefix_token_means.  Resumable: every step skips
# what exists.  Log: /workspace/cap_pilot/queue.log.
R=/workspace/cap_pilot_run.sh
for t in "cap256 256" "cap512 512" "cap512b 512" "cap768 768" "cap1024 1024"; do
    set -- $t
    $R gen "$1" "$2" || exit 1
done
for t in cap256 cap512 cap512b cap768; do
    $R acts "$t" || exit 1
done
echo "[$(date -u +%FT%TZ)] queue: steps 1 (all trees) and 2 (all but cap1024) done"
