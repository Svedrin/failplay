#!/usr/bin/env bash
#
# Watches for the "Logitech BT Adapter" bluetooth speaker. Whenever it's
# available, connects to it, routes PulseAudio to it and runs failaudio
# for as long as the device stays connected (restarting it whenever the
# playlist finishes). When the device disappears, failaudio is shut down
# cleanly and the script goes back to waiting.
#
# Intended to be run inside a long-lived tmux session, e.g.:
#   tmux new -s failaudio-bt ./bt_failaudio.sh
#
# Reads BT_MAC (required) and POLL_INTERVAL (optional) from
# ~/.failplay/bluetooth.conf. See README.md for the minimal config.

set -uo pipefail

readonly BT_CONF="${BT_CONF:-$HOME/.failplay/bluetooth.conf}"
# shellcheck disable=SC1090
[[ -f "$BT_CONF" ]] && source "$BT_CONF"

: "${BT_MAC:?BT_MAC is not set. Add it to $BT_CONF, e.g. BT_MAC=\"AA:BB:CC:DD:EE:FF\"}"

readonly BT_MAC
readonly POLL_INTERVAL="${POLL_INTERVAL:-10}"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly FAILAUDIO="$SCRIPT_DIR/failaudio.py"
readonly SINK_NAME="bluez_sink.${BT_MAC//:/_}.a2dp_sink"

failaudio_pid=""

log() {
    printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

is_bt_connected() {
    bluetoothctl info "$BT_MAC" 2>/dev/null | grep -q "Connected: yes"
}

is_failaudio_running() {
    [[ -n "$failaudio_pid" ]] && kill -0 "$failaudio_pid" 2>/dev/null
}

stop_failaudio() {
    is_failaudio_running || return 0

    log "Stopping failaudio (pid $failaudio_pid)..."
    kill -INT "$failaudio_pid" 2>/dev/null
    for _ in $(seq 1 10); do
        is_failaudio_running || break
        sleep 1
    done
    if is_failaudio_running; then
        log "failaudio did not exit in time, sending SIGKILL"
        kill -KILL "$failaudio_pid" 2>/dev/null
    fi
    failaudio_pid=""
}

ensure_pulseaudio() {
    systemctl --user is-active --quiet pulseaudio && return 0
    log "Starting pulseaudio user service..."
    systemctl --user start pulseaudio
}

wait_for_sink() {
    for _ in $(seq 1 10); do
        pactl list sinks short 2>/dev/null | grep -q "$SINK_NAME" && return 0
        sleep 1
    done
    return 1
}

start_failaudio() {
    log "Starting failaudio -> $SINK_NAME"
    "$FAILAUDIO" &
    failaudio_pid=$!
}

cleanup() {
    log "Caught signal, shutting down."
    stop_failaudio
    exit 0
}
trap cleanup INT TERM

log "Watching for bluetooth device $BT_MAC (poll every ${POLL_INTERVAL}s)"

while true; do
    if is_bt_connected; then
        ensure_pulseaudio

        if wait_for_sink; then
            pactl set-default-sink "$SINK_NAME" 2>/dev/null
        else
            log "Warning: sink $SINK_NAME did not appear after connecting"
        fi

        if ! is_failaudio_running; then
            start_failaudio
        fi
    else
        if is_failaudio_running; then
            log "Device disconnected, shutting down failaudio"
            stop_failaudio
        fi

        log "Device not connected, attempting to connect..."
        timeout 15 bluetoothctl connect "$BT_MAC" >/dev/null 2>&1 || true
    fi

    sleep "$POLL_INTERVAL"
done
