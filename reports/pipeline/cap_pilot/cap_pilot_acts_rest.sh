#!/usr/bin/env bash
# The cap pilot step 2 after cap768 ran out of GPU memory at --batch_size 8 (2026-10-29, 12 of 64
# entities: the stacked activations of 8 conversations of up to 768 response tokens no longer fit
# beside the 64-GB model on one A100): cap768 resumed and cap1024 run at --batch_size 4 (the last
# --batch_size wins over cap_pilot_run.sh's 8).  Log: /workspace/cap_pilot/acts_rest.log.
R=/workspace/cap_pilot_run.sh
$R acts cap768 --batch_size 4 || exit 1
$R acts cap1024 --batch_size 4 --prefix_token_means 256,512,768 --prefix_token_layers 25 || exit 1
echo "[$(date -u +%FT%TZ)] step 2 done for cap768 and cap1024"
