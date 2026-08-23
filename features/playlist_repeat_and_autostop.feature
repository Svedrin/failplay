Feature: Repeat and AutoStop
  A single track can be marked to repeat indefinitely, and a single
  track can be marked as the last one to play before playback stops.

  Background:
    Given a playlist with the tracks "a.mp3", "b.mp3", "c.mp3"

  Scenario: Advancing without any special track walks the list in order
    When I advance to the next track
    Then the current track should be "a.mp3"
    When I advance to the next track
    Then the current track should be "b.mp3"
    When I advance to the next track
    Then the current track should be "c.mp3"

  Scenario: The playlist loops back to the start when nothing is marked
    Given the playlist is currently playing "c.mp3"
    When I advance to the next track
    Then the current track should be "a.mp3"

  Scenario: Marking a track to repeat keeps playback on it
    Given the playlist is currently playing "b.mp3"
    And "b.mp3" is set to repeat
    When I advance to the next track
    Then the current track should be "b.mp3"
    When I advance to the next track
    Then the current track should be "b.mp3"

  Scenario: Toggling repeat off again releases the track
    Given the playlist is currently playing "b.mp3"
    And "b.mp3" is set to repeat
    When I toggle repeat for "b.mp3"
    And I advance to the next track
    Then the current track should be "c.mp3"

  Scenario: Setting repeat on a new track releases the previous one
    Given "a.mp3" is set to repeat
    When I toggle repeat for "b.mp3"
    Then "b.mp3" should be marked as repeat
    And "a.mp3" should not be marked as repeat

  Scenario: AutoStop ends playback once the marked track has played
    Given the playlist is currently playing "b.mp3"
    And "b.mp3" is set to stop after
    When I advance to the next track
    Then playback should stop with a message mentioning "stop after"

  Scenario: AutoStop is a one-shot: it is cleared once triggered
    Given the playlist is currently playing "b.mp3"
    And "b.mp3" is set to stop after
    When I advance to the next track
    Then no track should be marked as stop-after

  Scenario: AutoStop set on a queued track takes effect once it is reached
    Given the playlist is currently playing "a.mp3"
    And "c.mp3" is enqueued
    And "c.mp3" is set to stop after
    When I advance to the next track
    Then the current track should be "c.mp3"
    When I advance to the next track
    Then playback should stop with a message mentioning "stop after"

  Scenario: The queue takes priority over the plain playlist order
    Given the playlist is currently playing "a.mp3"
    And "c.mp3" is enqueued
    When I advance to the next track
    Then the current track should be "c.mp3"
    And the queue should be empty

  Scenario: Repeat takes priority over the queue
    Given the playlist is currently playing "a.mp3"
    And "a.mp3" is set to repeat
    And "c.mp3" is enqueued
    When I advance to the next track
    Then the current track should be "a.mp3"
    And the queue should contain, in order: "c.mp3"

  Scenario: Peeking the next track does not change playback state
    Given the playlist is currently playing "a.mp3"
    When I peek the next track
    Then the peeked track should be "b.mp3"
    And the current track should be "a.mp3"

  Scenario: Peeking respects AutoStop by returning nothing
    Given the playlist is currently playing "a.mp3"
    And "a.mp3" is set to stop after
    When I peek the next track
    Then there should be no peeked track

  Scenario: Peeking respects the queue
    Given the playlist is currently playing "a.mp3"
    And "c.mp3" is enqueued
    When I peek the next track
    Then the peeked track should be "c.mp3"

  Scenario: Advancing an empty playlist stops immediately
    Given an empty playlist
    When I advance to the next track
    Then playback should stop with a message mentioning "No songs"

  Scenario: Tracks missing from disk are skipped when advancing
    Given the playlist is currently playing "a.mp3"
    And track "b.mp3" is missing from disk
    When I advance to the next track
    Then the current track should be "c.mp3"
