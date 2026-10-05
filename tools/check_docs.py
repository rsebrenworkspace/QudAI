#!/usr/bin/env python3
"""
check_docs.py - cheap doc-drift detector for the QudAI repo.

Run from the repo root:   python tools/check_docs.py

Hard checks (exit code 1 if they fail):
  1. Every [HarmonyPatch(typeof(X), "Y")] in AIBrainPart.cs is listed in docs/ARCHITECTURE.md
     between <!-- patches:start --> and <!-- patches:end -->, and vice versa.
  2. Every command handled in ExecuteCommand is listed between <!-- actions:start --> and
     <!-- actions:end -->, and vice versa.

Soft checks (warnings only):
  3. Test count: highest "Test N" found in dry_run.py vs <!-- tests-max: N --> in ARCHITECTURE.md (if present).
  4. Hard-coded absolute user paths in .py/.cs files.
  5. docs/HANDOFF.md 'handoff-updated' date older than the newest git commit.
  6. Stray build artifacts (*.dll) in the repo root.

Limitations: regex based, so unusual code formatting can be missed. It checks that docs and code
*mention* the same things, not that the descriptions are correct.
"""
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CS_FILE = ROOT / "mod" / "QudAIBrain" / "AIBrainPart.cs"
ARCH = ROOT / "docs" / "ARCHITECTURE.md"
HANDOFF = ROOT / "docs" / "HANDOFF.md"
DRY_RUN = ROOT / "dry_run.py"

errors = []
warnings = []


def read(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None


def block(text, name):
    m = re.search(rf"<!--\s*{name}:start\s*-->(.*?)<!--\s*{name}:end\s*-->", text, re.S)
    return m.group(1) if m else None


def short_type(t):
    return t.split(".")[-1]


def check_patches(cs, arch):
    code = set()
    for m in re.finditer(r'\[HarmonyPatch\(\s*typeof\(\s*([\w\.]+)\s*\)\s*,\s*"(\w+)"', cs):
        code.add(f"{short_type(m.group(1))}.{m.group(2)}")

    section = block(arch, "patches")
    if section is None:
        errors.append("ARCHITECTURE.md is missing the <!-- patches:start/end --> block")
        return
    documented = set()
    # Table rows look like: | `PatchClass` | `Type.Method` | purpose |   (Target is the 2nd column)
    for line in section.splitlines():
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 2:
            continue
        m = re.fullmatch(r"`([A-Za-z_]\w*(?:\.\w+)+)`", cols[1])
        if m:
            typ, meth = m.group(1).rsplit(".", 1)
            documented.add(f"{short_type(typ)}.{meth}")

    for p in sorted(code - documented):
        errors.append(f"Patch in code but not documented: {p}")
    for p in sorted(documented - code):
        errors.append(f"Patch documented but not in code: {p}")
    print(f"patches: {len(code)} in code, {len(documented)} documented")


def check_actions(cs, arch):
    # Isolate ExecuteCommand to avoid matching unrelated string comparisons elsewhere.
    start = cs.find("static void ExecuteCommand")
    end = cs.find("static void ExecuteAutoexplore")
    body = cs[start:end] if start != -1 and end != -1 and end > start else cs

    code = set()
    for m in re.finditer(r'\bact\s*==\s*"([A-Z_]+)"', body):
        code.add(m.group(1))
    for m in re.finditer(r'\bact\.StartsWith\(\s*"([A-Z_]+)', body):
        code.add(m.group(1).rstrip("_"))
    for m in re.finditer(r'ToUpper\(\)\s*==\s*"([A-Z_]+)"', body):
        code.add(m.group(1))
    # MOVE_ is handled via act.StartsWith("MOVE_") in some versions; make sure it is present.
    if re.search(r'StartsWith\(\s*"MOVE_"', body):
        code.add("MOVE")

    section = block(arch, "actions")
    if section is None:
        errors.append("ARCHITECTURE.md is missing the <!-- actions:start/end --> block")
        return
    documented = set()
    # A command token is an ALL-CAPS identifier right after a backtick, not followed by a letter
    # (so `AutoAct.TryFindPathStep` is not mistaken for a command).
    for m in re.finditer(r"`([A-Z][A-Z_]*)(?![A-Za-z])", section):
        documented.add(m.group(1).rstrip("_"))
    # Aliases are documented in prose; treat the alias commands as optional.
    optional = {"FORCE_ATTACK", "ATTACK_CELL"}

    # The code sometimes handles a whole family with one prefix check
    # (e.g. act.StartsWith("AUTOLEVEL") covers AUTOLEVEL_STAT, AUTOLEVEL_SKILL, ...).
    def covered(token, others):
        return any(token == o or token.startswith(o) or o.startswith(token) for o in others)

    for a in sorted(code - optional):
        if not covered(a, documented):
            errors.append(f"Command in code but not documented: {a}")
    for a in sorted(documented - optional):
        if not covered(a, code):
            errors.append(f"Command documented but not found in ExecuteCommand: {a}")
    print(f"actions: {len(code)} in code, {len(documented)} documented")


def check_tests(arch):
    dry = read(DRY_RUN)
    if dry is None:
        warnings.append("dry_run.py not found; skipped test-count check")
        return
    nums = [int(n) for n in re.findall(r"\bTest\s+(\d+)", dry, re.I)]
    if not nums:
        warnings.append("Could not find 'Test N' markers in dry_run.py; test-count check skipped")
        return
    code_max = max(nums)
    m = re.search(r"<!--\s*tests-max:\s*(\d+)\s*-->", arch)
    if not m:
        warnings.append(f"dry_run.py has tests up to {code_max}; add <!-- tests-max: {code_max} --> to ARCHITECTURE.md")
    elif int(m.group(1)) != code_max:
        warnings.append(f"Docs say tests-max {m.group(1)} but dry_run.py has {code_max}")
    # README claims
    readme = read(ROOT / "README.md") or ""
    for claim in re.findall(r"(\d+)-scenario", readme):
        if int(claim) != code_max:
            warnings.append(f"README.md says {claim}-scenario suite; dry_run.py has up to Test {code_max}")


def check_paths():
    pat = re.compile(r"[A-Z]:\\\\?Users\\\\?\w+", re.I)
    for f in list(ROOT.glob("*.py")) + list(ROOT.glob("mod/**/*.cs")):
        text = read(f) or ""
        hits = len(pat.findall(text))
        if hits:
            warnings.append(f"{f.relative_to(ROOT)}: {hits} hard-coded user path(s); move to one config")


def check_handoff_date():
    text = read(HANDOFF)
    if text is None:
        warnings.append("docs/HANDOFF.md not found")
        return
    m = re.search(r"<!--\s*handoff-updated:\s*(\d{4}-\d{2}-\d{2})\s*-->", text)
    if not m:
        warnings.append("HANDOFF.md has no <!-- handoff-updated: YYYY-MM-DD --> marker")
        return
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs"], cwd=ROOT,
                             capture_output=True, text=True, timeout=10)
        last_commit = out.stdout.strip()
        if last_commit and last_commit > m.group(1):
            warnings.append(f"HANDOFF.md last updated {m.group(1)} but newest commit is {last_commit}")
    except Exception:
        pass  # git unavailable; not an error


def check_artifacts():
    dlls = [p.name for p in ROOT.glob("*.dll")]
    if dlls:
        warnings.append(f"Build artifacts in repo root (move to scratch/ and git-ignore): {', '.join(dlls)}")


def main():
    cs = read(CS_FILE)
    arch = read(ARCH)
    if cs is None:
        errors.append(f"Missing {CS_FILE.relative_to(ROOT)}")
    if arch is None:
        errors.append(f"Missing {ARCH.relative_to(ROOT)}")
    if cs is not None and arch is not None:
        check_patches(cs, arch)
        check_actions(cs, arch)
        check_tests(arch)
    check_paths()
    check_handoff_date()
    check_artifacts()

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
        sys.exit(1)
    print(f"\nOK ({len(warnings)} warning(s))")


if __name__ == "__main__":
    main()
