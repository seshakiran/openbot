#!/usr/bin/env python3
"""Private OpenAI-compatible speech adapter. Voice by Underdog Woof."""
import argparse
import hmac
import io
import json
import os
import re
import sys
import threading
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MODEL_ID = "underdog-woof-tts"
MAX_TEXT = 4000


def spoken_text(text):
    depth, offset, parts = 0, 0, []
    for tag in re.finditer(r"</?(?:think|thinking|analysis|reasoning)\b[^>]*>", text, re.I):
        if depth == 0:
            parts.append(text[offset:tag.start()])
        depth = max(0, depth - 1) if tag[0].startswith("</") else depth + 1
        offset = tag.end()
        if depth == 0:
            parts.append(" ")
    if depth == 0:
        parts.append(text[offset:])
    text = "".join(parts)
    return re.sub(r"\btokens?\s*/\s*(?:seconds?|secs?|s)\b", "tokens per second", text, flags=re.I).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-directory", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--port", type=int, default=3112)
    args = parser.parse_args()
    key = args.key_file.read_text().strip()
    if len(key) < 32:
        parser.error("The API key must have at least 32 characters.")
    if args.key_file.stat().st_mode & 0o077:
        parser.error("The key file must be readable only by its owner (chmod 600).")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    sys.path.insert(0, str(args.model_directory.resolve()))
    import numpy as np
    from underdog_woof import Woof
    models = {}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *unused):
            # Never log URLs, headers, voice text or credentials.
            pass

        def answer(self, status, body, content_type="application/json"):
            if not isinstance(body, bytes):
                body = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Voice-Attribution", "Voice by Underdog Woof")
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            supplied = self.headers.get("Authorization", "")
            if hmac.compare_digest(supplied.encode(), ("Bearer " + key).encode()):
                return True
            self.answer(401, {"error": {"message": "Authentication required"}})
            return False

        def do_GET(self):
            if self.path == "/health":
                self.answer(200, {"status": "ready", "attribution": "Voice by Underdog Woof"})
                return
            if not self.authorized():
                return
            if self.path == "/v1/models":
                self.answer(200, {"data": [{"id": MODEL_ID, "object": "model", "task": "text-to-speech"}]})
            elif self.path in ("/v1/audio/voices", "/v1/audio/speech/voices"):
                self.answer(200, {"voices": ["juno", "mira"]})
            else:
                self.answer(404, {"error": {"message": "Not found"}})

        def do_POST(self):
            if not self.authorized():
                return
            if self.path != "/v1/audio/speech":
                self.answer(404, {"error": {"message": "Not found"}})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 32768:
                    raise ValueError()
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError()
                text = body.get("input")
                voice = body.get("voice", "juno")
                if (not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT
                        or voice not in ("juno", "mira") or body.get("model") != MODEL_ID
                        or body.get("response_format", "wav") != "wav"):
                    raise ValueError()
                text = spoken_text(text)
                if not text:
                    raise ValueError()
            except (ValueError, TypeError, UnicodeError):
                self.answer(400, {"error": {"message": "Invalid speech request"}})
                return
            if not lock.acquire(blocking=False):
                self.answer(429, {"error": {"message": "Voice server is busy"}})
                return
            try:
                if voice not in models:
                    models[voice] = Woof(voice=voice)
                audio = models[voice](text, seed=0)
                pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
                output = io.BytesIO()
                with wave.open(output, "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(24000)
                    wav.writeframes(pcm)
                self.answer(200, output.getvalue(), "audio/wav")
            except Exception:
                self.answer(500, {"error": {"message": "Speech generation failed"}})
            finally:
                lock.release()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Woof speech server ready on 127.0.0.1:{args.port}. Voice by Underdog Woof.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
