"""QudAI paths: the one place that knows where the game keeps its data (AGENTS.md section 5: no user-specific absolute paths scattered over the code).

The exchange folder is where the mod and the brain pass state.json / action.json. It is the game's data folder for the current Windows user:
    %USERPROFILE%\\AppData\\LocalLow\\Freehold Games\\CavesOfQud\\QudAI
Set QUDAI_EXCHANGE_DIR to use another folder (the test suite points it at a temp dir so it can never touch the real game files).
The C# mod cannot import this file; it builds the same path from the user profile (AIBrainPart.cs, `ExchangeDir`).
"""
import os

DEFAULT_EXCHANGE_DIR = os.path.join(os.path.expanduser("~"), "AppData", "LocalLow", "Freehold Games", "CavesOfQud", "QudAI")
EXCHANGE_DIR = os.environ.get("QUDAI_EXCHANGE_DIR") or DEFAULT_EXCHANGE_DIR
