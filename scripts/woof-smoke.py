#!/usr/bin/env python3
"""Check the running Woof adapter with synthetic text; no credentials are printed."""
import argparse
import io
import json
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base-url", default="http://127.0.0.1:3112")
parser.add_argument("--key-file", type=Path, default=Path(".openbot/woof-api-key"))
parser.add_argument("--output", type=Path, default=Path(".openbot-build/woof-smoke"))
args = parser.parse_args()
key = args.key_file.read_text().strip()


def request(path, body=None, auth=True):
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(args.base_url + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


assert request("/v1/models", auth=False)[0] == 401
status, body = request("/v1/models")
assert status == 200 and json.loads(body)["data"][0]["task"] == "text-to-speech"
status, body = request("/v1/audio/voices")
assert status == 200 and json.loads(body)["voices"] == ["juno", "mira"]
assert request("/v1/audio/speech", {"model": "wrong", "input": "Test", "voice": "juno"})[0] == 400
assert request("/v1/audio/speech", {"model": "underdog-woof-tts", "input": "<think>Hidden.</think>", "voice": "juno"})[0] == 400
started = time.monotonic()
status, audio = request("/v1/audio/speech", {"model": "underdog-woof-tts", "input": "<think>Do not say this.</think>Hello. I am Hanu. The speed is 117 tokens/sec.", "voice": "juno", "response_format": "wav"})
assert status == 200, f"Speech request failed with HTTP {status}"
with wave.open(io.BytesIO(audio), "rb") as wav:
    assert wav.getframerate() == 24000 and wav.getnchannels() == 1 and wav.getsampwidth() == 2
    duration = wav.getnframes() / wav.getframerate()
    assert duration > 0
args.output.mkdir(parents=True, exist_ok=True)
(args.output / "hanu-juno.wav").write_bytes(audio)
(args.output / "report.json").write_text(json.dumps({"passed": True, "attribution": "Voice by Underdog Woof", "audioSeconds": duration, "requestSeconds": round(time.monotonic()-started, 3), "checks": ["authentication required", "model and voice discovery", "invalid requests refused", "reasoning-only text refused", "24 kHz mono PCM WAV"]}, indent=2))
print(f"Woof smoke passed. Voice by Underdog Woof. Report and synthetic sample: {args.output}")
