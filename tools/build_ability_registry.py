"""Builds data/abilities.json: every activated ability the game can give a character, from the game's own data.

Needs the game installed (reads Assembly-CSharp.dll, Mutations.xml, Skills.xml). Run locally:
    python tools/build_ability_registry.py [path to CoQ_Data]
The output is small reference data (names and command strings, no game code or art) and is committed, so tools and cloud
agents can use it without the game. Re-run after a game update.

Sources (all read-only, AGENTS R1: engine truth):
  1. Part types whose methods call AddActivatedAbility / AddMyActivatedAbility. The string constants in that method give
     [display name, command (when literal), category]. When the command is not a literal the game builds it at run time:
     the entry gets command_source "derived" (a guess: "Command" + name without spaces) until live data confirms it.
  2. The engine's own AI role lists: HandleEvent(AIGet<Role>AbilityListEvent) methods and the Command* strings in them
     (offensive / defensive / movement / passive / retreat).
  3. Mutations.xml and Skills.xml for the human names of the owning mutation / skill power.
"""
import collections
import datetime
import json
import os
import re
import sys

import dnfile

DEFAULT_DATA = r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data"
CATEGORIES = {"Skills", "Physical Mutations", "Mental Mutations", "Cybernetics", "Items", "Maneuvers", "Stances", "Tinkering"}
CMD = re.compile(r"^Command[A-Z][A-Za-z0-9_]+$")
ROLE_EVENTS = {
    "AIGetOffensiveAbilityListEvent": "offensive", "AIGetDefensiveAbilityListEvent": "defensive",
    "AIGetMovementAbilityListEvent": "movement", "AIGetPassiveAbilityListEvent": "passive",
    "AIGetRetreatAbilityListEvent": "retreat",
}


class Dll:
    def __init__(self, path):
        self.pe = dnfile.dnPE(path)
        self.md = self.pe.net.mdtables
        us = self.pe.net.user_strings
        raw = open(path, "rb").read()
        self.blob = raw[us.file_offset:us.file_offset + us.sizeof()]
        self.typedef_names = [str(r.TypeName) for r in self.md.TypeDef]
        self.typeref_names = [str(r.TypeName) for r in self.md.TypeRef]

    def ustr(self, off):
        b = self.blob[off]
        hdr = 1 if b & 0x80 == 0 else (2 if b & 0xC0 == 0x80 else 4)
        ln = b if hdr == 1 else (((b & 0x3F) << 8) | self.blob[off + 1] if hdr == 2 else 0)
        return self.blob[off + hdr: off + hdr + ln - 1].decode("utf-16le", errors="ignore")

    def body(self, m):
        rva = m.row.Rva
        if not rva:
            return b""
        try:
            first = self.pe.get_data(rva, 1)[0]
            if first & 3 == 2:
                size, hs = first >> 2, 1
            else:
                hb = self.pe.get_data(rva, 12)
                hs = ((hb[1] << 8 | hb[0]) >> 12) * 4
                size = int.from_bytes(hb[4:8], "little")
            return self.pe.get_data(rva + hs, size)
        except Exception:
            return b""

    def member_name(self, tok):
        t, r = tok >> 24, tok & 0xFFFFFF
        try:
            if t == 6:
                return str(self.md.MethodDef[r - 1].Name)
            if t == 10:
                return str(self.md.MemberRef[r - 1].Name)
        except Exception:
            pass
        return ""

    def scan(self, m):
        """Returns (ordered ldstr strings, set of called member names) of a method body."""
        code = self.body(m)
        strs, calls = [], set()
        for j in range(len(code) - 4):
            op = code[j]
            if op in (0x28, 0x6F):
                calls.add(self.member_name(int.from_bytes(code[j + 1:j + 5], "little")))
            elif op == 0x72 and code[j + 4] == 0x70:
                try:
                    strs.append(self.ustr(int.from_bytes(code[j + 1:j + 4], "little")))
                except Exception:
                    pass
        return strs, calls

    def first_param_class(self, m):
        def rc(b, i):
            x = b[i]
            if x & 0x80 == 0:
                return x, i + 1
            if x & 0xC0 == 0x80:
                return ((x & 0x3F) << 8) | b[i + 1], i + 2
            return ((x & 0x1F) << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3], i + 4
        try:
            sig = bytes(m.row.Signature.value)
            i = 1
            count, i = rc(sig, i)
            if sig[i] not in (0x01, 0x02) or count < 1:
                return None
            i += 1
            if sig[i] != 0x12:
                return None
            tok, i = rc(sig, i + 1)
            tag, idx = tok & 3, tok >> 2
            if tag == 0:
                return self.typedef_names[idx - 1]
            if tag == 1:
                return self.typeref_names[idx - 1]
        except Exception:
            return None
        return None


def split_camel(command):
    """CommandSunderMind -> 'Sunder Mind' (a readable guess when the game gives no usable name)."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", re.sub(r"^Command", "", command)).strip()


def looks_like_name(s):
    """Rejects strings that are not an ability's display name: messages, identifiers, property names."""
    s = (s or "").strip()
    if not s or ":" in s or "{" in s or "/" in s or len(s) > 30:
        return False
    if re.match(r"^(You|Your|Has|Is|Can|Received|Needs?|Cannot|Not)\b", s):
        return False
    if " " not in s and re.search(r"[a-z][A-Z]", s):          # a single CamelCase token is an identifier, not a title
        return False
    return s[0].isupper()


def pair_entries(strings, type_commands):
    """strings: ldstr order inside a registering method. Returns [{name, command, command_source, category}]."""
    entries, name, cmd = [], None, None
    for s in strings:
        if len(s) <= 1:
            continue
        if CMD.match(s):
            cmd = s
        elif s in CATEGORIES:
            if name or cmd:
                entries.append({"name": name, "command": cmd, "category": s})
            name, cmd = None, None
        elif name is None and not s.startswith(" ") and len(s) < 40 and "[" not in s:
            name = s.strip() if looks_like_name(s) else None
    # fill in commands that the method did not spell out
    for e in entries:
        if e["command"]:
            e["command_source"] = "literal"
        elif len(type_commands) == 1:
            e["command"], e["command_source"] = next(iter(type_commands)), "literal-in-type"
        elif e["name"]:
            e["command"], e["command_source"] = "Command" + re.sub(r"[^A-Za-z0-9]", "", e["name"]), "derived"
    return entries


def read_xml_names(data_dir):
    base = os.path.join(data_dir, "StreamingAssets", "Base")
    muts, skills = {}, {}
    mt = open(os.path.join(base, "Mutations.xml"), encoding="utf-8", errors="ignore").read()
    for m in re.finditer(r'<mutation [^>]*Name="([^"]*)"[^>]*Class="([^"]*)"', mt):
        muts[m.group(2)] = m.group(1)
    st = open(os.path.join(base, "Skills.xml"), encoding="utf-8", errors="ignore").read()
    for m in re.finditer(r'<(skill|power) [^>]*Name="([^"]*)"[^>]*Class="([^"]*)"[^>]*?(?:Description="([^"]*)")?', st):
        skills[m.group(3)] = {"name": m.group(2), "description": (m.group(4) or "")[:200]}
    return muts, skills


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATA
    dll = Dll(os.path.join(data_dir, "Managed", "Assembly-CSharp.dll"))
    muts, skills = read_xml_names(data_dir)

    # Command* literals anywhere in a part type, and AI roles from the engine's own event handlers
    type_cmds, roles_by_cmd, registrations = collections.defaultdict(set), collections.defaultdict(set), {}
    for row in dll.md.TypeDef:
        ns, tn = str(row.TypeNamespace), str(row.TypeName)
        if not ns.startswith("XRL.World.Parts"):
            continue
        full = f"{ns}.{tn}".replace("XRL.World.Parts", "Parts")
        for m in row.MethodList:
            strs, calls = dll.scan(m)
            for s in strs:
                if CMD.match(s):
                    type_cmds[full].add(s)
            if calls & {"AddActivatedAbility", "AddMyActivatedAbility"}:
                registrations.setdefault(full, []).append(strs)
            if str(m.row.Name) == "HandleEvent":
                ev = dll.first_param_class(m)
                if ev in ROLE_EVENTS:
                    for s in strs:
                        if CMD.match(s):
                            roles_by_cmd[s].add(ROLE_EVENTS[ev])

    abilities = {}
    for owner, seqs in sorted(registrations.items()):
        cls = owner.split(".")[-1]
        kind = "mutation" if owner.startswith("Parts.Mutation.") else ("skill" if owner.startswith("Parts.Skill.") else "other")
        for strs in seqs:
            for e in pair_entries(strs, type_cmds.get(owner, set())):
                if not e["command"]:
                    continue
                if e["category"] == "Cybernetics":
                    kind2 = "cybernetic"
                elif e["category"] == "Items":
                    kind2 = "item"
                elif e["category"] == "Stances":
                    kind2 = "stance"
                else:
                    kind2 = kind
                rec = abilities.setdefault(e["command"], {
                    "command": e["command"], "command_source": e["command_source"], "name": e["name"] or "",
                    "category": e["category"], "kind": kind2, "owners": [], "source_name": "", "engine_roles": [],
                })
                if owner not in rec["owners"]:
                    rec["owners"].append(owner)
                if cls in muts and not rec["source_name"]:
                    rec["source_name"] = muts[cls]
                elif cls in skills and not rec["source_name"]:
                    rec["source_name"] = skills[cls]["name"]
                    rec["description"] = skills[cls]["description"]
    # commands that only show up as literals in skill/mutation types (e.g. Acrobatics_Jump) but registered through a helper
    for owner, cmds in sorted(type_cmds.items()):
        cls = owner.split(".")[-1]
        for c in cmds:
            if c not in abilities and (cls in skills or cls in muts) and owner in registrations:
                abilities[c] = {"command": c, "command_source": "literal-in-type", "name": (skills.get(cls) or {}).get("name", muts.get(cls, "")),
                                "category": "Skills" if cls in skills else "Mutations", "kind": "skill" if cls in skills else "mutation",
                                "owners": [owner], "source_name": (skills.get(cls) or {}).get("name", muts.get(cls, "")), "engine_roles": []}
    for c, rec in abilities.items():
        if rec["source_name"] and not rec["name"]:
            rec["name"], rec["name_source"] = rec["source_name"], "xml"
        elif rec["name"]:
            rec["name_source"] = "code"
        else:
            rec["name"], rec["name_source"] = split_camel(c), "guess"
    for c, roles in roles_by_cmd.items():
        if c in abilities:
            abilities[c]["engine_roles"] = sorted(roles)
    out = {
        "_meta": {
            "generated": datetime.date.today().isoformat(),
            "sources": ["Assembly-CSharp.dll (AddActivatedAbility/AddMyActivatedAbility registrations, AIGet*AbilityListEvent handlers)",
                        "StreamingAssets/Base/Mutations.xml", "StreamingAssets/Base/Skills.xml"],
            "command_source": "literal = spelled out in the registering method; literal-in-type = the only Command* literal in the type; "
                              "derived = 'Command' + name without spaces (a guess; confirm with live data in memory/ability_stats.json)",
            "count": len(abilities),
        },
        "abilities": dict(sorted(abilities.items())),
    }
    dest = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "abilities.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=True)
    kinds = collections.Counter(a["kind"] for a in abilities.values())
    src = collections.Counter(a["command_source"] for a in abilities.values())
    print(f"wrote {dest}: {len(abilities)} abilities; by kind {dict(kinds)}; command source {dict(src)}")
    print("with an engine AI role:", sum(1 for a in abilities.values() if a["engine_roles"]))


if __name__ == "__main__":
    main()
