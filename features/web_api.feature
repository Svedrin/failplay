Feature: Web interface HTTP API
  failplay exposes a small HTTP API so the playlist can be controlled
  from a browser: browsing the music library, enqueuing/dequeuing,
  toggling repeat/stop-after, randomizing, and clearing the queue.

  Background:
    Given a music library containing the files "one.mp3", "two.mp3", "notes.txt"
    And a playlist with the tracks "one.mp3", "two.mp3"
    And the web server is running

  Scenario: The root page serves the HTML shell
    When I GET "/"
    Then the response status should be 200
    And the response content type should start with "text/html"

  Scenario: The state endpoint reports the playlist
    When I GET "/api/state"
    Then the response status should be 200
    And the JSON response should list the tracks "one.mp3", "two.mp3" in order

  Scenario: Enqueuing a library file over the API adds it to the queue
    When I POST "/api/enqueue" with JSON body {"path": "<one.mp3>"}
    Then the response status should be 200
    And "one.mp3" should be enqueued

  Scenario: Enqueuing a file not yet in the playlist adds it there too
    Given a music library containing the files "three.mp3"
    When I POST "/api/enqueue" with JSON body {"path": "<three.mp3>"}
    Then track "three.mp3" should be in the playlist
    And "three.mp3" should be enqueued

  Scenario: Dequeuing removes a track from the queue only
    Given "one.mp3" is enqueued
    When I POST "/api/dequeue" with JSON body {"path": "<one.mp3>"}
    Then the queue should be empty
    And track "one.mp3" should be in the playlist

  Scenario: Toggling repeat on a known track marks it
    When I POST "/api/repeat" with JSON body {"path": "<one.mp3>"}
    Then "one.mp3" should be marked as repeat

  Scenario: Toggling repeat on a track that is not in the playlist is ignored
    Given a music library containing the files "ghost.mp3"
    When I POST "/api/repeat" with JSON body {"path": "<ghost.mp3>"}
    Then the response status should be 200
    And no track should be marked as repeat

  Scenario: Toggling stop-after on a known track marks it
    When I POST "/api/stopafter" with JSON body {"path": "<two.mp3>"}
    Then "two.mp3" should be marked as stop-after

  Scenario: Toggling stop-after on a track that is not in the playlist is ignored
    Given a music library containing the files "ghost.mp3"
    When I POST "/api/stopafter" with JSON body {"path": "<ghost.mp3>"}
    Then the response status should be 200
    And no track should be marked as stop-after

  Scenario: Randomizing enqueues every track exactly once
    When I POST "/api/randomize"
    Then the queue should contain "one.mp3", "two.mp3" in any order

  Scenario: Clearing the queue empties it without touching the playlist
    Given "one.mp3" is enqueued
    And "two.mp3" is enqueued
    When I POST "/api/clearqueue"
    Then the queue should be empty
    And the playlist should contain, in order: "one.mp3", "two.mp3"

  Scenario: Enqueuing without a path is rejected
    When I POST "/api/enqueue" with JSON body {}
    Then the response status should be 400

  Scenario: Posting invalid JSON is rejected
    When I POST "/api/enqueue" with raw body "not json"
    Then the response status should be 400

  Scenario: Unknown GET routes return 404
    When I GET "/api/nonexistent"
    Then the response status should be 404

  Scenario: Unknown POST routes return 404
    When I POST "/api/nonexistent" with JSON body {"path": "x"}
    Then the response status should be 404

  Scenario: Library browsing lists the audio files in the root
    When I GET "/api/library"
    Then the response status should be 200
    And the JSON response should be a list of entries named "one.mp3, two.mp3"

  Scenario: Library browsing hides files with unsupported extensions
    When I GET "/api/library"
    Then the JSON response should not contain an entry named "notes.txt"

  Scenario: Library browsing lists subdirectories
    Given the music library has a subdirectory "Album"
    When I GET "/api/library"
    Then the JSON response should contain a directory entry named "Album"

  Scenario: Browsing into a subdirectory shows its own contents
    Given the music library has a subdirectory "Album" containing the files "track1.mp3"
    When I GET "/api/library?path=<Album>"
    Then the JSON response should be a list of entries named "track1.mp3"

  Scenario: Path traversal outside the library root is blocked
    When I GET "/api/library?path=../../../../../../etc"
    Then the response status should be 403

  Scenario: The SSE endpoint streams the current state on connect
    When I open the event stream at "/events"
    Then the first SSE event should list the tracks "one.mp3", "two.mp3" in order
