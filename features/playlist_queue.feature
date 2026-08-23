Feature: Queue management
  Tracks can be enqueued to change playback order without touching
  the underlying playlist order.

  Background:
    Given a playlist with the tracks "a.mp3", "b.mp3", "c.mp3"

  Scenario: Enqueuing a track adds it to the queue
    When I enqueue "b.mp3"
    Then the queue should contain, in order: "b.mp3"

  Scenario: Enqueuing the same track twice does not duplicate it
    When I enqueue "b.mp3"
    And I enqueue "b.mp3"
    Then the queue should contain, in order: "b.mp3"

  Scenario: Enqueuing a track not yet in the playlist adds it to both
    Given an empty playlist
    When I enqueue "new.mp3"
    Then track "new.mp3" should be in the playlist
    And the queue should contain, in order: "new.mp3"

  Scenario: Enqueuing multiple tracks preserves order
    When I enqueue "c.mp3"
    And I enqueue "a.mp3"
    Then the queue should contain, in order: "c.mp3", "a.mp3"

  Scenario: Dequeuing removes a track from the queue only
    Given "b.mp3" is enqueued
    When I dequeue "b.mp3"
    Then the queue should be empty
    And track "b.mp3" should be in the playlist

  Scenario: Dequeuing a track that isn't queued is a no-op
    When I dequeue "b.mp3"
    Then the queue should be empty

  Scenario: Toggling the queue enqueues an unqueued track
    When I toggle the queue for "a.mp3"
    Then the queue should contain, in order: "a.mp3"

  Scenario: Toggling the queue dequeues a queued track
    Given "a.mp3" is enqueued
    When I toggle the queue for "a.mp3"
    Then the queue should be empty

  Scenario: Clearing the queue removes all entries but keeps the playlist
    Given "a.mp3" is enqueued
    And "c.mp3" is enqueued
    When I clear the queue
    Then the queue should be empty
    And the playlist should contain, in order: "a.mp3", "b.mp3", "c.mp3"

  Scenario: Randomizing enqueues every unqueued track exactly once
    When I randomize the queue
    Then the queue should contain "a.mp3", "b.mp3", "c.mp3" in any order

  Scenario: Randomizing does not requeue a track that is already queued
    Given "b.mp3" is enqueued
    When I randomize the queue
    Then "b.mp3" should be at queue position 1
    And the queue should contain "a.mp3", "b.mp3", "c.mp3" in any order
