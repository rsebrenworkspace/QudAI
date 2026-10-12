"""The data collection switch (human decision 2026-10-12, HANDOFF issue 173).

  python tools/collection.py status
  python tools/collection.py on  "Dream Tortoise can operate: uses abilities, retreats, heals"
  python tools/collection.py off "working on the next character"

OFF (the default): deaths are development runs and do not count. ON: lives that END while it is on are written to the chronicle as data_collection "on" and count as evidence for the agent
(the known-killers lines in its prompt, the generation report). Switch it ON only when the character can operate; switch it OFF when you start working on a new one. The lives before this
switch existed never count: they were played without the defensive systems.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
import death_stats  # noqa: E402


def main(argv):
    cmd = (argv[1] if len(argv) > 1 else "status").lower()
    note = argv[2] if len(argv) > 2 else ""
    if cmd in ("on", "off"):
        since = None
        if cmd == "on":
            try:
                with open(os.path.join(REPO, "memory", "generation_counter.json"), encoding="utf-8") as f:
                    since = int(json.load(f).get("highest", 0)) + 1
            except (OSError, ValueError):
                since = None
        st = death_stats.set_collecting(cmd == "on", note, since_generation=since)
        print(f"Data collection is now {'ON' if st['collecting'] else 'OFF'}" + (f" (lives that end from generation {st['since_generation']} count)" if st["collecting"] and st["since_generation"] else "") + ".")
    else:
        st = death_stats.collection_state()
        print(f"Data collection: {'ON' if st['collecting'] else 'OFF'}" + (f" since generation {st['since_generation']}" if st["collecting"] and st["since_generation"] else "") + (f" ({st['note']})" if st["note"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
