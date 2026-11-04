#!/usr/bin/env bash
# Pod watchdog: stop this pod when the run it was armed for has gone idle
# (Roger, 2026-11-04: an autonomous, local belt and braces against a pod left
# running when the laptop sleeps or the agent's session ends; the cue it
# watches is explicit and scriptable, and it is armed before each extended
# run rather than guessing from CPU or GPU utilisation, which is what April's
# auto_stop_on_idle.sh tried and could not read).
#
#   watchdog.sh arm --idle-min 60 [--every-min 5] [--watch DIR]... [--pid N]...
#                   [--pid-file FILE]... [--ignore-ssh] [--ignore-gpu] [--dry-run]
#   watchdog.sh hold [HOURS]     a hold of HOURS (default 4): no stop while it lasts
#   watchdog.sh release          end the hold now
#   watchdog.sh status           the armed configuration, the hold, the last decision
#   watchdog.sh check            one decision, printed, nothing stopped (status 0 busy, 1 idle)
#   watchdog.sh disarm           stop the loop (the pod keeps running)
#
# Busy means any of: a file under a --watch directory modified within the
# last --idle-min minutes (the run's own output is the cue; give the
# directory it writes into); a --pid or a --pid-file's pid alive; a hold in
# force; an SSH session open (someone is working on the pod; --ignore-ssh
# turns this cue off); a process on a GPU (--ignore-gpu).  The loop checks
# every --every-min minutes and, when nothing has been busy for --idle-min
# minutes, writes a STOPPING line to the log and runs the stop command:
# `runpodctl stop pod $RUNPOD_POD_ID` (RunPod installs runpodctl and the key
# it needs on every pod; checked 2026-11-04), or $WATCHDOG_STOP_CMD when set.
# --dry-run logs the decision and does not stop.
#
# State in $WATCHDOG_DIR (default /workspace/.watchdog, on the volume so the
# log outlives the pod): config, pid, hold, last, log.  The run script that
# arms the watchdog still stops the pod itself when its outputs are safe; the
# watchdog is the backstop.  A stop erases the container disk, so arm it on a
# directory the run writes to until its outputs are copied off, or hold it
# while pulling.
set -uo pipefail

DIR="${WATCHDOG_DIR:-/workspace/.watchdog}"
LOG="$DIR/log"
now() { date -u +%s; }
stamp() { date -u +%FT%TZ; }
log() { mkdir -p "$DIR"; echo "$(stamp) $*" | tee -a "$LOG"; }
die() { echo "watchdog: $*" >&2; exit 2; }

# ---- the decision ---------------------------------------------------------
# Reads the configuration from $DIR/config (written by arm) unless the
# variables are already set (check_once called from the loop).
load_config() {
    [ -f "$DIR/config" ] || die "not armed (no $DIR/config)"
    # shellcheck disable=SC1090
    . "$DIR/config"
}

# Prints the busy cues, one per line; empty when idle.
busy_cues() {
    local d p f t
    for d in "${WATCH[@]-}"; do
        [ -n "$d" ] || continue
        if [ -d "$d" ] && [ -n "$(find "$d" -type f -mmin "-$IDLE_MIN" -print -quit 2>/dev/null)" ]; then
            echo "written: $d (a file under it changed within $IDLE_MIN min)"
        fi
    done
    for p in "${PIDS[@]-}"; do
        [ -n "$p" ] || continue
        if kill -0 "$p" 2>/dev/null; then echo "pid alive: $p"; fi
    done
    for f in "${PID_FILES[@]-}"; do
        [ -n "$f" ] || continue
        if [ -f "$f" ] && p=$(tr -d '[:space:]' < "$f") && [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then
            echo "pid alive: $p ($f)"
        fi
    done
    if [ -f "$DIR/hold" ]; then
        t=$(tr -d '[:space:]' < "$DIR/hold")
        if [ -n "$t" ] && [ "$t" -gt "$(now)" ] 2>/dev/null; then
            echo "hold until $(date -u -r "$t" +%FT%TZ 2>/dev/null || date -u -d "@$t" +%FT%TZ)"
        fi
    fi
    if [ "${IGNORE_SSH:-0}" != 1 ]; then
        if command -v ss >/dev/null 2>&1; then
            if [ -n "$(ss -Htn state established '( sport = :22 )' 2>/dev/null | head -1)" ]; then
                echo "ssh session open"
            fi
        elif [ -n "$(who 2>/dev/null | head -1)" ]; then
            echo "login session open"
        fi
    fi
    if [ "${IGNORE_GPU:-0}" != 1 ] && command -v nvidia-smi >/dev/null 2>&1; then
        if [ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | head -1)" ]; then
            echo "process on a gpu"
        fi
    fi
}

# One decision.  Prints BUSY or IDLE with the cues, records it in $DIR/last;
# returns 0 busy, 1 idle.
check_once() {
    local cues
    cues=$(busy_cues)
    mkdir -p "$DIR"
    if [ -n "$cues" ]; then
        echo "$(now) BUSY" > "$DIR/last"
        echo "BUSY: $(echo "$cues" | paste -sd ';' -)"
        return 0
    fi
    echo "$(now) IDLE" > "$DIR/last"
    echo "IDLE"
    return 1
}

stop_pod() {
    if [ "${DRY_RUN:-0}" = 1 ]; then
        log "DRY RUN: would stop the pod now"
        return 0
    fi
    if [ -n "${WATCHDOG_STOP_CMD:-}" ]; then
        log "STOPPING: $WATCHDOG_STOP_CMD"
        bash -c "$WATCHDOG_STOP_CMD" 2>&1 | tee -a "$LOG"
    else
        [ -n "${RUNPOD_POD_ID:-}" ] || { log "cannot stop: RUNPOD_POD_ID is not set"; return 1; }
        log "STOPPING: runpodctl stop pod $RUNPOD_POD_ID"
        runpodctl stop pod "$RUNPOD_POD_ID" 2>&1 | tee -a "$LOG"
    fi
}

# ---- the loop -------------------------------------------------------------
run_loop() {
    load_config
    local idle_since="" c
    log "armed: idle $IDLE_MIN min, every ${EVERY_SEC}s; watch=[${WATCH[*]-}] pids=[${PIDS[*]-}] pid_files=[${PID_FILES[*]-}] ignore_ssh=${IGNORE_SSH:-0} ignore_gpu=${IGNORE_GPU:-0} dry_run=${DRY_RUN:-0}"
    while :; do
        if c=$(check_once); then
            idle_since=""
            log "$c"
        else
            [ -n "$idle_since" ] || idle_since=$(now)
            local idle_s=$(( $(now) - idle_since ))
            log "IDLE for $((idle_s / 60)) min (stop at $IDLE_MIN)"
            if [ "$idle_s" -ge $(( IDLE_MIN * 60 )) ]; then
                stop_pod
                log "stop command sent; the loop ends"
                rm -f "$DIR/pid"
                exit 0
            fi
        fi
        sleep "$EVERY_SEC"
    done
}

# ---- the commands ---------------------------------------------------------
cmd=${1:-}; shift || true
case "$cmd" in
    arm)
        IDLE_MIN=""; EVERY_SEC=300; WATCH=(); PIDS=(); PID_FILES=(); IGNORE_SSH=0; IGNORE_GPU=0; DRY_RUN=0
        while [ $# -gt 0 ]; do
            case "$1" in
                --idle-min) IDLE_MIN=$2; shift 2 ;;
                --every-min) EVERY_SEC=$(( $2 * 60 )); shift 2 ;;
                --every-sec) EVERY_SEC=$2; shift 2 ;;            # for tests
                --watch) WATCH+=("$(cd "$2" 2>/dev/null && pwd || echo "$2")"); shift 2 ;;
                --pid) PIDS+=("$2"); shift 2 ;;
                --pid-file) PID_FILES+=("$2"); shift 2 ;;
                --ignore-ssh) IGNORE_SSH=1; shift ;;
                --ignore-gpu) IGNORE_GPU=1; shift ;;
                --dry-run) DRY_RUN=1; shift ;;
                *) die "unknown option $1" ;;
            esac
        done
        [ -n "$IDLE_MIN" ] && [ "$IDLE_MIN" -gt 0 ] 2>/dev/null || die "arm needs --idle-min N (minutes, > 0)"
        [ ${#WATCH[@]} -gt 0 ] || [ ${#PIDS[@]} -gt 0 ] || [ ${#PID_FILES[@]} -gt 0 ] \
            || die "arm needs a cue: --watch DIR, --pid N or --pid-file FILE"
        mkdir -p "$DIR"
        if [ -f "$DIR/pid" ] && kill -0 "$(cat "$DIR/pid")" 2>/dev/null; then
            kill "$(cat "$DIR/pid")" 2>/dev/null; log "disarmed the previous loop (pid $(cat "$DIR/pid"))"
        fi
        {
            echo "IDLE_MIN=$IDLE_MIN"; echo "EVERY_SEC=$EVERY_SEC"
            printf 'WATCH=('; printf '%q ' "${WATCH[@]-}"; echo ')'
            printf 'PIDS=('; printf '%q ' "${PIDS[@]-}"; echo ')'
            printf 'PID_FILES=('; printf '%q ' "${PID_FILES[@]-}"; echo ')'
            echo "IGNORE_SSH=$IGNORE_SSH"; echo "IGNORE_GPU=$IGNORE_GPU"; echo "DRY_RUN=$DRY_RUN"
            echo "ARMED_AT=$(stamp)"
        } > "$DIR/config"
        # setsid where it exists (Linux pods): the loop outlives the shell that armed it.
        if command -v setsid >/dev/null 2>&1; then
            setsid nohup bash "$0" _loop >> "$DIR/loop.out" 2>&1 < /dev/null &
        else
            nohup bash "$0" _loop >> "$DIR/loop.out" 2>&1 < /dev/null &
        fi
        echo $! > "$DIR/pid"
        echo "armed (loop pid $(cat "$DIR/pid")); log at $LOG"
        ;;
    _loop) run_loop ;;
    hold)
        hours=${1:-4}
        mkdir -p "$DIR"
        echo $(( $(now) + hours * 3600 )) > "$DIR/hold"
        log "hold for $hours h (until $(date -u -r "$(cat "$DIR/hold")" +%FT%TZ 2>/dev/null || date -u -d "@$(cat "$DIR/hold")" +%FT%TZ))"
        ;;
    release) rm -f "$DIR/hold"; log "hold released" ;;
    check) load_config; check_once ;;
    status)
        if [ -f "$DIR/config" ]; then
            echo "config ($DIR/config):"; sed 's/^/  /' "$DIR/config"
        else
            echo "not armed"
        fi
        if [ -f "$DIR/pid" ] && kill -0 "$(cat "$DIR/pid")" 2>/dev/null; then
            echo "loop: running (pid $(cat "$DIR/pid"))"
        else
            echo "loop: not running"
        fi
        if [ -f "$DIR/hold" ]; then
            t=$(cat "$DIR/hold")
            if [ "$t" -gt "$(now)" ] 2>/dev/null; then echo "hold: until $(date -u -r "$t" +%FT%TZ 2>/dev/null || date -u -d "@$t" +%FT%TZ)"; else echo "hold: expired"; fi
        else
            echo "hold: none"
        fi
        [ -f "$DIR/last" ] && echo "last decision: $(cat "$DIR/last")"
        [ -f "$LOG" ] && { echo "log tail:"; tail -5 "$LOG" | sed 's/^/  /'; }
        ;;
    disarm)
        if [ -f "$DIR/pid" ] && kill -0 "$(cat "$DIR/pid")" 2>/dev/null; then
            kill "$(cat "$DIR/pid")" && log "disarmed (pid $(cat "$DIR/pid"))"
        else
            echo "no loop running"
        fi
        rm -f "$DIR/pid"
        ;;
    ""|-h|--help) sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//' ;;
    *) die "unknown command $cmd (arm, hold, release, status, check, disarm)" ;;
esac
