"""The data collection switch (human decision 2026-10-12, HANDOFF issues 173 and 174). The mod console has the same switch on its Control tab.

  python tools/collection.py status
  python tools/collection.py on  [--build esper] [--target 10] ["note"]
  python tools/collection.py off ["note"]

OFF (the default): deaths are development runs and do not count. ON: lives that END while it is on (and whose build starts with --build, when given) are written to the chronicle as
data_collection "on" and count as evidence for the agent (the known-killers lines in its prompt, the generation report). --target is how many lives the human wants this collection to run
for; the console shows the progress. Switch it ON only when the character can operate; switch it OFF when you start working on a new one. The lives before this switch existed never count:
they were played without the defensive systems. The switch is local state in memory/collection.json (never committed).
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
import death_stats  # noqa: E402


def describe(st):
    if not st["collecting"]:
        return "Data collection: OFF" + (f" ({st['note']})" if st["note"] else "")
    bits = []
    if st["since_generation"]:
        bits.append(f"since generation {st['since_generation']}")
    if st["build"]:
        bits.append(f"build {st['build']}*")
    if st["target"]:
        bits.append(f"target {st['target']} lives")
    return "Data collection: ON" + (" (" + ", ".join(bits) + ")" if bits else "") + (f" - {st['note']}" if st["note"] else "")


def main(argv):
    args = list(argv[1:])
    cmd = (args.pop(0) if args else "status").lower()
    build, target, words = "", None, []
    while args:
        a = args.pop(0)
        if a == "--build" and args:
            build = args.pop(0)
        elif a == "--target" and args:
            try:
                target = int(args.pop(0))
            except ValueError:
                target = None
        else:
            words.append(a)
    note = " ".join(words)
    if cmd in ("on", "off"):
        since = None
        if cmd == "on":
            try:
                with open(os.path.join(REPO, "memory", "generation_counter.json"), encoding="utf-8") as f:
                    since = int(json.load(f).get("highest", 0)) + 1
            except (OSError, ValueError):
                since = None
        st = death_stats.set_collecting(cmd == "on", note, since_generation=since, build=build, target=target)
        print(describe(st))
    else:
        print(describe(death_stats.collection_state()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
