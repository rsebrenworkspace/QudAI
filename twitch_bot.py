import os
import sys
import time
import json
import socket
import ssl
import random
import threading
from collections import Counter

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "twitch_config.json")
from qudai_config import EXCHANGE_DIR  # noqa: E402  (one config for the paths: qudai_config.py)
VOTES_FILE = os.path.join(EXCHANGE_DIR, "twitch_votes.json")
LAST_STATE_FILE = os.path.join(EXCHANGE_DIR, "last_state.json")

# Valid stat vote aliases
STAT_ALIASES = {
    "toughness": "Toughness", "tou": "Toughness", "con": "Toughness", "hp": "Toughness",
    "agility": "Agility", "agi": "Agility", "dex": "Agility",
    "strength": "Strength", "str": "Strength",
    "intelligence": "Intelligence", "int": "Intelligence",
    "willpower": "Willpower", "wil": "Willpower", "wis": "Willpower",
    "ego": "Ego", "cha": "Ego"
}

# Valid skill vote aliases
SKILL_ALIASES = {
    "rifle": "Rifles", "rifles": "Rifles", "gun": "Rifles", "guns": "Rifles",
    "acrobatics": "Acrobatics", "dodge": "Acrobatics_Dodge", "spry": "Acrobatics_Dodge",
    "endurance": "Endurance", "swimming": "Endurance_Swimming", "longstrider": "Endurance_Longstrider",
    "shakeitoff": "Endurance_ShakeItOff", "harvestry": "CookingAndGathering_Harvestry", "butchery": "CookingAndGathering_Butchery"
}

# Valid mutation vote aliases
MUTATION_ALIASES = {
    "freezingray": "FreezingRay", "freeze": "FreezingRay", "ice": "FreezingRay",
    "lightmanipulation": "LightManipulation", "laser": "LightManipulation", "light": "LightManipulation",
    "flamingray": "FlamingRay", "fire": "FlamingRay", "flame": "FlamingRay",
    "forcebubble": "ForceBubble", "bubble": "ForceBubble",
    "forcewall": "ForceWall", "wall": "ForceWall",
    "teleportation": "Teleportation", "teleport": "Teleportation", "blink": "Teleportation",
    "multiplelegs": "MultipleLegs", "legs": "MultipleLegs", "speed": "MultipleLegs",
    "multiplearms": "MultipleArms", "arms": "MultipleArms",
    "doublemuscled": "DoubleMuscled", "muscles": "DoubleMuscled",
    "triplejointed": "TripleJointed", "joints": "TripleJointed",
    "regeneration": "Regeneration", "regen": "Regeneration",
    "carapace": "Carapace", "shell": "Carapace",
    "phasing": "Phasing", "phase": "Phasing",
    "electricalgeneration": "ElectricalGeneration", "shock": "ElectricalGeneration", "lightning": "ElectricalGeneration",
    "corrosivegasgeneration": "CorrosiveGasGeneration", "gas": "CorrosiveGasGeneration"
}

class TwitchVoteManager:
    def __init__(self, config_file=CONFIG_PATH):
        self.config_file = config_file
        self.config = self.load_config()
        self.channel = self.config.get("channel", "").strip().lower().lstrip("#")
        self.token = self.config.get("oauth_token", "").strip()
        self.bot_user = self.config.get("bot_username", "").strip()
        self.enabled = self.config.get("enabled", False)

        self.stat_votes = {}    # user -> stat
        self.skill_votes = {}   # user -> skill
        self.mutation_votes = {} # user -> mutation
        self.lock = threading.Lock()
        self.sock = None
        self.running = False

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Twitch] Config load error: {e}")
        return {"channel": "", "enabled": False}

    def save_votes_to_disk(self):
        try:
            with self.lock:
                stat_counts = dict(Counter(self.stat_votes.values()))
                skill_counts = dict(Counter(self.skill_votes.values()))
                mutation_counts = dict(Counter(self.mutation_votes.values()))
            
            data = {
                "stat_votes": stat_counts,
                "skill_votes": skill_counts,
                "mutation_votes": mutation_counts,
                "total_stat_votes": len(self.stat_votes),
                "total_skill_votes": len(self.skill_votes),
                "total_mutation_votes": len(self.mutation_votes),
                "timestamp": time.time()
            }
            with open(VOTES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Twitch] Error saving votes to disk: {e}")

    def get_top_stat(self):
        with self.lock:
            if not self.stat_votes:
                return None
            counts = Counter(self.stat_votes.values())
            return counts.most_common(1)[0]  # (stat_name, count)

    def get_top_skill(self):
        with self.lock:
            if not self.skill_votes:
                return None
            counts = Counter(self.skill_votes.values())
            return counts.most_common(1)[0]  # (skill_class, count)

    def get_top_mutation(self):
        with self.lock:
            if not self.mutation_votes:
                return None
            counts = Counter(self.mutation_votes.values())
            return counts.most_common(1)[0]  # (mutation_name, count)

    def reset_stat_votes(self):
        with self.lock:
            self.stat_votes.clear()
        self.save_votes_to_disk()

    def reset_skill_votes(self):
        with self.lock:
            self.skill_votes.clear()
        self.save_votes_to_disk()

    def reset_mutation_votes(self):
        with self.lock:
            self.mutation_votes.clear()
        self.save_votes_to_disk()

    def send_chat(self, msg):
        if self.sock and self.token and self.channel:
            try:
                self.sock.send(f"PRIVMSG #{self.channel} :{msg}\r\n".encode("utf-8"))
            except Exception:
                pass

    def handle_message(self, user, message):
        msg = message.strip()
        parts = msg.split()
        if not parts:
            return

        cmd = parts[0].lower()
        if cmd == "!vote" and len(parts) > 1:
            target = parts[1].lower()
            if target in STAT_ALIASES:
                stat = STAT_ALIASES[target]
                with self.lock:
                    self.stat_votes[user] = stat
                self.save_votes_to_disk()
                print(f"[Twitch Vote] {user} voted for STAT: {stat}")
            elif target in SKILL_ALIASES:
                skill = SKILL_ALIASES[target]
                with self.lock:
                    self.skill_votes[user] = skill
                self.save_votes_to_disk()
                print(f"[Twitch Vote] {user} voted for SKILL: {skill}")
            elif target in MUTATION_ALIASES:
                mut = MUTATION_ALIASES[target]
                with self.lock:
                    self.mutation_votes[user] = mut
                self.save_votes_to_disk()
                print(f"[Twitch Vote] {user} voted for MUTATION: {mut}")

        elif cmd == "!votes":
            with self.lock:
                stats = dict(Counter(self.stat_votes.values()))
                skills = dict(Counter(self.skill_votes.values()))
                muts = dict(Counter(self.mutation_votes.values()))
            s_str = ", ".join(f"{k}:{v}" for k, v in stats.items()) or "None"
            sk_str = ", ".join(f"{k}:{v}" for k, v in skills.items()) or "None"
            m_str = ", ".join(f"{k}:{v}" for k, v in muts.items()) or "None"
            reply = f"Current Votes -> Stats: [{s_str}] | Skills: [{sk_str}] | Mutations: [{m_str}]"
            print(f"[Twitch] {reply}")
            self.send_chat(reply)

        elif cmd == "!status":
            if os.path.exists(LAST_STATE_FILE):
                try:
                    with open(LAST_STATE_FILE, "r", encoding="utf-8") as f:
                        st = json.load(f)
                    hp = st.get("hp", "?")
                    max_hp = st.get("max_hp", "?")
                    lvl = st.get("level", "?")
                    zone = st.get("zone_name", "Unknown")
                    ap = st.get("ap", 0)
                    sp = st.get("sp", 0)
                    ammo = st.get("missile_ammo", 0)
                    reply = f"QudAI Status -> Lvl {lvl} | HP: {hp}/{max_hp} | Ammo: {ammo} | Zone: {zone} | AP: {ap} | SP: {sp}"
                    print(f"[Twitch] {reply}")
                    self.send_chat(reply)
                except Exception:
                    pass

    def run(self):
        if not self.channel:
            print("[Twitch] No channel configured in twitch_config.json. Set 'channel' and 'enabled': true.")
            return

        nick = self.bot_user if self.bot_user else f"justinfan{random.randint(10000, 99999)}"
        password = f"oauth:{self.token.lstrip('oauth:')}" if self.token else "SCHMOOPIE"

        print(f"[Twitch] Connecting to #{self.channel} as {nick}...")
        self.running = True

        while self.running:
            try:
                context = ssl.create_default_context()
                raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock = context.wrap_socket(raw_sock, server_hostname="irc.chat.twitch.tv")
                self.sock.connect(("irc.chat.twitch.tv", 6697))
                self.sock.send(f"PASS {password}\r\nNICK {nick}\r\nJOIN #{self.channel}\r\n".encode("utf-8"))

                print(f"[Twitch] Connected to #{self.channel}! Listening for chat commands (!vote, !votes, !status)...")
                read_buffer = ""

                while self.running:
                    data = self.sock.recv(2048).decode("utf-8", errors="ignore")
                    if not data:
                        break

                    read_buffer += data
                    lines = read_buffer.split("\r\n")
                    read_buffer = lines.pop()

                    for line in lines:
                        if line.startswith("PING"):
                            self.sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                        elif "PRIVMSG" in line:
                            try:
                                user = line.split("!", 1)[0].lstrip(":")
                                message = line.split("PRIVMSG", 1)[1].split(":", 1)[1]
                                self.handle_message(user, message)
                            except Exception:
                                pass
            except Exception as e:
                print(f"[Twitch] Connection error: {e}. Reconnecting in 10s...")
                time.sleep(10)

def start_twitch_in_background():
    manager = TwitchVoteManager()
    if manager.enabled and manager.channel:
        t = threading.Thread(target=manager.run, daemon=True)
        t.start()
        return manager
    return None

if __name__ == "__main__":
    mgr = TwitchVoteManager()
    if not mgr.channel:
        print("Please enter your Twitch channel name in twitch_config.json")
    else:
        mgr.run()
