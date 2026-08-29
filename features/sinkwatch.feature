@dbus
Feature: Automatic exit when the PulseAudio sink disappears
  --stop-on-sink-disconnect makes fail{play,blaster} watch PulseAudio's DBus
  interface for the sink they're playing through - a specific one, if
  PULSE_SINK names it, otherwise whatever the current default is - going
  away, and exit with a distinct code when that happens, instead of quietly
  continuing on whatever fallback sink PulseAudio picks next.

  Scenario: Without a usable session bus, the watchdog stays inactive
    Given the DBus session bus is unreachable
    When I create a sink watchdog
    Then the sink watchdog should not be active

  Scenario: Without the QtDBus module, the watchdog stays inactive
    Given the QtDBus module is unavailable
    When I create a sink watchdog
    Then the sink watchdog should not be active

  Scenario: With a session bus but no PulseAudio DBus interface, the watchdog stays inactive
    Given a real DBus session bus is available
    When I create a sink watchdog
    Then the sink watchdog should not be active

  Scenario: With no configured sink name, the watchdog watches the default sink
    Given a fake PulseAudio with sinks "alsa_output.builtin", "bluez_output.headset"
    And the default sink is "alsa_output.builtin"
    When I create a sink watchdog
    Then the sink watchdog should be active
    And it should be watching "alsa_output.builtin"

  Scenario: A configured sink name overrides the default
    Given a fake PulseAudio with sinks "alsa_output.builtin", "bluez_output.headset"
    And the default sink is "alsa_output.builtin"
    When I create a sink watchdog configured for "bluez_output.headset"
    Then the sink watchdog should be active
    And it should be watching "bluez_output.headset"

  Scenario: A configured sink name that doesn't exist leaves the watchdog inactive
    Given a fake PulseAudio with sinks "alsa_output.builtin"
    When I create a sink watchdog configured for "nonexistent_sink"
    Then the sink watchdog should not be active

  Scenario: No configured sink name and no default sink leaves the watchdog inactive
    Given a fake PulseAudio with sinks "alsa_output.builtin", "bluez_output.headset"
    When I create a sink watchdog
    Then the sink watchdog should not be active

  Scenario: The watched sink disappearing reports it gone
    Given a fake PulseAudio with sinks "alsa_output.builtin", "bluez_output.headset"
    And the default sink is "alsa_output.builtin"
    And a sink watchdog has been created
    When "alsa_output.builtin" is removed
    Then the sink watchdog should report the sink gone

  Scenario: An unrelated sink disappearing does not report anything
    Given a fake PulseAudio with sinks "alsa_output.builtin", "bluez_output.headset"
    And the default sink is "alsa_output.builtin"
    And a sink watchdog has been created
    When "bluez_output.headset" is removed
    Then the sink watchdog should not report the sink gone
