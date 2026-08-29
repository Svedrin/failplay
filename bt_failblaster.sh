#!/usr/bin/env bash
#
# Watches for the "Logitech BT Adapter" bluetooth speaker. Whenever it's
# available, connects to it, routes PulseAudio to it and runs failblaster
# in the foreground (with --stop-on-sink-disconnect, so it exits itself as
# soon as PulseAudio's DBus interface reports the sink gone) so its curses
# TUI is usable from this terminal. A background watchdog polling
# bluetoothctl is kept as a fallback in case DBus isn't available; once
# failblaster exits (by quitting or being killed), the script goes back to
# waiting for the device.
#
# Intended to be run inside a long-lived tmux session, e.g.:
#   tmux new -s failblaster-bt ./bt_failblaster.sh
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
readonly FAILBLASTER="$SCRIPT_DIR/failblaster.py"
readonly SINK_NAME="bluez_sink.${BT_MAC//:/_}.a2dp_sink"

watchdog_pid=""

log() {
    printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

is_bt_connected() {
    bluetoothctl info "$BT_MAC" 2>/dev/null | grep -q "Connected: yes"
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

stop_watchdog() {
    [[ -n "$watchdog_pid" ]] && kill "$watchdog_pid" 2>/dev/null
    watchdog_pid=""
}

# Runs in the background while failblaster is in the foreground. Kills
# failblaster as soon as the bluetooth device disappears. failblaster isn't
# backgrounded, so we don't have its pid up front; find it by name instead.
start_watchdog() {
    (
        while true; do
            sleep "$POLL_INTERVAL"
            pgrep -f "$FAILBLASTER" >/dev/null 2>&1 || exit 0
            if ! is_bt_connected; then
                pkill -TERM -f "$FAILBLASTER" 2>/dev/null
                exit 0
            fi
        done
    ) &
    watchdog_pid=$!
}

cleanup() {
    log "Caught signal, shutting down."
    stop_watchdog
    pkill -TERM -f "$FAILBLASTER" 2>/dev/null
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

        log "Starting failblaster -> $SINK_NAME"
        start_watchdog
        "$FAILBLASTER" --stop-on-sink-disconnect
        stop_watchdog
        log "failblaster exited"
    else
        log "Device not connected, attempting to connect..."
        timeout 15 bluetoothctl connect "$BT_MAC" >/dev/null 2>&1 || true
        sleep "$POLL_INTERVAL"
    fi
done
