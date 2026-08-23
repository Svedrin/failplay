Feature: Uploading files into the media library
  The web view can let browsers add new audio files to the library, but
  only once an uploads directory is configured. That directory can be
  named anything and nested at any depth, as long as it lives within the
  music library (the library root itself also qualifies) -- if it's
  outside the library, uploads stay off. Uploaded files must always land
  there, never overwrite an existing file, and only known audio extensions
  are accepted. The uploads directory itself doesn't need to exist ahead
  of time; it's created the first time something is uploaded.

  Background:
    Given a music library containing the files "one.mp3", "two.mp3"
    And a playlist with the tracks "one.mp3", "two.mp3"

  Scenario: Uploads are disabled by default
    Given the web server is running
    When I upload the file "new.mp3" with content "some audio bytes"
    Then the response status should be 403

  Scenario: An uploads directory outside the music library is rejected
    Given the web server is running with an uploads directory outside the media library
    When I upload the file "new.mp3" with content "some audio bytes"
    Then the response status should be 403

  Scenario: An uploads directory that escapes the library via ".." is rejected
    Given the web server is running with uploads enabled in "../escaped-uploads"
    When I upload the file "new.mp3" with content "some audio bytes"
    Then the response status should be 403

  Scenario Outline: An arbitrarily named uploads directory within the library is accepted
    Given the web server is running with uploads enabled in "<relpath>"
    When I upload the file "new.mp3" with content "some audio bytes"
    Then the response status should be 200
    And the uploads directory should contain a file "new.mp3" with content "some audio bytes"

    Examples:
      | relpath           |
      | incoming          |
      | drop-off          |
      | incoming/new      |

  Scenario: The library root itself qualifies as an uploads directory
    Given the web server is running with uploads enabled in the library root
    When I upload the file "new.mp3" with content "some audio bytes"
    Then the response status should be 200
    And the uploads directory should contain a file "new.mp3" with content "some audio bytes"

  Scenario: The state endpoint reports whether uploads are enabled
    Given the web server is running with uploads enabled
    When I GET "/api/state"
    Then the JSON response should report uploads as enabled

  Scenario: The state endpoint reports uploads as disabled when not configured
    Given the web server is running
    When I GET "/api/state"
    Then the JSON response should report uploads as disabled

  Scenario: The uploads directory does not exist until something is uploaded
    Given the web server is running with uploads enabled
    Then the uploads directory should not exist yet

  Scenario: Uploading a file creates the uploads directory and stores the file
    Given the web server is running with uploads enabled
    When I upload the file "new.mp3" with content "some audio bytes"
    Then the response status should be 200
    And the uploads directory should exist
    And the uploads directory should contain a file "new.mp3" with content "some audio bytes"

  Scenario: An uploaded file becomes visible when browsing the uploads directory
    Given the web server is running with uploads enabled
    When I upload the file "new.mp3" with content "some audio bytes"
    And I GET "/api/library?path=<uploads_dir>"
    Then the JSON response should be a list of entries named "new.mp3"

  Scenario: Uploading a file with an unsupported extension is rejected
    Given the web server is running with uploads enabled
    When I upload the file "notes.txt" with content "hello"
    Then the response status should be 400
    And the uploads directory should not contain a file "notes.txt"

  Scenario: Uploading without a filename is rejected
    Given the web server is running with uploads enabled
    When I POST "/api/upload" with raw body "some audio bytes"
    Then the response status should be 400

  Scenario: Uploading a filename containing a path separator is rejected
    Given the web server is running with uploads enabled
    When I upload the file "../evil.mp3" with content "some audio bytes"
    Then the response status should be 400

  Scenario: Uploading a file that already exists is rejected without touching it
    Given the web server is running with uploads enabled
    And a file "dup.mp3" with content "original" already exists in the uploads directory
    When I upload the file "dup.mp3" with content "replacement"
    Then the response status should be 409
    And the uploads directory should contain a file "dup.mp3" with content "original"
