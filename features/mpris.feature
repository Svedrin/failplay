@dbus
Feature: MPRIS2 desktop integration
  failplay and failblaster can optionally expose themselves as an MPRIS2
  player on the session DBus, so desktop shells (KDE's lock screen media
  widget etc.) can show what's playing and offer a working stop button.
  The feature is entirely best-effort: without a usable DBus, playback
  must keep working exactly as if the MPRIS interface didn't exist.

  Scenario: Without a usable session bus, the interface stays inactive
    Given the DBus session bus is unreachable
    When I create an MPRIS interface for "FailPlay"
    Then the MPRIS interface should not be active

  Scenario: Without the QtDBus module, the interface stays inactive
    Given the QtDBus module is unavailable
    When I create an MPRIS interface for "FailPlay"
    Then the MPRIS interface should not be active

  Scenario: With a session bus available, the interface registers itself
    Given a real DBus session bus is available
    When I create an MPRIS interface for "FailPlay"
    Then the MPRIS interface should be active
    And its DBus service name should be "org.mpris.MediaPlayer2.failplay"

  Scenario: A second instance with the same identity gets a distinct service name
    Given a real DBus session bus is available
    And an MPRIS interface for "FailPlay" is registered
    When I create another MPRIS interface for "FailPlay"
    Then the MPRIS interface should be active
    And its DBus service name should not be "org.mpris.MediaPlayer2.failplay"

  Scenario: The root interface reports identity and honest capabilities
    Given a real DBus session bus is available
    And an MPRIS interface for "FailPlay" is registered
    Then the DBus property "org.mpris.MediaPlayer2" "Identity" should be "FailPlay"
    And the DBus property "org.mpris.MediaPlayer2" "CanQuit" should be "true"
    And the DBus property "org.mpris.MediaPlayer2" "CanRaise" should be "false"

  Scenario: The player interface advertises no seek/skip capabilities
    Given a real DBus session bus is available
    And an MPRIS interface for "FailPlay" is registered
    Then the DBus property "org.mpris.MediaPlayer2.Player" "CanGoNext" should be "false"
    And the DBus property "org.mpris.MediaPlayer2.Player" "CanGoPrevious" should be "false"
    And the DBus property "org.mpris.MediaPlayer2.Player" "CanPlay" should be "false"
    And the DBus property "org.mpris.MediaPlayer2.Player" "CanPause" should be "false"
    And the DBus property "org.mpris.MediaPlayer2.Player" "CanSeek" should be "false"
    And the DBus property "org.mpris.MediaPlayer2.Player" "CanControl" should be "true"

  Scenario: Playback status starts out Stopped
    Given a real DBus session bus is available
    And an MPRIS interface for "FailPlay" is registered
    Then the DBus property "org.mpris.MediaPlayer2.Player" "PlaybackStatus" should be "Stopped"

  Scenario: Playback status becomes Playing when a track starts
    Given a real DBus session bus is available
    And an MPRIS interface for "FailPlay" is registered
    When the player starts playing "Some Song.mp3"
    Then the DBus property "org.mpris.MediaPlayer2.Player" "PlaybackStatus" should be "Playing"

  Scenario: Playback status returns to Stopped when playback stops
    Given a real DBus session bus is available
    And an MPRIS interface for "FailPlay" is registered
    And the player starts playing "Some Song.mp3"
    When the player stops
    Then the DBus property "org.mpris.MediaPlayer2.Player" "PlaybackStatus" should be "Stopped"

  Scenario: Metadata reflects the currently playing track
    Given a real DBus session bus is available
    And an MPRIS interface for "FailPlay" is registered
    When the player starts playing "Some Song.mp3" by "Some Artist" from "Some Album"
    Then the DBus Metadata property should contain title "Some Song"
    And the DBus Metadata property should contain artist "Some Artist"
    And the DBus Metadata property should contain album "Some Album"

  Scenario: Calling Stop over DBus stops playback and requests the app quit
    Given a real DBus session bus is available
    And an MPRIS interface for "FailPlay" is registered
    When I call "Stop" on the DBus player interface
    Then the player should have been stopped
    And the quit callback should have been called

  Scenario: Calling Quit on the root interface also stops playback
    Given a real DBus session bus is available
    And an MPRIS interface for "FailPlay" is registered
    When I call "Quit" on the DBus root interface
    Then the player should have been stopped
    And the quit callback should have been called

  Scenario: Play/Pause/Next/Previous are accepted but ignored
    Given a real DBus session bus is available
    And an MPRIS interface for "FailPlay" is registered
    When I call "Play" on the DBus player interface
    And I call "Pause" on the DBus player interface
    And I call "Next" on the DBus player interface
    And I call "Previous" on the DBus player interface
    Then the player should not have been stopped
    And the quit callback should not have been called
