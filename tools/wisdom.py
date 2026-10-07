"""List, approve and reject the ancestral lessons (memory/ancestral_wisdom.json).

Only approved lessons are shown to the combat model (chronicler.format_ancestral_memory_for_prompt). New lessons start unapproved.

    python tools/wisdom.py                 list every lesson with its generation number and status
    python tools/wisdom.py approve 14 16   approve generations 14 and 16
    python tools/wisdom.py reject 15       withdraw approval from generation 15
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chronicler  # noqa: E402


def main(argv):
    wisdom = chronicler.load_ancestral_wisdom()
    if len(argv) >= 2 and argv[0] in ("approve", "reject"):
        gens = {int(x) for x in argv[1:] if x.isdigit()}
        changed = []
        for w in wisdom:
            if w.get("generation") in gens:
                w["approved"] = (argv[0] == "approve")
                changed.append(w["generation"])
        chronicler.save_ancestral_wisdom(wisdom)
        print(f"{argv[0]}d generations: {sorted(changed) or 'none matched'}")
    for w in wisdom:
        mark = "APPROVED" if w.get("approved") is True else "hidden  "
        print(f"[{mark}] Gen {w.get('generation')}: {w.get('lesson')}")
        print(f"            died to: {str(w.get('death_reason'))[:110]}")


if __name__ == "__main__":
    main(sys.argv[1:])
