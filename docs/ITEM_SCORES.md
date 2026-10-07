# Items in Caves of Qud, and which builds should prefer which

*Generated 2026-10-06 by `tools/item_report.py` from `data/items.json` (built by `tools/build_item_catalog.py` from the game's own blueprint files). Scores are policy: every weight is a named constant in `item_scoring.py`. Confidence: `[verified in game data]` for the counts, `[policy guess]` for the scores.*

## How many items are there

The game defines **5202 object blueprints** in total. Of those, **1918** inherit from `Item`; **264** are abstract base blueprints, leaving **1654 concrete item blueprints**. Excluding creature natural weapons (342), projectiles (88) and things that cannot be picked up, **974 are loot items** a character can actually carry. `[verified in game data 2026-10-06]`

> Blueprints are not the number of distinct things a player can find: the game also generates relics, applies item mods (Mods tags) and tier-scaled variants at run time.

| group | loot items |
|---|---|
| armor | 229 |
| food | 138 |
| melee weapon | 112 |
| cybernetics | 77 |
| missile weapon | 51 |
| water container | 47 |
| scrap | 47 |
| book | 47 |
| other | 44 |
| trade good | 36 |
| data disk | 36 |
| tool | 24 |
| corpse | 22 |
| tonic | 13 |
| shield | 13 |
| power cell | 10 |
| quest item | 9 |
| trinket | 5 |
| applicator | 5 |
| medication | 3 |
| thrown weapon | 2 |
| light source | 2 |
| artifact | 2 |

By tier (0 weakest, 8 strongest; `None` = untiered goods such as food and trade items): 0: 35, 1: 69, 2: 59, 3: 80, 4: 83, 5: 47, 6: 60, 7: 50, 8: 40, None: 451

## What each build values (derived from its template, nothing hand-written)

| build | trained weapon skills | caster | ranged | shield | weight class | stat priorities (3 = top) |
|---|---|---|---|---|---|---|
| Auspicious Beginnings (Freeze & Dismember Marauder) | Axe |  |  |  | heavy | Strength 3, Toughness 2.5, Intelligence 2, Agility 1.5 |
| Praetorian Generalist (Rifle & Tower Shield) | LongBlades, Rifle |  | yes | yes | heavy | Toughness 3, Strength 2.5, Intelligence 2, Agility 1.5 |
| Limb-Off (Multi-Arm Meat Grinder) | Axe |  |  |  | heavy | Strength 3, Toughness 2.5, Intelligence 2, Agility 1.5 |
| Esper-ited Away (The Clairvoyant Thrallmaster) | (none) | yes |  | yes | light | Ego 3, Willpower 2.5, Intelligence 2, Toughness 1.5 |
| Uncle Iroh (Lightning & Flame Elementalist) | Cudgel |  |  | yes | normal | Willpower 3, Toughness 2.5, Intelligence 2, Agility 1.5 |
| Bullet Specter (Phased Pistol Ghost) | Pistol |  | yes |  | light | Agility 3, Toughness 2.5, Intelligence 2, Willpower 1.5 |
| Classic Punchkin (Carbide Fist Juggernaut) | Cudgel |  |  | yes | heavy | Strength 3, Toughness 2.5, Intelligence 2, Agility 1.5 |
| Gunkin (Quad-Gun Akimbo Leadstorm) | Pistol |  | yes |  | light | Agility 3, Toughness 2.5, Intelligence 2 |
| Gas Giant (Corrosive & Sleep Cloud Master) | (none) | yes |  | yes | light | Willpower 3, Toughness 2.5, Intelligence 2, Agility 1.5 |

## Best items per build (top of each class, with score)

### Auspicious Beginnings (Freeze & Dismember Marauder)

- **Melee:** zetachrome halberd (39.75); flawless crysteel halberd (36.75); crysteel halberd (33.75); zetachrome battle axe (31.5); fullerite two-handed axe (30.75)
- **Firearms/bows:** pump shotgun (9.97); combat shotgun (9.22); flamethrower (7.05); chaingun (6.6)
- **Shields:** flawless crysteel aegis (18); Va'am's lens (15); crysteel aegis (15)
- **Body armor:** zetachrome lune (21); flawless crysteel shardmail (16.5); nanoweave vest (15)
- **Head armor:** psychodyne helmet (22.5); Dagasha's spur (15.5); zetachrome apex (12)
- **Hands armor:** leyline puppeteers (15); ulnar stimulators (14.25); zetachrome gloves (12)
- **Feet armor:** zetachrome pumps (12); ninefold boots (9.5); flawless crysteel boots (9)
- **Back armor:** powered exoskeleton (12); mercurial cloak (9.5); palladium mesh tabard (5.5)
- **Stat/defence boosters:** psychodyne helmet (22.5); leyline puppeteers (15); ulnar stimulators (14.25); black mote (14)

### Praetorian Generalist (Rifle & Tower Shield)

- **Melee:** two-handed zetachrome long sword (42.25); flawless crysteel great sword (36.25); zetachrome long sword (33); La Jeunesse (30.25); crysteel great sword (30.25)
- **Firearms/bows:** pump shotgun (41.25); combat shotgun (38.75); electrobow (24.5); carbine (19.5)
- **Shields:** flawless crysteel aegis (22); Va'am's lens (19); crysteel aegis (19)
- **Body armor:** zetachrome lune (21); flawless crysteel shardmail (16.5); nanoweave vest (15)
- **Head armor:** psychodyne helmet (22.5); Dagasha's spur (15.5); zetachrome apex (12)
- **Hands armor:** leyline puppeteers (15); ulnar stimulators (13); zetachrome gloves (12)
- **Feet armor:** zetachrome pumps (12); ninefold boots (9.5); flawless crysteel boots (9)
- **Back armor:** mercurial cloak (9.5); powered exoskeleton (9.5); palladium mesh tabard (5.5)
- **Stat/defence boosters:** psychodyne helmet (22.5); leyline puppeteers (15); black mote (14); circle of light in the chord of Shugruith (13.5)

### Limb-Off (Multi-Arm Meat Grinder)

- **Melee:** zetachrome halberd (39.75); flawless crysteel halberd (36.75); crysteel halberd (33.75); zetachrome battle axe (31.5); fullerite two-handed axe (30.75)
- **Firearms/bows:** pump shotgun (9.97); combat shotgun (9.22); flamethrower (7.05); chaingun (6.6)
- **Shields:** flawless crysteel aegis (16); Va'am's lens (13); crysteel aegis (13)
- **Body armor:** zetachrome lune (21); flawless crysteel shardmail (16.5); nanoweave vest (15)
- **Head armor:** psychodyne helmet (22.5); Dagasha's spur (15.5); zetachrome apex (12)
- **Hands armor:** leyline puppeteers (15); ulnar stimulators (14.25); zetachrome gloves (12)
- **Feet armor:** zetachrome pumps (12); ninefold boots (9.5); flawless crysteel boots (9)
- **Back armor:** powered exoskeleton (12); mercurial cloak (9.5); palladium mesh tabard (5.5)
- **Stat/defence boosters:** psychodyne helmet (22.5); leyline puppeteers (15); ulnar stimulators (14.25); black mote (14)

### Esper-ited Away (The Clairvoyant Thrallmaster)

- **Melee:** zetachrome long sword (6.3); crystalline jile (5.95); zetachrome battle axe (5.95); zetachrome dagger (5.95); zetachrome dagger (5.95)
- **Firearms/bows:** pump shotgun (9.97); combat shotgun (9.22); flamethrower (7.05); chain pistol (5.4)
- **Shields:** flawless crysteel aegis (22); Va'am's lens (19); crysteel aegis (19)
- **Body armor:** zetachrome lune (15.9); nanoweave vest (15); flexivest (10.5)
- **Head armor:** psychodyne helmet (42.5); zetachrome apex (12); Dagasha's spur (11.9)
- **Hands armor:** leyline puppeteers (15); zetachrome gloves (12); flawless crysteel gauntlets (9)
- **Feet armor:** zetachrome pumps (12); ninefold boots (9.5); flawless crysteel boots (8.4)
- **Back armor:** mercurial cloak (9.5); palladium mesh tabard (5.5); kaleidocera cape (4.5)
- **Stat/defence boosters:** psychodyne helmet (42.5); leyline puppeteers (15); black mote (14); circle of light in the chord of Shugruith (13.5)

### Uncle Iroh (Lightning & Flame Elementalist)

- **Melee:** zetachrome warhammer (45.25); flawless crysteel warhammer (34.75); zetachrome hammer (31.5); maghammer (30.25); crysteel warhammer (28.75)
- **Firearms/bows:** pump shotgun (9.97); combat shotgun (9.22); flamethrower (7.05); chain pistol (5.4)
- **Shields:** flawless crysteel aegis (22); Va'am's lens (19); crysteel aegis (19)
- **Body armor:** zetachrome lune (18); nanoweave vest (15); flawless crysteel shardmail (12)
- **Head armor:** psychodyne helmet (47.5); Dagasha's spur (14); zetachrome apex (12)
- **Hands armor:** leyline puppeteers (15); zetachrome gloves (12); flawless crysteel gauntlets (9)
- **Feet armor:** zetachrome pumps (12); ninefold boots (9.5); flawless crysteel boots (9)
- **Back armor:** mercurial cloak (9.5); palladium mesh tabard (5.5); kaleidocera cape (4.5)
- **Stat/defence boosters:** psychodyne helmet (47.5); leyline puppeteers (15); black mote (14); circle of light in the chord of Shugruith (13.5)

### Bullet Specter (Phased Pistol Ghost)

- **Melee:** zetachrome warhammer (13.28); two-handed zetachrome long sword (12.38); flawless crysteel great sword (10.58); flawless crysteel warhammer (10.12); zetachrome halberd (10.12)
- **Firearms/bows:** chain pistol (26); chain pistol (26); chrome revolver (19); semi-automatic pistol (19)
- **Shields:** flawless crysteel aegis (14); Va'am's lens (11); crysteel aegis (11)
- **Body armor:** nanoweave vest (17); zetachrome lune (13.9); flexivest (13.5)
- **Head armor:** psychodyne helmet (33.5); zetachrome apex (12); Dagasha's spur (10.9)
- **Hands armor:** leyline puppeteers (17); zetachrome gloves (12); ulnar stimulators (11.75)
- **Feet armor:** zetachrome pumps (12); ninefold boots (8.5); flawless crysteel boots (6.4)
- **Back armor:** mercurial cloak (10.5); palladium mesh tabard (6.5); kaleidocera cape (5.5)
- **Stat/defence boosters:** psychodyne helmet (33.5); black mote (18); leyline puppeteers (17); circle of light in the chord of Shugruith (16.5)

### Classic Punchkin (Carbide Fist Juggernaut)

- **Melee:** zetachrome warhammer (45.25); flawless crysteel warhammer (34.75); zetachrome hammer (31.5); maghammer (30.25); crysteel warhammer (28.75)
- **Firearms/bows:** pump shotgun (9.97); combat shotgun (9.22); flamethrower (7.05); chaingun (6.6)
- **Shields:** flawless crysteel aegis (22); Va'am's lens (19); crysteel aegis (19)
- **Body armor:** zetachrome lune (21); flawless crysteel shardmail (16.5); nanoweave vest (15)
- **Head armor:** psychodyne helmet (22.5); Dagasha's spur (15.5); zetachrome apex (12)
- **Hands armor:** leyline puppeteers (15); ulnar stimulators (14.25); zetachrome gloves (12)
- **Feet armor:** zetachrome pumps (12); ninefold boots (9.5); flawless crysteel boots (9)
- **Back armor:** powered exoskeleton (12); mercurial cloak (9.5); palladium mesh tabard (5.5)
- **Stat/defence boosters:** psychodyne helmet (22.5); leyline puppeteers (15); ulnar stimulators (14.25); black mote (14)

### Gunkin (Quad-Gun Akimbo Leadstorm)

- **Melee:** zetachrome warhammer (13.28); two-handed zetachrome long sword (12.38); flawless crysteel great sword (10.58); flawless crysteel warhammer (10.12); zetachrome halberd (10.12)
- **Firearms/bows:** chain pistol (26); chain pistol (26); chrome revolver (19); semi-automatic pistol (19)
- **Shields:** flawless crysteel aegis (14); Va'am's lens (11); crysteel aegis (11)
- **Body armor:** nanoweave vest (17); zetachrome lune (13.9); flexivest (13.5)
- **Head armor:** psychodyne helmet (23.5); zetachrome apex (12); Dagasha's spur (10.9)
- **Hands armor:** leyline puppeteers (17); zetachrome gloves (12); ulnar stimulators (11.75)
- **Feet armor:** zetachrome pumps (12); ninefold boots (8.5); flawless crysteel boots (6.4)
- **Back armor:** mercurial cloak (10.5); palladium mesh tabard (6.5); kaleidocera cape (5.5)
- **Stat/defence boosters:** psychodyne helmet (23.5); black mote (18); leyline puppeteers (17); circle of light in the chord of Shugruith (16.5)

### Gas Giant (Corrosive & Sleep Cloud Master)

- **Melee:** zetachrome long sword (6.3); crystalline jile (5.95); zetachrome battle axe (5.95); zetachrome dagger (5.95); zetachrome dagger (5.95)
- **Firearms/bows:** pump shotgun (9.97); combat shotgun (9.22); flamethrower (7.05); chain pistol (5.4)
- **Shields:** flawless crysteel aegis (22); Va'am's lens (19); crysteel aegis (19)
- **Body armor:** zetachrome lune (15.9); nanoweave vest (15); flexivest (10.5)
- **Head armor:** psychodyne helmet (47.5); zetachrome apex (12); Dagasha's spur (11.9)
- **Hands armor:** leyline puppeteers (15); zetachrome gloves (12); flawless crysteel gauntlets (9)
- **Feet armor:** zetachrome pumps (12); ninefold boots (9.5); flawless crysteel boots (8.4)
- **Back armor:** mercurial cloak (9.5); palladium mesh tabard (5.5); kaleidocera cape (4.5)
- **Stat/defence boosters:** psychodyne helmet (47.5); leyline puppeteers (15); black mote (14); circle of light in the chord of Shugruith (13.5)

## Cross-build check: where does the same item rank?

For a sanity check, the single best melee weapon and firearm for each build, side by side:

| build | best melee | best firearm |
|---|---|---|
| Auspicious Beginnings (Freeze & Dismember Marauder) | zetachrome halberd (39.75) | pump shotgun (9.97) |
| Praetorian Generalist (Rifle & Tower Shield) | two-handed zetachrome long sword (42.25) | pump shotgun (41.25) |
| Limb-Off (Multi-Arm Meat Grinder) | zetachrome halberd (39.75) | pump shotgun (9.97) |
| Esper-ited Away (The Clairvoyant Thrallmaster) | zetachrome long sword (6.3) | pump shotgun (9.97) |
| Uncle Iroh (Lightning & Flame Elementalist) | zetachrome warhammer (45.25) | pump shotgun (9.97) |
| Bullet Specter (Phased Pistol Ghost) | zetachrome warhammer (13.28) | chain pistol (26) |
| Classic Punchkin (Carbide Fist Juggernaut) | zetachrome warhammer (45.25) | pump shotgun (9.97) |
| Gunkin (Quad-Gun Akimbo Leadstorm) | zetachrome warhammer (13.28) | chain pistol (26) |
| Gas Giant (Corrosive & Sleep Cloud Master) | zetachrome long sword (6.3) | pump shotgun (9.97) |

## Junk: what scores low for every build

Non-equipment items scoring below 3 (score plus trade value) for **every** build, and equipment that would make every build worse, by group. Dropped only when the pack is under pressure; never anything equipped. Armor and weapons are otherwise never junk by themselves: they are replaced when something better is carried (`choose_equips`/`choose_drops`).

- **scrap** (47): [Corpse], [the ultimate scrap], bent metal sheet, bent surgical stent, blunt scalpel, broken microcontroller array, burnt capacitor, corroded circuit board, cracked lens, cracked robotics housing, depleted stem-generator, destroyed cybernetics controller ...
- **other** (32): Barathrumite token, Schrodinger page from the Annals of Qud, bones, boulder, bronze key, cast net, chrome key, chrome security card, crystal key, cybernetics credit wedge, hurdy-gurdy, item ...
- **book** (27): *advertisement*, Aphorisms about Birds, Corpus Choliys, Fauns of the Meadow, History of Joppa, Vol. 1, History of Joppa, Vol. 2, OPERATING MANUAL FOR LARGE CREATURE, On Humanoid Mimicry of Animals and Plants, The Canticles Chromaic, Verses XVII-XXIV, The Mimic and the Madpole, [Item], book ...
- **corpse** (22): [limb], albino ape heart, ashes, black puma haunch, charred corpse, flattened remains, fresh corpse, human corpse, human remains, mangled corpse, moldering corpse, mummified corpse ...
- **trade good** (15): agate *creature* figurine, albino ape pelt, box of crayons, bronze ingot, bubble level, copper *creature* figurine, copper nugget, grave goods, gyre iron, ogre ape pelt, rough agate gemstone, scratched copper nugget ...
- **armor** (4): chassis plate, fullerite flake armor, fullerite plate mail, quilted shawl
- **trinket** (3): metal folding chair, plastic tree, small sphere of negative weight
- **missile weapon** (2): blast cannon, swarm rack

## Placed unique items (not random loot)

Marked by the game with `StaticObjectsTable:` tags: quest rewards and story artifacts. Excluded from the lists above.

- flange from the Great Machine (armor, tier 8)
- gauge from the Great Machine (armor, tier 8)
- gear from the Great Machine (shield, tier 8)
- sail from the Great Machine (armor, tier 8)

