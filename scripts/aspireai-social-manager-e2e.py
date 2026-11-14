#!/usr/bin/env python3
"""Build and exercise the AspireAI social-manager package without network access."""

from __future__ import annotations

import json
import subprocess
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "tools" / "aspireai-social-manager"
PUBLISHER = (
    PACKAGE
    / "agents"
    / "aspireai-social-manager"
    / "skills"
    / "aspireai-social-manager"
    / "scripts"
    / "aspireai_publisher.py"
)


def run(*arguments: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(arguments, text=True, capture_output=True, check=False)
    if completed.returncode != expected:
        raise AssertionError(
            f"Command returned {completed.returncode}, expected {expected}: {' '.join(arguments)}\n"
            f"stdout: {completed.stdout}\nstderr: {completed.stderr}"
        )
    return completed


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aspireai-social-manager-") as temporary:
        temp = Path(temporary)
        archive = temp / "aspireai-social-manager.zip"
        run("python3", str(PACKAGE / "build_import.py"), "--output", str(archive))
        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
            assert "openbot-import.json" in names
            assert (
                "agents/aspireai-social-manager/skills/aspireai-social-manager/SKILL.md" in names
            )
            manifest = json.loads(bundle.read("openbot-import.json"))
            assert manifest["format"] == "openbot-agent-import"
            assert len(manifest["agents"][0]["routines"]) == 7
            assert all(not routine["active"] for routine in manifest["agents"][0]["routines"])

        config = temp / "config.json"
        config.write_text(
            (PACKAGE / "agents" / "aspireai-social-manager" / "skills" / "aspireai-social-manager"
             / "references" / "config.example.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        database = temp / "posts.sqlite3"
        base = ("python3", str(PUBLISHER), "--config", str(config), "--database", str(database))
        doctor = run(*base, "doctor")
        assert json.loads(doctor.stdout)["ok"] is True
        run(*base, "reserve", "--content-id", "news:2026-11-13:morning:test", "--channel", "whatsapp-news")
        duplicate = run(
            *base,
            "reserve",
            "--content-id",
            "news:2026-11-13:morning:test",
            "--channel",
            "whatsapp-news",
            expected=1,
        )
        assert "already has status sending" in duplicate.stderr
        run(
            *base,
            "complete",
            "--content-id",
            "news:2026-11-13:morning:test",
            "--channel",
            "whatsapp-news",
            "--remote-id",
            "test-message-id",
        )
        status = json.loads(run(*base, "status").stdout)
        assert status[0]["status"] == "completed"
        assert status[0]["remote_id"] == "test-message-id"

        report = {
            "archive": str(archive),
            "files": len(names),
            "routines": len(manifest["agents"][0]["routines"]),
            "ledger": status[0],
        }
        output = ROOT / ".openbot-build" / "aspireai-social-manager" / "e2e-report.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
