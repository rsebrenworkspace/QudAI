# Creature catalog (generated)

Built 2026-10-08 from `StreamingAssets/Base/ObjectBlueprints/*.xml` by `tools/build_creature_catalog.py`; this page by `tools/creature_report.py`. Static facts for planning only: the live
`state.json` is the truth for the creature in front of the character (heroes, mutated and legendary creatures differ from their blueprint).

- **852** concrete creature blueprints; 852 with a level, 99 carry or use a ranged attack, 57 are rooted (turrets, plants, wall vines), 408 start hostile by their factions' starting reputation.
- Levels by band: 0-4: 97, 10-14: 52, 120-124: 1, 15-19: 118, 20-24: 77, 25-29: 85, 30-34: 105, 35-39: 26, 40-44: 72, 45-49: 5, 5-9: 137, 50-54: 74, 55-59: 1, 60-64: 1, 65-69: 1
- Checked against the live game: the levels of the creatures named in past post-mortems (chitinous puma 12, irritable tortoise 5, a snapjaw 1, ...) all match.

## Hostile on sight at the start (faction starting reputation of -250 or less, inferred), level 12 or below, mobile (what a young character meets)

| creature | blueprint | level | HP | best melee | ranged | | |
|---|---|---|---|---|---|---|---|
| snapjaw brute | `Snapjaw Brute 0` | 1 | 25 | 1d4 | - |  | hostile |
| snapjaw brute | `Snapjaw Brute 1` | 1 | 25 | 1d4 | - |  | hostile |
| snapjaw brute | `Snapjaw Brute 2` | 1 | 25 | 1d4 | - |  | hostile |
| snapjaw warlord | `Snapjaw Hero 1` | 1 | 25 | 1d4 | - |  | hostile |
| snapjaw warlord | `Snapjaw Hero Stopsvaalinn` | 1 | 25 | 1d4 | - |  | hostile |
| snapjaw warlord | `Fort Snapjaw Warlord` | 1 | 20 | 1d4 | - |  | hostile |
| giant amoeba | `GiantAmoeba` | 1 | 20 | 1d3 x4 | - |  | hostile |
| snapjaw warlord | `Snapjaw Hero 0` | 1 | 20 | 1d4 | - |  | hostile |
| snapjaw warlord | `Snapjaw Warlord 0` | 1 | 20 | 1d4 | - |  | hostile |
| snapjaw warlord | `Snapjaw Warlord 1` | 1 | 20 | 1d4 | - |  | hostile |
| snapjaw warlord | `Snapjaw Warlord 2` | 1 | 20 | 1d4 | - |  | hostile |
| snapjaw warrior | `Snapjaw Warrior 0` | 1 | 20 | 1d4 | - |  | hostile |
| snapjaw warrior | `Snapjaw Warrior 1` | 1 | 20 | 1d4 | - |  | hostile |
| snapjaw warrior | `Snapjaw Warrior 2` | 1 | 20 | 1d4 | - |  | hostile |
| [Creature] | `Delegate` | 1 | 16 | - | - |  | hostile |
| [Creature] | `DelegateBears` | 1 | 16 | - | - |  | hostile |
| [Creature] | `Merchant Guard` | 1 | 16 | - | - |  | hostile |
| hunter of the Sightless Way | `PsychicSeekerHunter` | 1 | 16 | - | - |  | hostile |
| [Creature] | `TombCultistPeriod1` | 1 | 16 | - | - |  | hostile |
| [Creature] | `TombCultistPeriod2` | 1 | 16 | - | - |  | hostile |
| [Creature] | `TombCultistPeriod3` | 1 | 16 | - | - |  | hostile |
| [Creature] | `TombCultistPeriod4` | 1 | 16 | - | - |  | hostile |
| [Creature] | `TombCultistPeriod5` | 1 | 16 | - | - |  | hostile |
| [Creature] | `TombCultistPeriod6` | 1 | 16 | - | - |  | hostile |
| boar | `Boar` | 1 | 13 | 1d3 | - |  | hostile |
| salamander | `Salamander` | 1 | 9 | 1d3 | - |  | hostile |
| giant dragonfly | `GiantDragonfly` | 1 | 6 | 1d3 | - |  | hostile |
| snapjaw hunter | `Snapjaw Hunter 0` | 1 | 6 | 1d4 | Short Bow |  | hostile |
| snapjaw hunter | `Snapjaw Hunter 1` | 1 | 6 | 1d4 | Short Bow |  | hostile |
| snapjaw hunter | `Snapjaw Hunter 2` | 1 | 6 | 1d4 | Short Bow |  | hostile |
| snapjaw shotgunner | `Snapjaw Shotgunner 0` | 1 | 6 | 1d4 | Pump Shotgun |  | hostile |
| snapjaw shotgunner | `Snapjaw Shotgunner 1` | 1 | 6 | 1d4 | Pump Shotgun |  | hostile |
| snapjaw shotgunner | `Snapjaw Shotgunner 2` | 1 | 6 | 1d4 | Pump Shotgun |  | hostile |
| ray cat | `Farm Ray Cat` | 1 | 5 | 1d2-1 x2 | - |  | hostile |
| glowfish | `Glowfish` | 1 | 5 | 1d3 | - |  | hostile |
| ray cat | `Joppa Ray Cat` | 1 | 5 | 1d2-1 x2 | - |  | hostile |
| ray cat | `Ray Cat` | 1 | 5 | 1d2-1 x2 | - |  | hostile |
| glowfish | `Uplifted Glowfish` | 1 | 5 | 1d3 | - |  | hostile |
| snapjaw | `Snapjaw` | 1 | 3 | 1d4 | - |  | hostile |
| snapjaw scavenger | `Snapjaw Scavenger 0` | 1 | 3 | 1d4 | - |  | hostile |
| snapjaw scavenger | `Snapjaw Scavenger 1` | 1 | 3 | 1d4 | - |  | hostile |
| snapjaw scavenger | `Snapjaw Scavenger 2` | 1 | 3 | 1d4 | - |  | hostile |
| snapjaw scavenger | `TutorialSnapjaw` | 1 | 3 | 1d4 | - |  | hostile |
| cannibal | `Cannibal` | 3 | 14 | 1d2 | - |  | hostile |
| croc | `Croc` | 3 | 13 | 1d4 | - |  | hostile |
| engine crabs | `Engine Crabs` | 4 | 12 | - | - |  | hostile |
| baboon hero | `Baboon Hero 1` | 5 | 20 | 1d2 | - |  | hostile |
| shrewd baboon | `Shrewd Baboon` | 5 | 20 | 1d2 | - |  | hostile |
| electrofuge | `Electrofuge` | 5 | 18 | 2d3 | - |  | hostile |
| scorpiock | `Scorpiock` | 5 | 17 | 1d4 | - |  | hostile |
| hulking baboon | `Hulking Baboon` | 5 | 15 | 1d2 | - |  | hostile |
| cave spider | `Cave Spider` | 5 | 12 | 1d2 | - |  | hostile |
| horned chameleon | `Horned Chameleon` | 5 | 11 | 1d4 | - |  | hostile |
| giant centipede | `Giant Centipede` | 5 | 8 | 1d3 | - |  | hostile |
| baboon | `Baboon` | 5 | 5 | 1d2 | - |  | hostile |
| shading =creatureRegionNoun= | `Chiliad Creature Trees` | 6 | 200 | 1d6 x2 | - |  | hostile |
| two-headed boar | `Two-Headed Boar` | 6 | 37 | 1d3 x2 | - |  | hostile |
| bear | `Bear` | 6 | 27 | 1d3 | - |  | hostile |
| bear | `TutorialBear` | 6 | 27 | 1d3 | - |  | hostile |
| =creatureRegionAdjective= scorpion | `Chiliad Creature Arachnids` | 6 | 25 | 1d4 | - |  | hostile |
| ... 75 more | | | | | | | |

## Rooted shooters (turrets and the like): fragile ones first

| creature | blueprint | level | HP | best melee | ranged | | |
|---|---|---|---|---|---|---|---|
| musket turret | `SecurityTurret` | 15 | 5 | - | Musket | rooted | hostile |
| seed-spitting vine | `Seed-Spitting Vine` | 1 | 5 | - | Seed Slingshot | rooted | hostile |
| microturret | `Microturret` | 15 | 10 | - | Semi-Automatic Pistol | rooted | hostile |
| thirst thistle | `Thirst Thistle` | 7 | 10 | - | Thistle Pitcher | rooted | calm |
| rifle turret | `RifleTurret` | 15 | 15 | - | Desert Rifle | rooted | hostile |
| chaingun turret | `ChaingunTurret` | 15 | 25 | - | Chaingun | rooted | hostile |
| laser turret | `LaserTurret` | 15 | 45 | - | Laser Rifle | rooted | hostile |
| mercurial | `Mercurial` | 20 | 50 | - | Laser Rifle | rooted | hostile |
| chain laser emplacement | `ChainLaserEmplacement` | 25 | 65 | - | Chain Laser | rooted | hostile |
| chain laser emplacement | `GritGateChainLaserEmplacement` | 25 | 65 | - | Chain Laser | rooted | ? |
| chain laser emplacement | `GritGateChainLaserEmplacement_On` | 25 | 65 | - | Chain Laser | rooted | ? |
| rocket turret | `RocketTurret` | 15 | 65 | - | Missile Launcher | rooted | hostile |
| Vivira | `Vivira` | 25 | 65 | - | Chain Laser | rooted | calm |

## Mobile ranged attackers, level 15 or below

| creature | blueprint | level | HP | best melee | ranged | | |
|---|---|---|---|---|---|---|---|
| snapjaw hunter | `Snapjaw Hunter 0` | 1 | 6 | 1d4 | Short Bow |  | hostile |
| snapjaw hunter | `Snapjaw Hunter 1` | 1 | 6 | 1d4 | Short Bow |  | hostile |
| snapjaw hunter | `Snapjaw Hunter 2` | 1 | 6 | 1d4 | Short Bow |  | hostile |
| snapjaw shotgunner | `Snapjaw Shotgunner 0` | 1 | 6 | 1d4 | Pump Shotgun |  | hostile |
| snapjaw shotgunner | `Snapjaw Shotgunner 1` | 1 | 6 | 1d4 | Pump Shotgun |  | hostile |
| snapjaw shotgunner | `Snapjaw Shotgunner 2` | 1 | 6 | 1d4 | Pump Shotgun |  | hostile |
| glowmoth | `Glowmoth` | 6 | 10 | - | Glowmoth_Gaze |  | hostile |
| Issachari rifler | `Issachari Rifler` | 8 | 16 | - | Desert Rifle |  | hostile |
| Meyehind | `Meyehind` | 8 | 60 | - | Short Bow |  | ? |
| Naphtaali jeer | `Naphtaali Jeer` | 8 | 10 | - | Short Bow |  | hostile |
| trash monk | `Trash Monk` | 8 | 20 | - | Short Bow, Electrobow |  | calm |
| hindren scout | `HindrenScout` | 9 | 40 | - | Short Bow |  | calm |
| slugsnout | `Slugsnout` | 9 | 25 | 1d4 | Slugsnout Snout |  | hostile |
| snapjaw spearfiend | `Snapjaw Spearfiend` | 12 | 15 | 1d4 | - |  | hostile |
| snapjaw trapper | `Snapjaw Trapper` | 13 | 15 | 1d4 | - |  | hostile |
| arconaut | `Arconaut` | 14 | 23 | - | Borderlands Revolver |  | ? |
| arconaut | `Arconaut Still` | 14 | 23 | - | Borderlands Revolver |  | ? |
| arconaut | `Cave Arconaut` | 14 | 23 | - | Borderlands Revolver |  | ? |
| hindren scout and pariah | `HindrenScoutPariah` | 14 | 40 | - | Short Bow |  | ? |
| two-headed slugsnout | `Two-Headed Slugsnout` | 14 | 25 | 1d4 x2 | Slugsnout Snout |  | hostile |
| agolfly | `Agolfly` | 15 | 35 | 1d3 | Girshfly_Energy |  | hostile |
| goatfolk yurtwarden | `Goatfolk Yurtwarden` | 15 | 30 | 1d3 | Desert Rifle |  | hostile |
| traipsing mortar | `Traipsing Mortar` | 15 | 20 | 1d4 | Mortar Tube |  | hostile |

## What varies between two creatures of the same blueprint

- 371 blueprints can become named heroes (hero tags); 33 get random mutations (Aoyg-No-Longer, Geeub, Goek, Mak, disciple of the Sightless Way, goatfolk qlippoth...); legendary creatures are generated per world.
- 57 swarm (they fight as a group): =creatureRegionAdjective= Girshling, Agolgot, Bethsaida, Ehalcodon, Fjorn-Kosef, Haggabah, Jotun, Mechanimist houndmaster, Mechanimist zealot, Naphtaali =creatureRegionNoun=....
