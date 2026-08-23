Feature: Persisting the playlist to a PLS file
  The playlist, queue, current track, and the repeat / stop-after
  markers can be saved to a .pls file and loaded back later.

  Scenario: Saving and reloading an untouched playlist round-trips
    Given a playlist with the tracks "a.mp3", "b.mp3", "c.mp3"
    When I save the playlist to "playlist.pls"
    And I load a fresh playlist from "playlist.pls"
    Then the playlist should contain, in order: "a.mp3", "b.mp3", "c.mp3"

  Scenario: Saving and reloading preserves current, repeat, stop-after and queue
    Given a playlist with the tracks "a.mp3", "b.mp3", "c.mp3"
    And the playlist is currently playing "b.mp3"
    And "b.mp3" is set to repeat
    And "c.mp3" is set to stop after
    And "a.mp3" is enqueued
    When I save the playlist to "playlist.pls"
    And I load a fresh playlist from "playlist.pls"
    Then the current track should be "b.mp3"
    And "b.mp3" should be marked as repeat
    And "c.mp3" should be marked as stop-after
    And the queue should contain, in order: "a.mp3"

  Scenario: Loading a playlist file replaces whatever was loaded before
    Given a playlist with the tracks "x.mp3", "y.mp3"
    And a pls file "new.pls" containing the tracks "a.mp3", "b.mp3", "c.mp3"
    When I load the playlist from "new.pls"
    Then the playlist should contain, in order: "a.mp3", "b.mp3", "c.mp3"
    And track "x.mp3" should not be in the playlist

  Scenario: Saving over an existing file creates a backup copy
    Given a playlist with the tracks "a.mp3"
    When I save the playlist to "playlist.pls"
    And I save the playlist to "playlist.pls"
    Then a backup file "playlist.pls~" should exist

  Scenario: Loading a playlist that references a file missing from disk still adds it
    Given a pls file "broken.pls" containing the tracks "a.mp3", "b.mp3"
    And track "b.mp3" is missing from disk
    When I load the playlist from "broken.pls"
    Then track "b.mp3" should be in the playlist
    And the playlist should contain, in order: "a.mp3", "b.mp3"
