Feature: Index bookkeeping under playlist mutation
  Removing, inserting, and moving tracks must keep the "current",
  "repeat", and "stopafter" markers pointing at the right track, since
  they are stored internally as plain list indices.

  Background:
    Given a playlist with the tracks "a.mp3", "b.mp3", "c.mp3", "d.mp3"

  Scenario: Removing a track before the current one shifts current back
    Given the playlist is currently playing "c.mp3"
    When I remove "a.mp3" from the playlist
    Then the current track should be "c.mp3"

  Scenario: Removing the first track as current clears current
    Given the playlist is currently playing "a.mp3"
    When I remove "a.mp3" from the playlist
    Then there should be no current track

  Scenario: Removing the current track moves current to the previous one
    Given the playlist is currently playing "c.mp3"
    When I remove "c.mp3" from the playlist
    Then the current track should be "b.mp3"

  Scenario: Removing a track after the current one leaves current untouched
    Given the playlist is currently playing "b.mp3"
    When I remove "d.mp3" from the playlist
    Then the current track should be "b.mp3"

  Scenario: Removing the repeated track clears the repeat flag
    Given "b.mp3" is set to repeat
    When I remove "b.mp3" from the playlist
    Then no track should be marked as repeat

  Scenario: Removing a track before the repeated one shifts the flag back
    Given "c.mp3" is set to repeat
    When I remove "a.mp3" from the playlist
    Then "c.mp3" should be marked as repeat

  Scenario: Removing a track after the repeated one leaves the flag untouched
    Given "b.mp3" is set to repeat
    When I remove "d.mp3" from the playlist
    Then "b.mp3" should be marked as repeat

  Scenario: Removing the stop-after track clears the flag
    Given "b.mp3" is set to stop after
    When I remove "b.mp3" from the playlist
    Then no track should be marked as stop-after

  Scenario: Removing a track before the stop-after one shifts the flag back
    Given "c.mp3" is set to stop after
    When I remove "a.mp3" from the playlist
    Then "c.mp3" should be marked as stop-after

  Scenario: Inserting a track before the current one shifts current forward
    Given the playlist is currently playing "b.mp3"
    When I insert "x.mp3" at position 0
    Then the current track should be "b.mp3"

  Scenario: Inserting a track after the current one leaves current untouched
    Given the playlist is currently playing "b.mp3"
    When I insert "x.mp3" at position 3
    Then the current track should be "b.mp3"

  Scenario: Inserting a track before the repeated one shifts the flag forward
    Given "b.mp3" is set to repeat
    When I insert "x.mp3" at position 0
    Then "b.mp3" should be marked as repeat

  Scenario: Inserting a track before the stop-after one shifts the flag forward
    Given "b.mp3" is set to stop after
    When I insert "x.mp3" at position 0
    Then "b.mp3" should be marked as stop-after

  Scenario: Moving the repeated track keeps the flag on it
    Given "b.mp3" is set to repeat
    When I move "b.mp3" to position 3
    Then "b.mp3" should be marked as repeat
    And the playlist should contain, in order: "a.mp3", "c.mp3", "d.mp3", "b.mp3"

  Scenario: Moving the stop-after track keeps the flag on it
    Given "b.mp3" is set to stop after
    When I move "b.mp3" to position 0
    Then "b.mp3" should be marked as stop-after
    And the playlist should contain, in order: "b.mp3", "a.mp3", "c.mp3", "d.mp3"

  Scenario: Moving a track to its own position is a no-op
    When I move "b.mp3" to position 1
    Then the playlist should contain, in order: "a.mp3", "b.mp3", "c.mp3", "d.mp3"
