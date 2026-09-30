"""
QudAI Mod Synchronization Utility
Synchronizes mod files between this repository and Caves of Qud's local mod directory.
"""
import os
import shutil
import sys

GAME_MOD_DIR = os.path.expandvars(r"%APPDATA%\..\LocalLow\Freehold Games\CavesOfQud\Mods\QudAIBrain")
REPO_MOD_DIR = os.path.join(os.path.dirname(__file__), "mod", "QudAIBrain")

FILES_TO_SYNC = ["AIBrainPart.cs", "workshop.json"]


def deploy():
    """Copies mod files from repository to Caves of Qud mod folder."""
    if not os.path.exists(GAME_MOD_DIR):
        os.makedirs(GAME_MOD_DIR, exist_ok=True)
    print(f"[Deploy] Syncing from Repo -> Game Mod Folder ({GAME_MOD_DIR})")
    for f in FILES_TO_SYNC:
        src = os.path.join(REPO_MOD_DIR, f)
        dst = os.path.join(GAME_MOD_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  -> Deployed {f}")
        else:
            print(f"  [!] Missing source file: {src}")


def pull():
    """Copies mod files from Caves of Qud mod folder to repository."""
    if not os.path.exists(REPO_MOD_DIR):
        os.makedirs(REPO_MOD_DIR, exist_ok=True)
    print(f"[Pull] Syncing from Game Mod Folder -> Repo ({REPO_MOD_DIR})")
    for f in FILES_TO_SYNC:
        src = os.path.join(GAME_MOD_DIR, f)
        dst = os.path.join(REPO_MOD_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  -> Pulled {f}")
        else:
            print(f"  [!] Missing source file: {src}")


if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "deploy"
    if mode == "pull":
        pull()
    else:
        deploy()
