#!/usr/bin/env python3
"""
Test Audio Playback API Endpoint

These are manual, opt-in checks against a LIVE backend. They POST to
http://localhost:8008, and ``/api/v1/audio/play`` drives real audio hardware, so
they are marked ``@pytest.mark.slow`` and are excluded by the default
``pytest -m "not slow"`` run. Start the backend first (``python run.py serve``),
then opt in with ``pytest -m slow`` or run this file directly as a script.

They skip cleanly when the backend is not listening and fail loudly on an
unexpected status or a malformed body. Previously every code path returned a
bool that pytest discarded, so the tests could never fail no matter what the
server did.
"""

import json
import sys
import time
from datetime import datetime

import pytest
import requests


def _excerpt(text, limit=200):
    """Truncate a response body so a failure message stays readable."""
    body = (text or "").strip()
    return body if len(body) <= limit else body[:limit] + "..."


def _check_success_body(endpoint, response, body, required, expected=None):
    """Assert the endpoint returned its documented success body.

    A 200 carrying a well-formed but wrong body — an empty ``{}``, or a
    ``{"status": "error"}`` envelope, or a bare ``{"detail": ...}`` — is still
    a failure. The contract asserted here is read from
    ``backend/app/api/v1/endpoints/audio.py``; no field is invented.
    """
    if not isinstance(body, dict):
        pytest.fail(f"{endpoint}: expected a JSON object, got {type(body).__name__}: {_excerpt(response.text)}")

    missing = [key for key in required if key not in body]
    if missing:
        pytest.fail(f"{endpoint}: body missing {missing} (status {response.status_code}): {_excerpt(response.text)}")

    for key, value in (expected or {}).items():
        if body[key] != value:
            pytest.fail(
                f"{endpoint}: expected {key}={value!r}, got {body[key]!r} "
                f"(status {response.status_code}): {_excerpt(response.text)}"
            )
    return body


@pytest.mark.slow
def test_audio_generate():
    """Test audio generation endpoint first.

    Opt-in: requires the backend running on localhost:8008 (marked ``slow``).
    Skips if the backend is down, fails on a bad status or a non-JSON body.
    """

    # API endpoint
    url = "http://localhost:8008/api/v1/audio/generate"

    # Test payload
    payload = {
        "frequency": 528,
        "duration": 5,
        "volume": 0.8,
        "prayer_bowl_mode": True,
        "harmonic_strength": 0.3,
        "modulation_depth": 0.05,
    }

    # Headers
    headers = {"Content-Type": "application/json"}

    print("Testing Audio Generation API")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 50)

    try:
        # Send POST request
        print(f"Sending POST request to {url}...")
        start_time = time.time()

        response = requests.post(url, json=payload, headers=headers, timeout=10)

        end_time = time.time()
        response_time = end_time - start_time

        print(f"Response received in {response_time:.2f} seconds")
        print(f"Status Code: {response.status_code}")

        # Check if request was successful
        if response.status_code == 200:
            print("SUCCESS: Audio generation endpoint returned 200 OK")

            # Parse response
            try:
                response_data = response.json()
                print(f"Response Data: {json.dumps(response_data, indent=2)}")

                # Check for expected fields
                if "status" in response_data:
                    print(f"Status field found: {response_data['status']}")
                else:
                    print("WARNING: No 'status' field in response")

                if "message" in response_data:
                    print(f"Message field found: {response_data['message']}")
                else:
                    print("WARNING: No 'message' field in response")

            except json.JSONDecodeError:
                print("WARNING: Response is not valid JSON")
                print(f"Raw Response: {response.text}")
                pytest.fail(
                    f"/api/v1/audio/generate: response is not valid JSON "
                    f"(status {response.status_code}): {_excerpt(response.text)}"
                )

            # A 200 is not sufficient: the body must match the contract in
            # backend/app/api/v1/endpoints/audio.py (generate_audio success body).
            _check_success_body(
                "/api/v1/audio/generate",
                response,
                response_data,
                required=("status", "message", "config", "audio_generated", "samples"),
                expected={"status": "success", "audio_generated": True},
            )

        else:
            print(f"ERROR: Expected 200 OK, got {response.status_code}")
            print(f"Response: {response.text}")
            pytest.fail(
                f"/api/v1/audio/generate: expected 200 OK, got {response.status_code}: {_excerpt(response.text)}"
            )

    except requests.exceptions.ConnectionError:
        print("ERROR: Connection failed - is the server running?")
        pytest.skip("backend not running on localhost:8008")

    except requests.exceptions.Timeout:
        print("ERROR: Request timed out")
        pytest.fail("Request to /api/v1/audio/generate timed out")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request failed: {e}")
        pytest.fail(f"Request to /api/v1/audio/generate failed: {e}")

    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        pytest.fail(f"Unexpected error calling /api/v1/audio/generate: {e}")


@pytest.mark.slow
def test_audio_playback():
    """Test audio playback endpoint.

    Opt-in: requires the backend running on localhost:8008 (marked ``slow``).
    This one POSTs ``hardware_level`` to the playback endpoint, so it drives
    real audio hardware. Skips if the backend is down, fails otherwise.
    """

    # API endpoint
    url = "http://localhost:8008/api/v1/audio/play"

    # Test payload
    payload = {"hardware_level": 2}

    # Headers
    headers = {"Content-Type": "application/json"}

    print("\nTesting Audio Playback API")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 50)

    try:
        # Send POST request
        print(f"Sending POST request to {url}...")
        start_time = time.time()

        response = requests.post(url, json=payload, headers=headers, timeout=10)

        end_time = time.time()
        response_time = end_time - start_time

        print(f"Response received in {response_time:.2f} seconds")
        print(f"Status Code: {response.status_code}")

        # Check if request was successful
        if response.status_code == 200:
            print("SUCCESS: Audio playback endpoint returned 200 OK")

            # Parse response
            try:
                response_data = response.json()
                print(f"Response Data: {json.dumps(response_data, indent=2)}")

                # Check for expected fields
                if "status" in response_data:
                    print(f"Status field found: {response_data['status']}")
                else:
                    print("WARNING: No 'status' field in response")

                if "message" in response_data:
                    print(f"Message field found: {response_data['message']}")
                else:
                    print("WARNING: No 'message' field in response")

            except json.JSONDecodeError:
                print("WARNING: Response is not valid JSON")
                print(f"Raw Response: {response.text}")
                pytest.fail(
                    f"/api/v1/audio/play: response is not valid JSON "
                    f"(status {response.status_code}): {_excerpt(response.text)}"
                )

            # play_audio success body; hardware_level echoes the request.
            _check_success_body(
                "/api/v1/audio/play",
                response,
                response_data,
                required=("status", "message", "hardware_level", "audio_duration", "audio_samples"),
                expected={"status": "success", "hardware_level": payload["hardware_level"]},
            )

        else:
            print(f"ERROR: Expected 200 OK, got {response.status_code}")
            print(f"Response: {response.text}")
            pytest.fail(f"/api/v1/audio/play: expected 200 OK, got {response.status_code}: {_excerpt(response.text)}")

    except requests.exceptions.ConnectionError:
        print("ERROR: Connection failed - is the server running?")
        pytest.skip("backend not running on localhost:8008")

    except requests.exceptions.Timeout:
        print("ERROR: Request timed out")
        pytest.fail("Request to /api/v1/audio/play timed out")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request failed: {e}")
        pytest.fail(f"Request to /api/v1/audio/play failed: {e}")

    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        pytest.fail(f"Unexpected error calling /api/v1/audio/play: {e}")


@pytest.mark.slow
def test_audio_status():
    """Test audio status endpoint to verify playback state.

    Opt-in: requires the backend running on localhost:8008 (marked ``slow``).
    Skips if the backend is down, fails on an unexpected status.
    """

    url = "http://localhost:8008/api/v1/audio/status"

    print("\nTesting Audio Status Endpoint")
    print(f"URL: {url}")
    print("-" * 50)

    try:
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            print(f"Status endpoint returned {response.status_code}")
            pytest.fail(f"/api/v1/audio/status: expected 200 OK, got {response.status_code}: {_excerpt(response.text)}")

        print("Audio status endpoint working")
        response_data = response.json()
        print(f"Status Response: {json.dumps(response_data, indent=2)}")

        # get_audio_status success body; has_audio/spectrum_available are bools.
        _check_success_body(
            "/api/v1/audio/status",
            response,
            response_data,
            required=("status", "has_audio", "audio_duration", "spectrum_available", "timestamp"),
            expected={"status": "success"},
        )
        for key in ("has_audio", "spectrum_available"):
            if not isinstance(response_data[key], bool):
                pytest.fail(
                    f"/api/v1/audio/status: expected {key} to be a bool, got {response_data[key]!r} "
                    f"(status {response.status_code}): {_excerpt(response.text)}"
                )

    except requests.exceptions.ConnectionError:
        print("ERROR: Connection failed - is the server running?")
        pytest.skip("backend not running on localhost:8008")

    except requests.exceptions.Timeout:
        print("ERROR: Request timed out")
        pytest.fail("Request to /api/v1/audio/status timed out")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request failed: {e}")
        pytest.fail(f"Request to /api/v1/audio/status failed: {e}")

    except json.JSONDecodeError:
        print("ERROR: Status response is not valid JSON")
        print(f"Raw Response: {response.text}")
        pytest.fail(f"/api/v1/audio/status: response is not valid JSON: {_excerpt(response.text)}")

    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        pytest.fail(f"Unexpected error calling /api/v1/audio/status: {e}")


def main():
    """Main test function"""
    print("Vajra.Stream Audio Playback Test")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)

    # These tests no longer report a bool; they raise on failure and skip when
    # the backend is down, so the summary is derived from the raised outcome.
    checks = (
        ("Audio Generation", test_audio_generate),
        ("Audio Playback", test_audio_playback),
        ("Audio Status", test_audio_status),
    )

    outcomes = {}
    for label, check in checks:
        try:
            check()
        except pytest.skip.Exception as exc:
            outcomes[label] = f"SKIPPED ({exc})"
        except pytest.fail.Exception as exc:
            outcomes[label] = f"FAILED ({exc})"
        except Exception as exc:
            outcomes[label] = f"FAILED ({exc})"
        else:
            outcomes[label] = "PASSED"

    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)

    for label, outcome in outcomes.items():
        print(f"{label} Test: {outcome}")

    overall_success = all(outcome == "PASSED" for outcome in outcomes.values())

    if overall_success:
        print("\nOVERALL RESULT: ALL TESTS PASSED")
        print("Audio playback functionality is working correctly")
        return 0
    else:
        print("\nOVERALL RESULT: SOME TESTS FAILED")
        print("Audio playback functionality needs attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
