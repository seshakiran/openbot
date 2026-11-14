#!/usr/bin/env python3
"""Bounded publishers and an idempotent posting ledger for AspireAI."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path("~/.config/aspireai-social-manager/config.json").expanduser()
DEFAULT_DATABASE = Path("~/.local/share/aspireai-social-manager/posts.sqlite3").expanduser()
FINAL_STATES = {"completed", "failed", "uncertain"}


class PublisherError(RuntimeError):
    pass


def now_ms() -> int:
    return int(time.time() * 1000)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PublisherError(f"Could not read JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise PublisherError(f"The JSON root in {path} must be an object.")
    return value


def load_config(path: Path) -> dict[str, Any]:
    value = load_json(path)
    targets = value.get("targets")
    if not isinstance(targets, dict):
        raise PublisherError("The config needs a targets object.")
    for name in (
        "whatsappNews",
        "whatsappPodcasts",
        "whatsappAnnouncements",
        "discordNews",
        "discordPodcasts",
        "discordAnnouncements",
    ):
        if not isinstance(targets.get(name), str) or not targets[name].strip():
            raise PublisherError(f"The config target {name} is missing.")
    for section in ("site", "x", "discord", "podcast"):
        item = value.get(section)
        if not isinstance(item, dict) or not isinstance(item.get("enabled"), bool):
            raise PublisherError(f"The config section {section} needs an enabled boolean.")
    return value


def connect_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS publications (
          content_id TEXT NOT NULL,
          channel TEXT NOT NULL,
          status TEXT NOT NULL,
          remote_id TEXT,
          reason TEXT,
          created_at INTEGER NOT NULL,
          updated_at INTEGER NOT NULL,
          PRIMARY KEY (content_id, channel)
        )
        """
    )
    return connection


def reserve(connection: sqlite3.Connection, content_id: str, channel: str) -> None:
    validate_identifier(content_id, "content ID")
    validate_identifier(channel, "channel")
    timestamp = now_ms()
    try:
        with connection:
            connection.execute(
                "INSERT INTO publications(content_id, channel, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (content_id, channel, "sending", timestamp, timestamp),
            )
    except sqlite3.IntegrityError as error:
        row = connection.execute(
            "SELECT status, remote_id FROM publications WHERE content_id = ? AND channel = ?",
            (content_id, channel),
        ).fetchone()
        status = row["status"] if row else "unknown"
        remote_id = row["remote_id"] if row and row["remote_id"] else "none"
        raise PublisherError(
            f"Publication refused: {content_id} already has status {status} for {channel}; remote ID: {remote_id}."
        ) from error


def set_state(
    connection: sqlite3.Connection,
    content_id: str,
    channel: str,
    status: str,
    *,
    remote_id: str | None = None,
    reason: str | None = None,
) -> None:
    if status not in FINAL_STATES:
        raise PublisherError(f"Invalid final state: {status}")
    if remote_id is not None and len(remote_id) > 500:
        raise PublisherError("The remote ID is too long.")
    if reason is not None and len(reason) > 500:
        raise PublisherError("The reason is too long.")
    with connection:
        changed = connection.execute(
            """
            UPDATE publications
               SET status = ?, remote_id = ?, reason = ?, updated_at = ?
             WHERE content_id = ? AND channel = ? AND status = 'sending'
            """,
            (status, remote_id, reason, now_ms(), content_id, channel),
        ).rowcount
    if changed != 1:
        raise PublisherError(f"No active reservation exists for {content_id} on {channel}.")


def validate_identifier(value: str, label: str) -> None:
    if not value or len(value) > 200 or any(character in value for character in "\r\n\t"):
        raise PublisherError(f"The {label} is invalid.")


def text_file(path: Path, maximum: int) -> str:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise PublisherError(f"Could not read {path}: {error}") from error
    if not text or len(text) > maximum:
        raise PublisherError(f"The text in {path} must contain 1 to {maximum} characters.")
    return text


def percent(value: str) -> str:
    return urllib.parse.quote(value, safe="~-._")


def x_authorization(method: str, url: str, credentials: dict[str, str]) -> str:
    oauth = {
        "oauth_consumer_key": credentials["api_key"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": credentials["access_token"],
        "oauth_version": "1.0",
    }
    base_parameters = "&".join(f"{percent(key)}={percent(value)}" for key, value in sorted(oauth.items()))
    signature_base = "&".join((method.upper(), percent(url), percent(base_parameters)))
    signing_key = f"{percent(credentials['api_secret'])}&{percent(credentials['access_token_secret'])}"
    signature = base64.b64encode(
        hmac.new(signing_key.encode(), signature_base.encode(), hashlib.sha1).digest()
    ).decode()
    oauth["oauth_signature"] = signature
    values = ", ".join(f'{percent(key)}="{percent(value)}"' for key, value in sorted(oauth.items()))
    return f"OAuth {values}"


def required_environment(names: tuple[str, ...]) -> dict[str, str]:
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise PublisherError(f"Missing environment values: {', '.join(missing)}")
    return {name: os.environ[name] for name in names}


def post_x(config: dict[str, Any], text: str) -> str:
    section = config["x"]
    if not section["enabled"]:
        raise PublisherError("X publishing is disabled in the config.")
    values = required_environment(("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"))
    base = str(section.get("apiBase", "https://api.x.com")).rstrip("/")
    url = f"{base}/2/tweets"
    authorization = x_authorization(
        "POST",
        url,
        {
            "api_key": values["X_API_KEY"],
            "api_secret": values["X_API_SECRET"],
            "access_token": values["X_ACCESS_TOKEN"],
            "access_token_secret": values["X_ACCESS_TOKEN_SECRET"],
        },
    )
    request = urllib.request.Request(
        url,
        data=json.dumps({"text": text}, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Authorization": authorization, "Content-Type": "application/json"},
    )
    timeout = bounded_timeout(section.get("timeoutSeconds"), 30, 5, 120)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    post_id = value.get("data", {}).get("id") if isinstance(value, dict) else None
    if not isinstance(post_id, str) or not post_id:
        raise PublisherError("X accepted the request but returned no post ID.")
    return post_id


def post_discord(config: dict[str, Any], text: str) -> str:
    section = config["discord"]
    if not section["enabled"]:
        raise PublisherError("Direct Discord webhook publishing is disabled in the config.")
    webhook = required_environment(("ASPIREAI_DISCORD_WEBHOOK",))["ASPIREAI_DISCORD_WEBHOOK"]
    separator = "&" if "?" in webhook else "?"
    request = urllib.request.Request(
        f"{webhook}{separator}wait=true",
        data=json.dumps({"content": text}, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    timeout = bounded_timeout(section.get("timeoutSeconds"), 30, 5, 120)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    message_id = value.get("id") if isinstance(value, dict) else None
    if not isinstance(message_id, str) or not message_id:
        raise PublisherError("Discord accepted the request but returned no message ID.")
    return message_id


def command_section(config: dict[str, Any], name: str) -> tuple[list[str], int]:
    section = config[name]
    if not section["enabled"]:
        raise PublisherError(f"{name} is disabled in the config.")
    argv = section.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(value, str) and value for value in argv):
        raise PublisherError(f"The {name} argv must be a non-empty string list.")
    timeout = bounded_timeout(section.get("timeoutSeconds"), 90, 5, 3600)
    return argv, timeout


def run_json_command(config: dict[str, Any], name: str, payload: dict[str, Any]) -> dict[str, Any]:
    argv, timeout = command_section(config, name)
    completed = subprocess.run(
        argv,
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise PublisherError(f"The {name} command exited with status {completed.returncode}.")
    try:
        value = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PublisherError(f"The {name} command returned invalid JSON.") from error
    if not isinstance(value, dict):
        raise PublisherError(f"The {name} command must return a JSON object.")
    return value


def bounded_timeout(value: Any, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise PublisherError(f"A timeout must be between {minimum} and {maximum} seconds.")
    return value


def classify_failure(error: BaseException) -> tuple[str, str]:
    if isinstance(error, urllib.error.HTTPError):
        if 400 <= error.code < 500:
            return "failed", f"The service refused the request with HTTP {error.code}."
        return "uncertain", f"The service returned HTTP {error.code}; delivery is uncertain."
    if isinstance(error, (urllib.error.URLError, TimeoutError, subprocess.TimeoutExpired)):
        return "uncertain", "The connection ended without a confirmed delivery result."
    if isinstance(error, PublisherError):
        return "failed", str(error)
    return "uncertain", "The publication ended without a confirmed delivery result."


def publish_with_ledger(
    connection: sqlite3.Connection,
    content_id: str,
    channel: str,
    operation: Any,
) -> str:
    reserve(connection, content_id, channel)
    try:
        remote_id = operation()
    except BaseException as error:
        status, reason = classify_failure(error)
        set_state(connection, content_id, channel, status, reason=reason)
        raise PublisherError(reason) from error
    set_state(connection, content_id, channel, "completed", remote_id=remote_id)
    return remote_id


def doctor(config: dict[str, Any]) -> list[str]:
    checks = ["config", "targets", "ledger"]
    if config["x"]["enabled"]:
        required_environment(("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"))
        checks.append("x-environment")
    if config["discord"]["enabled"]:
        required_environment(("ASPIREAI_DISCORD_WEBHOOK",))
        checks.append("discord-environment")
    for name in ("site", "podcast"):
        if config[name]["enabled"]:
            argv, _ = command_section(config, name)
            executable = Path(argv[0]).expanduser()
            if executable.is_absolute() and not executable.exists():
                raise PublisherError(f"The {name} executable does not exist: {executable}")
            checks.append(f"{name}-command")
    return checks


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    root.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    commands = root.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor")
    status = commands.add_parser("status")
    status.add_argument("--limit", type=int, default=50)

    for name in ("reserve", "complete", "failed", "uncertain"):
        item = commands.add_parser(name)
        item.add_argument("--content-id", required=True)
        item.add_argument("--channel", required=True)
        if name == "complete":
            item.add_argument("--remote-id", required=True)
        if name in ("failed", "uncertain"):
            item.add_argument("--reason", required=True)

    x = commands.add_parser("post-x")
    x.add_argument("--content-id", required=True)
    x.add_argument("--text-file", required=True, type=Path)

    discord = commands.add_parser("post-discord")
    discord.add_argument("--content-id", required=True)
    discord.add_argument("--channel", required=True)
    discord.add_argument("--text-file", required=True, type=Path)

    site = commands.add_parser("post-site")
    site.add_argument("--content-id", required=True)
    site.add_argument("--kind", required=True, choices=("news", "podcast", "announcement"))
    site.add_argument("--payload", required=True, type=Path)

    podcast = commands.add_parser("generate-podcast")
    podcast.add_argument("--content-id", required=True)
    podcast.add_argument("--payload", required=True, type=Path)
    return root


def main() -> int:
    arguments = parser().parse_args()
    try:
        config = load_config(arguments.config)
        connection = connect_database(arguments.database)
        if arguments.command == "doctor":
            print(json.dumps({"ok": True, "checks": doctor(config)}))
            return 0
        if arguments.command == "status":
            limit = max(1, min(arguments.limit, 500))
            rows = connection.execute(
                "SELECT content_id, channel, status, remote_id, reason, updated_at FROM publications ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            print(json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2))
            return 0
        if arguments.command == "reserve":
            reserve(connection, arguments.content_id, arguments.channel)
            print(json.dumps({"status": "sending"}))
            return 0
        if arguments.command == "complete":
            set_state(
                connection,
                arguments.content_id,
                arguments.channel,
                "completed",
                remote_id=arguments.remote_id,
            )
            print(json.dumps({"status": "completed"}))
            return 0
        if arguments.command in ("failed", "uncertain"):
            set_state(
                connection,
                arguments.content_id,
                arguments.channel,
                arguments.command,
                reason=arguments.reason,
            )
            print(json.dumps({"status": arguments.command}))
            return 0
        if arguments.command == "post-x":
            text = text_file(arguments.text_file, 25_000)
            remote_id = publish_with_ledger(
                connection,
                arguments.content_id,
                "x",
                lambda: post_x(config, text),
            )
        elif arguments.command == "post-discord":
            text = text_file(arguments.text_file, 2_000)
            remote_id = publish_with_ledger(
                connection,
                arguments.content_id,
                arguments.channel,
                lambda: post_discord(config, text),
            )
        elif arguments.command == "post-site":
            payload = load_json(arguments.payload)
            result = publish_with_ledger(
                connection,
                arguments.content_id,
                f"site-{arguments.kind}",
                lambda: command_remote_id(
                    run_json_command(
                        config,
                        "site",
                        {"contentId": arguments.content_id, "kind": arguments.kind, "payload": payload},
                    ),
                    "site",
                ),
            )
            remote_id = result
        elif arguments.command == "generate-podcast":
            payload = load_json(arguments.payload)
            result = run_json_command(
                config,
                "podcast",
                {"contentId": arguments.content_id, "payload": payload},
            )
            output = result.get("output")
            if result.get("verified") is not True or not isinstance(output, str) or not output:
                raise PublisherError("The podcast command did not return a verified output path.")
            output_path = Path(output).expanduser()
            if not output_path.is_file() or output_path.stat().st_size == 0:
                raise PublisherError("The verified podcast output is missing or empty.")
            remote_id = str(output_path)
        else:
            raise PublisherError(f"Unsupported command: {arguments.command}")
        print(json.dumps({"status": "completed", "remoteId": remote_id}, ensure_ascii=False))
        return 0
    except PublisherError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def command_remote_id(value: dict[str, Any], label: str) -> str:
    remote_id = value.get("url") or value.get("id")
    if not isinstance(remote_id, str) or not remote_id:
        raise PublisherError(f"The {label} command returned no URL or ID.")
    return remote_id


if __name__ == "__main__":
    raise SystemExit(main())
