"""Stands in for claude.exe in tests. Behaviour is chosen with FAKE_CLAUDE_* variables.

It records what it was given (arguments, working folder, stdin, the system prompt
file) so tests can check what the real program would have received.
"""

import json
import os
import sys
import time
from pathlib import Path

argv = sys.argv[1:]
stdin = sys.stdin.read()
prompt = argv[argv.index("-p") + 1] if "-p" in argv else stdin
mode = os.environ.get("FAKE_CLAUDE_MODE", "ok")

if record := os.environ.get("FAKE_CLAUDE_RECORD"):
    system = ""
    if "--system-prompt-file" in argv:
        system_file = Path(argv[argv.index("--system-prompt-file") + 1])
        system = system_file.read_text(encoding="utf-8")
    Path(record).write_text(
        json.dumps(
            {
                "argv": argv,
                "cwd": os.getcwd(),
                "files": sorted(os.listdir()),
                "stdin": stdin,
                "prompt": prompt,
                "system": system,
            }
        ),
        encoding="utf-8",
    )

if mode == "sleep":
    time.sleep(1.5)
    Path(os.environ["FAKE_CLAUDE_DONE"]).write_text("finished", encoding="utf-8")

if mode == "garbage":
    print("this is not json")
    sys.exit(0)

envelope: dict[str, object] = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "stop_reason": "end_turn",
    "result": "OK",
}
if "--json-schema" in argv:
    schema = json.loads(argv[argv.index("--json-schema") + 1])
    if schema.get("title") == "Ruling":  # the clerk's question
        envelope["structured_output"] = {
            "reason": "Written as a joke.",
            "hear_as": os.environ.get("FAKE_CLAUDE_REGISTER", "play"),
        }
    else:
        envelope["structured_output"] = {
            "read": "Noted.",
            "band": "sound",
            "nudge": 2,
            "line": "Fine by me.",
        }
if mode == "error":
    envelope.update(subtype="error", is_error=True, result="Not logged in. Please run /login")
elif mode == "refusal":
    envelope["stop_reason"] = "refusal"
    envelope.pop("structured_output", None)
elif mode == "no_structured":
    envelope.pop("structured_output", None)

print(json.dumps(envelope))
