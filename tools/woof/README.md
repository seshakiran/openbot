# Woof speech server

Voice by Underdog Woof. Optional personal-use CPU speech output for OpenBot.
The model and its code are from [ConwayResearch/Underdog-Woof](https://huggingface.co/ConwayResearch/Underdog-Woof).
They are not vendored here. Keep their LICENSE and NOTICE with each local download.
Woof is English text-to-speech, not speech recognition or an agent model.

The tested model revision is `be702960539777fc3f698e54335276a8391b00f9`.
The local environment uses Python 3.11 and NumPy 2.4.6. Weights, environment, API
key, settings and generated audio stay in ignored `.openbot/` or `.openbot-build/`.

## Local setup

Download the repository at the revision above into `.openbot/woof-model`, including
`underdog_woof/`, `woof_int8.npz`, LICENSE and NOTICE. With the Hugging Face CLI:

```sh
hf download ConwayResearch/Underdog-Woof \
  --revision be702960539777fc3f698e54335276a8391b00f9 \
  --local-dir .openbot/woof-model
python3.11 -m venv .openbot/woof-venv
.openbot/woof-venv/bin/python -m pip install numpy==2.4.6
```

Generate a private key locally, once. Never overwrite a key used by a phone:

```sh
python3 - <<'PY'
from pathlib import Path
import secrets
p = Path('.openbot/woof-api-key')
with p.open('x', opener=lambda path, flags: __import__('os').open(path, flags, 0o600)) as f:
    f.write(secrets.token_urlsafe(32) + '\n')
PY
```

Run the server:

```sh
.openbot/woof-venv/bin/python tools/woof/server.py \
  --model-directory .openbot/woof-model --key-file .openbot/woof-api-key
```

It binds only to `127.0.0.1:3112`. GET `/health` has no credentials. Model and voice
discovery and synthesis require Bearer authentication. The adapter accepts only
`underdog-woof-tts`, `juno` or `mira`, and WAV output. Audio is 24 kHz mono PCM16.
It does not log text, headers or credentials. One synthesis runs at a time; another
request gets 429. Tagged reasoning is removed and `tokens/sec` is expanded before
synthesis. This does not identify untagged reasoning or commentary.

## iPhone over Tailscale

Inspect `tailscale serve status` first. With unused HTTPS port 8445:

```sh
tailscale serve --bg --https=8445 http://127.0.0.1:3112
```

In OpenBot on the iPhone, Settings > Voice > Voice server:

- Address: `https://YOUR-MAC.YOUR-TAILNET.ts.net:8445/v1`.
- API key: copy the value from local `.openbot/woof-api-key` into the phone's form.
- Connect, then select speech model `underdog-woof-tts` and voice `juno` or `mira`.
- Enable speech output only. Keep the phone recognizer for listening; this adapter
  does not provide transcription. Choose Voice server as the speaking engine.
- Keep GPT live voice off to use this voice with the agent's existing LLM.

Keep the Mac awake, this process running and Tailscale connected. Existing phone
pairing and the other Tailscale services do not change. Stop the process with
Ctrl-C; remove only this endpoint with `tailscale serve --https=8445 off`.

## Checks and limits

```sh
bun scripts/speech-text-e2e.ts
python3 scripts/woof-smoke.py
```

The smoke check uses synthetic text, checks authentication and discovery, then
writes a WAV and report under `.openbot-build/woof-smoke`. The same check accepts
`--base-url https://YOUR-MAC.YOUR-TAILNET.ts.net:8445` to verify private HTTPS.
No user session or agent turn is used.

The shared speech formatter removes tagged reasoning. The adapter also removes tags if they reach it. An older phone formatter can
remove the tags while retaining their contents before the adapter sees the text;
the adapter cannot safely identify that flattened reasoning. Mobile source also stops reading
progress commentary and waits for a completed final answer; that behavior and
in-app Woof attribution require an updated phone build. They cannot be installed
by restarting the Mac. The installed phone must be configured by its user.

Use the required "Voice by Underdog Woof" attribution in the app and in published
samples. The model has its own noncommercial license, separate from the adapter's
repository license; commercial use requires permission from Underdog. Do not use
its output for model training. Consult the downloaded LICENSE for the full terms.
