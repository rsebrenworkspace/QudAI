#!/usr/bin/env python3
"""
git_report.py - read-only git health report for the QudAI repo.

Run from anywhere inside the repo:   python tools/git_report.py
Paste the output into chat (or hand it to Claude Code) instead of running ten separate commands.

It NEVER changes anything: no add, commit, checkout, reset, clean, stash, or push. It only runs
read-only git commands and prints what it finds, with a suggested next step for common situations.
"""
import os
import subprocess
import sys

GAME_DATA_PREFIXES = ("memory/", "chronicles/")
ARTIFACT_EXTS = (".dll", ".exe", ".pyc", ".pdb")


def git(*args, raw=False):
    """Run a read-only git command. raw=True keeps leading whitespace (needed for `git status --porcelain`,
    where a leading space is part of the status code)."""
    try:
        p = subprocess.run(["git", *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
    except FileNotFoundError:
        print("git was not found on PATH. Install Git for Windows (https://git-scm.com/downloads/win).")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        return 1, "timed out"
    return p.returncode, (p.stdout.rstrip() if raw else p.stdout.strip())


def main():
    rc, root = git("rev-parse", "--show-toplevel")
    if rc != 0:
        print("Not inside a git repository. cd into D:\\QudAI first.")
        sys.exit(1)
    os.chdir(root)
    notes, actions = [], []

    print(f"=== git report: {root} ===")

    # --- branch / upstream / ahead-behind --------------------------------
    rc, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    detached = branch == "HEAD"
    rc, head = git("log", "-1", "--format=%h %s")
    print(f"Branch:   {'(DETACHED HEAD)' if detached else branch}")
    print(f"Last:     {head or '(no commits yet)'}")
    if detached:
        actions.append("You are on a detached HEAD. Switch back with: git switch main")

    rc, upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    ahead = behind = 0
    if rc == 0 and upstream:
        rc2, counts = git("rev-list", "--left-right", "--count", "@{u}...HEAD")
        if rc2 == 0 and counts:
            behind, ahead = (int(x) for x in counts.split())
        print(f"Upstream: {upstream}  (ahead {ahead}, behind {behind})")
        if ahead and behind:
            actions.append("Diverged from GitHub: run `git pull --no-rebase`, then `git push`.")
        elif ahead:
            actions.append("You have commits GitHub does not: run `git push`.")
        elif behind:
            actions.append("GitHub has commits you do not: run `git pull`.")
    else:
        print("Upstream: none (this branch is not tracking a GitHub branch)")
        if not detached:
            actions.append(f"Publish this branch with: git push -u origin {branch}")

    # --- in-progress operations -------------------------------------------
    rc, gitdir = git("rev-parse", "--absolute-git-dir")
    in_progress = []
    for marker, label in (("MERGE_HEAD", "merge"), ("rebase-merge", "rebase"),
                          ("rebase-apply", "rebase/am"), ("CHERRY_PICK_HEAD", "cherry-pick"),
                          ("REVERT_HEAD", "revert")):
        if gitdir and os.path.exists(os.path.join(gitdir, marker)):
            in_progress.append(label)
    rc, conflicts = git("diff", "--name-only", "--diff-filter=U")
    conflict_files = [c for c in conflicts.splitlines() if c]
    if in_progress:
        print(f"IN PROGRESS: {', '.join(in_progress)}")
        actions.append("An operation is half-finished. Do not start anything new. Paste this report so we can finish or abort it safely.")
    if conflict_files:
        print("CONFLICTS in: " + ", ".join(conflict_files))

    # --- working tree ------------------------------------------------------
    rc, status = git("status", "--porcelain=v1", "-uall", raw=True)
    entries = [l for l in status.splitlines() if l]
    staged = [e for e in entries if e[0] not in " ?" and e[0] != "!"]
    unstaged = [e for e in entries if e[1] not in " ?" and not e.startswith("??")]
    untracked = [e for e in entries if e.startswith("??")]
    print(f"\nWorking tree: {len(staged)} staged, {len(unstaged)} modified-unstaged, {len(untracked)} untracked")
    for e in entries[:14]:
        path = e[3:].replace("\\", "/")
        tag = "  [GAME DATA: do not discard]" if path.startswith(GAME_DATA_PREFIXES) else ""
        print(f"  {e[:2]} {path}{tag}")
    if len(entries) > 14:
        print(f"  ... and {len(entries) - 14} more")
    if staged and not conflict_files:
        actions.append("Staged changes are waiting: commit them with `git commit -m \"message\"`, or `git restore --staged <file>` to unstage.")
    if not entries and not in_progress:
        notes.append("Working tree is clean.")

    # --- stash -------------------------------------------------------------
    rc, stash = git("stash", "list")
    stash_lines = [s for s in stash.splitlines() if s]
    if stash_lines:
        print(f"\nStash: {len(stash_lines)} entr{'y' if len(stash_lines) == 1 else 'ies'} (parked changes, not lost)")
        for s in stash_lines[:3]:
            print("  " + s)

    # --- branches ------------------------------------------------------------
    rc, refs = git("for-each-ref", "--format=%(refname:short)\t%(upstream:short)\t%(upstream:track)", "refs/heads")
    base = "main"
    rc, has_main = git("rev-parse", "--verify", "--quiet", "main")
    if rc != 0:
        rc, has_master = git("rev-parse", "--verify", "--quiet", "master")
        base = "master" if rc == 0 else None
    print("\nLocal branches:")
    for line in refs.splitlines():
        parts = line.split("\t")
        name = parts[0]
        up = parts[1] if len(parts) > 1 and parts[1] else "no upstream"
        track = parts[2] if len(parts) > 2 else ""
        extra = ""
        if base and name != base:
            rc, n = git("rev-list", "--count", f"{base}..{name}")
            if rc == 0 and n.isdigit() and int(n) > 0:
                extra = f"  <- {n} commit(s) NOT on {base} yet"
                actions.append(f"Branch `{name}` has work that is not on {base}. Merge it with a pull request on GitHub.")
        marker = "*" if name == branch else " "
        print(f"  {marker} {name:<28} {up} {track}{extra}")

    # --- recent history ------------------------------------------------------
    rc, log = git("log", "--oneline", "-5")
    if log:
        print("\nRecent commits:")
        for l in log.splitlines():
            print("  " + l[:110])

    # --- repo health -----------------------------------------------------------
    rc, co = git("count-objects", "-v")
    info = dict(line.split(": ", 1) for line in co.splitlines() if ": " in line)
    pp = int(info.get("prune-packable", "0") or 0)
    garbage = int(info.get("garbage", "0") or 0)
    print("\nRepo health:")
    print(f"  loose objects: {info.get('count', '?')}, packs: {info.get('packs', '?')}, garbage: {garbage}, prune-packable: {pp}")
    if garbage:
        actions.append("`garbage` is nonzero. Paste this report; do not delete anything in .git by hand.")
    if pp:
        notes.append("prune-packable > 0 is harmless leftovers (often from Windows holding .git folders open). With Antigravity/Claude Code/File Explorer/GitHub Desktop closed, `git prune-packed` cleans it. If it prompts to retry, answer n or press Ctrl+C.")

    rc, autocrlf = git("config", "core.autocrlf")
    rc, uname = git("config", "user.name")
    rc, uemail = git("config", "user.email")
    rc, remote = git("remote", "get-url", "origin")
    rc, attrs = git("ls-files", ".gitattributes")
    print(f"  core.autocrlf: {autocrlf or '(unset)'} | .gitattributes: {'yes' if attrs else 'no'} | remote: {remote or '(none)'}")
    if not uname or not uemail:
        actions.append("Git does not know who you are. Run: git config --global user.name \"Your Name\" and git config --global user.email \"you@example.com\"")

    rc, tracked = git("ls-files")
    artifacts = [f for f in tracked.splitlines() if f.lower().endswith(ARTIFACT_EXTS)]
    if artifacts:
        notes.append("Tracked build artifacts: " + ", ".join(artifacts[:6]) +
                     ". Adding them to .gitignore does NOT untrack them; use `git rm --cached <file>` (or `git mv` into scratch/).")

    # --- summary -----------------------------------------------------------------
    print("\n--- Summary ---")
    seen = set()
    for a in actions:
        if a not in seen:
            seen.add(a)
            print("NEXT: " + a)
    for n in notes:
        print("NOTE: " + n)
    if not actions and not notes:
        print("Nothing to do.")
    elif not actions:
        print("Nothing urgent.")
    print("(This report changed nothing.)")


if __name__ == "__main__":
    main()
