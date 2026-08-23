Feature: Basic playlist management
  As a user of failplay
  I want to add, insert, and remove tracks from the playlist
  So that I can build up what I want to listen to

  Scenario: Appending tracks adds them in order
    Given an empty playlist
    When I append "a.mp3" to the playlist
    And I append "b.mp3" to the playlist
    And I append "c.mp3" to the playlist
    Then the playlist should contain, in order: "a.mp3", "b.mp3", "c.mp3"
    And the playlist should contain 3 tracks

  Scenario: Appending the same track twice is a no-op
    Given an empty playlist
    When I append "a.mp3" to the playlist
    And I append "a.mp3" to the playlist
    Then the playlist should contain 1 track
    And the playlist should contain, in order: "a.mp3"

  Scenario: Inserting a track places it before the given position
    Given a playlist with the tracks "a.mp3", "b.mp3", "c.mp3"
    When I insert "x.mp3" at position 1
    Then the playlist should contain, in order: "a.mp3", "x.mp3", "b.mp3", "c.mp3"

  Scenario: Inserting a track that is already in the playlist is a no-op
    Given a playlist with the tracks "a.mp3", "b.mp3"
    When I insert "a.mp3" at position 1
    Then the playlist should contain, in order: "a.mp3", "b.mp3"

  Scenario: Removing a track shrinks the playlist
    Given a playlist with the tracks "a.mp3", "b.mp3", "c.mp3"
    When I remove "b.mp3" from the playlist
    Then the playlist should contain, in order: "a.mp3", "c.mp3"
    And track "b.mp3" should not be in the playlist

  Scenario: Removing a track that is also enqueued dequeues it first
    Given a playlist with the tracks "a.mp3", "b.mp3", "c.mp3"
    And "b.mp3" is enqueued
    When I remove "b.mp3" from the playlist
    Then the queue should be empty
    And track "b.mp3" should not be in the playlist

  Scenario: Removing a track that isn't there is a no-op
    Given a playlist with the tracks "a.mp3"
    When I remove "z.mp3" from the playlist
    Then the playlist should contain, in order: "a.mp3"

  Scenario: The title is parsed from the file name without extension
    Given a playlist with the tracks "My Song.mp3"
    Then the title of "My Song.mp3" should be "My Song"

  Scenario: Membership can be checked directly
    Given a playlist with the tracks "a.mp3"
    Then track "a.mp3" should be in the playlist
    And track "z.mp3" should not be in the playlist

  Scenario: A freshly created playlist is not dirty
    Given an empty playlist
    Then the playlist should not be dirty

  Scenario: Appending a track marks the playlist dirty
    Given an empty playlist
    When I append "a.mp3" to the playlist
    Then the playlist should be dirty

  Scenario: Saving the playlist clears the dirty flag
    Given a playlist with the tracks "a.mp3"
    When I save the playlist to "playlist.pls"
    Then the playlist should not be dirty
