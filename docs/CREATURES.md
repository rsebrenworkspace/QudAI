# Creature catalog (generated)

Built 2026-10-08 from `StreamingAssets/Base/ObjectBlueprints/*.xml` by `tools/build_creature_catalog.py`; this page by `tools/creature_report.py`. Static facts for planning only: the live
`state.json` is the truth for the creature in front of the character (heroes, mutated and legendary creatures differ from their blueprint).

- **845** concrete creature blueprints; 845 with a level, 99 carry or use a ranged attack, 61 are rooted (turrets, plants, wall vines), 454 start hostile by their factions' starting reputation.
- Levels by band: 0-4: 197, 10-14: 53, 120-124: 1, 15-19: 123, 20-24: 83, 25-29: 85, 30-34: 105, 35-39: 26, 40-44: 72, 45-49: 5, 5-9: 84, 50-54: 8, 55-59: 1, 60-64: 1, 65-69: 1
- Checked against the live game: the levels of the creatures named in past post-mortems (chitinous puma 12, irritable tortoise 5, a snapjaw 1, ...) all match.

## Hostile on sight at the start (faction starting reputation of -250 or less, inferred), level 12 or below, mobile (what a young character meets)

| creature | blueprint | level | HP | best melee | ranged | | |
|---|---|---|---|---|---|---|---|
| tree golem | `Tree Golem` | 1 | 1500 | - | - |  | hostile |
| shading =creatureRegionNoun= | `Chiliad Creature Trees` | 1 | 200 | 1d6 x2 | - |  | hostile |
| mopango charioteer golem | `Mopango Charioteer Golem` | 1 | 100 | - | - |  | hostile |
| mopango golem | `Mopango Golem` | 1 | 100 | - | - |  | hostile |
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
| baetyl golem | `Baetyl Golem` | 1 | 16 | - | - |  | hostile |
| bat golem | `Bat Golem` | 1 | 16 | - | - |  | hostile |
| bipedal robot golem | `Bipedal Robot Golem` | 1 | 16 | - | - |  | hostile |
| bush golem | `Bush Golem` | 1 | 16 | - | - |  | hostile |
| cat golem | `Cat Golem` | 1 | 16 | - | - |  | hostile |
| =creatureRegionAdjective= scorpion | `Chiliad Creature Arachnids` | 1 | 16 | 1d4 | - |  | hostile |
| =creatureRegionAdjective= cannibal | `Chiliad Creature Cannibals` | 1 | 16 | - | - |  | hostile |
| =creatureRegionAdjective= cat | `Chiliad Creature Cats` | 1 | 16 | 1d4 | - |  | hostile |
| =creatureRegionAdjective= crab | `Chiliad Creature Crabs` | 1 | 16 | 1d3 | - |  | hostile |
| =creatureRegionAdjective= fish | `Chiliad Creature Fish` | 1 | 16 | 1d4 | - |  | hostile |
| =creatureRegionAdjective= frog | `Chiliad Creature Frogs` | 1 | 16 | 1d4 | - |  | hostile |
| =creatureRegionAdjective= fly | `Chiliad Creature Insects` | 1 | 16 | 1d4 | - |  | hostile |
| Issachari =creatureRegionNoun= | `Chiliad Creature Issachari` | 1 | 16 | - | - |  | hostile |
| =creatureRegionAdjective= clam | `Chiliad Creature Mollusks` | 1 | 16 | 1d6 | - |  | hostile |
| =creatureRegionAdjective= ooze | `Chiliad Creature Oozes` | 1 | 16 | 1d3 x4 | - |  | hostile |
| machine =creatureRegionNoun= | `Chiliad Creature Robots` | 1 | 16 | - | - |  | hostile |
| [Creature] | `Chiliad Creature Robots Random` | 1 | 16 | - | - |  | hostile |
| =creatureRegionAdjective= root | `Chiliad Creature Roots` | 1 | 16 | 1d6 x2 | - |  | hostile |
| svardym =creatureRegionNoun= | `Chiliad Creature Svardym` | 1 | 16 | - | - |  | hostile |
| =creatureRegionAdjective= pig | `Chiliad Creature Swine` | 1 | 16 | 1d4 | - |  | hostile |
| Templar =creatureRegionNoun= | `Chiliad Creature Templar` | 1 | 16 | - | - |  | hostile |
| troll =creatureRegionNoun= | `Chiliad Creature Trolls` | 1 | 16 | - | - |  | hostile |
| =creatureRegionAdjective= lizard | `Chiliad Creature Unshelled Reptiles` | 1 | 16 | 1d4 | - |  | hostile |
| =creatureRegionAdjective= vine | `Chiliad Creature Vines` | 1 | 16 | 1d6 x2 | - |  | hostile |
| =creatureRegionAdjective= worm | `Chiliad Creature Worms` | 1 | 16 | 1d6 | - |  | hostile |
| clam golem | `Clam Golem` | 1 | 16 | - | - |  | hostile |
| crab golem | `Crab Golem` | 1 | 16 | - | - |  | hostile |
| crystal golem | `Crystal Golem` | 1 | 16 | - | - |  | hostile |
| [Creature] | `Delegate` | 1 | 16 | - | - |  | hostile |
| [Creature] | `DelegateBears` | 1 | 16 | - | - |  | hostile |
| equine golem | `Equine Golem` | 1 | 16 | - | - |  | hostile |
| fish golem | `Fish Golem` | 1 | 16 | - | - |  | hostile |
| frog golem | `Frog Golem` | 1 | 16 | - | - |  | hostile |
| hexapodal robot golem | `Hexapodal Robot Golem` | 1 | 16 | - | - |  | hostile |
| hindren golem | `Hindren Golem` | 1 | 16 | - | - |  | hostile |
| hover golem | `Hover Golem` | 1 | 16 | - | - |  | hostile |
| human golem | `Human Golem` | 1 | 16 | - | - |  | hostile |
| humanoid robot golem | `Humanoid Robot Golem` | 1 | 16 | - | - |  | hostile |
| insect golem | `Insect Golem` | 1 | 16 | - | - |  | hostile |
| jelly golem | `Jelly Golem` | 1 | 16 | - | - |  | hostile |
| [Creature] | `Merchant Guard` | 1 | 16 | - | - |  | hostile |
| nest golem | `Nest Golem` | 1 | 16 | - | - |  | hostile |
| ... 112 more | | | | | | | |

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
