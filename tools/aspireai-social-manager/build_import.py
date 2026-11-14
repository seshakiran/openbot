#!/usr/bin/env python3
"""Build the AspireAI OpenBot import archive."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT.parents[1] / ".openbot-build" / "aspireai-social-manager" / "aspireai-social-manager.zip"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    manifest_path = ROOT / "openbot-import.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "openbot-agent-import" or manifest.get("version") != 1:
        raise SystemExit("The OpenBot import manifest is invalid.")
    sources = [manifest_path]
    agents = ROOT / "agents"
    sources.extend(path for path in agents.rglob("*") if path.is_file() and not path.is_symlink())
    unsafe = [path for path in sources if path.name.startswith(".env") or "private" in path.name.lower()]
    if unsafe:
        raise SystemExit(f"Refused unsafe import paths: {', '.join(str(path) for path in unsafe)}")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    part = arguments.output.with_suffix(arguments.output.suffix + ".part")
    with zipfile.ZipFile(part, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(sources):
            archive.write(path, path.relative_to(ROOT).as_posix())
    part.replace(arguments.output)
    print(arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
