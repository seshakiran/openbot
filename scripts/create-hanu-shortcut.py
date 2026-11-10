#!/usr/bin/env python3
"""Create a credential-free iPhone shortcut that opens an existing Hanu chat."""
import argparse
import plistlib
import re
from pathlib import Path
from urllib.parse import urlencode


def identifier(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise argparse.ArgumentTypeError("Use an existing OpenBot identifier, not a URL or credential.")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True, type=identifier)
    parser.add_argument("--agent", required=True, type=identifier)
    parser.add_argument("--output", type=Path, default=Path(".openbot/Ask Hanu.unsigned.shortcut"))
    args = parser.parse_args()
    url = "openbot://live-activity?" + urlencode({"server": args.server, "agent": args.agent})
    shortcut = {
        "WFWorkflowName": "Ask Hanu",
        "WFWorkflowClientVersion": "4046.0.2.2",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": 4282601983, "WFWorkflowIconGlyphNumber": 61440},
        "WFWorkflowTypes": [],
        "WFWorkflowInputContentItemClasses": [],
        "WFWorkflowActions": [
            {"WFWorkflowActionIdentifier": "is.workflow.actions.url", "WFWorkflowActionParameters": {"WFURLActionURL": url}},
            {"WFWorkflowActionIdentifier": "is.workflow.actions.openurl", "WFWorkflowActionParameters": {}},
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as target:
        plistlib.dump(shortcut, target, fmt=plistlib.FMT_BINARY)
    args.output.chmod(0o600)
    print(f"Created {args.output}. Sign with Apple's shortcuts sign command before import.")


if __name__ == "__main__":
    main()
