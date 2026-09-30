# Caves of Qud Builds for an AI Automation Agent

**Research date:** 2026-09-29  
**Scope:** Character construction, progression priorities, item targets, tactical sequencing, and safe exploration policy.  
**Spoiler level:** Mechanics and item names; light location/progression spoilers; no story walkthrough.

## How to read this guide

This is an evidence-bounded policy guide, not a claim that Caves of Qud has a single solved meta.

- **Sourced fact** means the statement is directly supported by the linked official wiki, official patch notes, or cited community guide.
- **Community recommendation** means a player-authored source recommends it. The official wiki's Build Library is player submitted, not developer balance guidance.
- **Agent policy (inference)** is a conservative decision rule derived from the build's mechanics. It is not presented as a fact from the source.
- **Uncertain** marks details that the sources do not specify, that depend on random loot, or that may vary by game branch/version.

The official wiki's [Build Library](https://wiki.cavesofqud.com/wiki/Build_Library) says its entries are player submitted and divides them into beginner, medium, and challenge builds. Its beginner criteria emphasize more than 18 Toughness, few active abilities, broad usability, and having both damage and escape options. Exact builds below preserve the submitted starting numbers when available.

### Version caveat

The game and its automation systems continue to change. Freehold's official devlog records ongoing updates after 1.0, and a September 7, 2026 beta build tested a new autoexplore algorithm with a new default `classic` mode and updated enemy targeting. Branch-sensitive automation should therefore be feature-detected rather than assumed. See [Freehold Games devlog](https://freeholdgames.itch.io/cavesofqud/devlog) and [Autoexplore Beta, build 211.52](https://steamdb.info/patchnotes/25160080/).

## Shared mechanics that should shape every policy

### Attribute interpretation

The official [Attributes](https://wiki.cavesofqud.com/wiki/Attributes) page documents these relationships:

- Strength raises melee penetration, carry capacity, and gates many Axe/Cudgel skills.
- Agility affects accuracy and Dodge Value and gates missile/finesse skills.
- Toughness controls hit points.
- Ego modifies mental-mutation levels.
- Attribute modifiers change once per two points relative to 16, so odd/even breakpoints matter.

The community guide [How to Make a Build](https://www.qudzoo.com/advice/build-making) adds a useful planning model: melee primarily needs Strength plus Agility, ranged primarily needs Agility, and Esper play needs Ego; Toughness benefits every build. It recommends getting a core offense online first, then survivability, then accessory skills such as Tinkering.

### Global safety policy for an automation agent

The following is an **agent-policy inference**, informed by [Qud Fundamentals](https://www.qudzoo.com/advice/novice/fundamentals) and its companion [Cheat Sheet](https://www.qudzoo.com/advice/novice/sheet):

1. On first sight of any hostile, stop automation and inspect it with Look.
2. Treat `Tough` as a manual-review encounter and `Very Tough` or `Impossible` as an avoid/retreat condition unless a build-specific rule explicitly proves a safe counter.
3. Do not autoexplore while confused, lost in a dangerous biome, below 60% HP, affected by a damaging status, missing the build's escape resource, or with an unresolved hostile on the zone.
4. Never allow autoget while a non-ignored hostile is nearby; item pickup consumes turns.
5. Keep a recoiler when cave-diving or traveling far from safe settlements, but do not count it as an immediate escape when hostiles have a path to the character.
6. Default the ignored-hostile difficulty threshold to `None`. A mature agent may raise it to `Trivial` or `Easy` only after it has a verified encounter model for the local zone and build.
7. Keep the automation interruption radius conservative (community guidance suggests roughly 10–15 tiles). Re-evaluate this when the active branch exposes different autoexplore behavior.
8. Disable autoattack for any build whose main attack has area effects, friendly-fire risk, limited ammunition/charges, phase timing, gas placement, or cooldown sequencing.

### Common state model

An AI controller should track at least:

```yaml
combat_state:
  hp_fraction: 0.0-1.0
  visible_hostiles: []
  highest_threat: trivial|easy|average|tough|very_tough|impossible
  distance_to_primary_target: integer
  escape_available: boolean
  hostile_path_blocks_recoiler: boolean
  active_cooldowns: {}
  ammo_by_type: {}
  power_state: {}
  phase_state: in_phase|out_of_phase|n/a
  gas_map_known: boolean
  friendly_fire_risk: boolean
  retreat_path_known: boolean
exploration_state:
  branch_or_build: string
  zone_tier_estimate: integer|null
  light_source_available: boolean
  encumbrance_fraction: number
  dangerous_status: []
```

## Build matrix

| # | Build | Genotype/calling | Primary plan | Complexity | Evidence strength |
|---|---|---|---|---|---|
| 1 | Auspicious Beginnings | Mutant Marauder | Freeze, close, dismember; escape via legs/teleport | Low | Exact official-wiki community entry |
| 2 | Praetorian Generalist | True Kin Praetorian | Rifle opening, sword/shield finish | Low | Exact official-wiki community entry |
| 3 | Limb-Off | Mutant Marauder | Durable multi-arm axe dismemberment | Low–medium | Exact official-wiki community entry |
| 4 | Esper-ited Away | Mutant Greybeard | Scout through walls, isolate, ranged mental offense | Medium–high | Exact entry plus dedicated Esper guide |
| 5 | Uncle Iroh | Mutant Greybeard | Detect, wall, electrical burst, fire follow-up | Medium | Exact official-wiki community entry |
| 6 | Bullet Specter | Mutant Gunslinger | Pistol kiting with phasing and time control | Medium–high | Exact entry; progression/items partly inferred |
| 7 | Classic Punchkin | True Kin Child of the Hearth | Strength-scaled unarmed cudgel pressure | Medium | Exact entry plus current community consensus |
| 8 | Gunkin | True Kin pistol specialist | Multi-gun Akimbo burst | High/item-dependent | Community archetype; exact start not canonical |
| 9 | Gas Giant | Mutant Greybeard | Sleep/control gas plus corrosive damage | High | Exact official-wiki community entry |

---

## 1. Auspicious Beginnings — freeze/axe escape mutant

**Sources:** [Build Library: Auspicious Beginnings (Mutant)](https://wiki.cavesofqud.com/wiki/Build_Library#Auspicious_Beginnings_%28Mutant%29); [Attributes](https://wiki.cavesofqud.com/wiki/Attributes); [How to Make a Build](https://www.qudzoo.com/advice/build-making).

### Sourced starting configuration

| Field | Value |
|---|---|
| Genotype/calling | Mutated Human, Marauder |
| Strength | 20 |
| Agility | 18 |
| Toughness | 18 |
| Intelligence | 17 |
| Willpower | 15 |
| Ego | 18 |
| Mutations | Freezing Ray (Hands), Multiple Legs, Teleportation |
| Defect | Amphibious |
| Starting skills | Dismember, Charge, Butchery |

The Build Library describes this as a standard beginner build with a strong combat mutation and multiple escape tools. It explicitly suggests moving points from Willpower/Ego into Toughness if the player struggles.

### Progression

**Community-supported priority:** maintain a reliable damage option and escape option.  
**Agent policy (inference):**

1. Raise Freezing Ray until it reliably controls early targets.
2. Buy Axe skills that improve the already-granted Dismember plan; add basic survivability before luxury skills.
3. Raise Multiple Legs after core offense if travel/kiting reliability is the limiting factor.
4. Treat Teleportation as an emergency resource, not routine movement.
5. Favor Toughness on a safety-first agent; exact later attribute allocation is **uncertain** because the source gives no leveling schedule.

### Desired items

The source provides no named staged item list. These are **inferred categories**:

| Phase | Policy target | Confidence |
|---|---|---|
| Early | Best available axe; armor toward a survivable AV baseline; non-mutational light; ranged backup; water containers | Inferred |
| Mid | Higher-tier axe whose Strength cap is not already wasted; recoiler; cold-resistant gear for self/environmental safety | Inferred |
| Late | High-tier axe or vibro fallback for targets the normal penetration plan cannot solve; status and resistance coverage | Inferred |

### Tactical policy

```text
IF target is dangerous at range AND Freezing Ray can reach:
    fire Freezing Ray
    close only while target is frozen/controlled
ELSE IF target is isolated and Charge has a safe landing tile:
    Charge
IF adjacent and Dismember is available against an anatomically relevant target:
    Dismember
IF control fails OR HP < 60% OR multiple dangerous hostiles converge:
    retreat with Multiple Legs
    use Teleportation only if ordinary retreat is unsafe
```

**Do not** charge into unrevealed tiles or across hazards. Do not assume freezing works equally on every target.

### Autoexplore

- Permit only with Teleportation ready or a verified open retreat path.
- Stop on any `Average` or harder hostile until the agent has classified resistances and ranged capability.
- Amphibious increases water-management burden; include thirst and water reserve in travel gating.

---

## 2. Praetorian Generalist — rifle, sword, and shield True Kin

**Sources:** [Build Library: Auspicious Beginnings (True Kin)](https://wiki.cavesofqud.com/wiki/Build_Library#Auspicious_Beginnings_%28True_Kin%29); [How to Make a Build](https://www.qudzoo.com/advice/build-making).

### Sourced starting configuration

| Field | Value |
|---|---|
| Genotype/caste | True Kin, Praetorian |
| Strength | 22 |
| Agility | 18 |
| Toughness | 21 |
| Intelligence | 16 |
| Willpower | 17 |
| Ego | 16 |
| Cybernetic | Optical bioscanner |
| Starting skills | Long Blade Proficiency, Shield Slam, Steady Hands, Draw a Bead |
| Starting kit noted by source | Chain mail, steel long sword, desert rifle |
| Other | +15 cold resistance |

The Build Library calls this extremely survivable and notes that the optical bioscanner exposes exact HP, AV, and DV when examining opponents—especially valuable to an agent.

### Progression

**Agent policy (inference):**

1. Preserve the hybrid loop: rifle at distance, long blade plus shield after contact.
2. Buy only the rifle skills that materially improve the equipped weapon; the Qudzoo build guide notes rifles work with little skill investment.
3. Develop Shield and Long Blade utility, then Single Weapon Fighting if prerequisites and equipment support it.
4. Treat cybernetics as opportunistic. Do not hard-code implants beyond the starting bioscanner without checking body-slot and license constraints.
5. Raise Strength for melee penetration or Agility for accuracy based on observed failure mode; keep Toughness adequate.

### Desired items

| Phase | Sourced or inferred target |
|---|---|
| Early | **Sourced start:** desert rifle, steel long sword, chain mail, shield-compatible play. Carry lead slugs. |
| Mid | **Inferred:** better accurate rifle, higher-tier long blade, improved shield/armor, recoiler, useful low-cost cybernetics. |
| Late | **Community guide:** ceremonial vibrokhopesh is a strong long-term Single Weapon Fighting/shield option; otherwise adapt to available high-tier gear and implants. |

### Tactical policy

```text
ON hostile detection:
    read bioscanner output
    compare target AV/DV/HP to current weapon performance
IF line of fire is clear and target is outside melee:
    Draw a Bead / fire rifle
IF target closes:
    switch decision policy to shield + long blade
    Shield Slam when displacement/stun is tactically useful
IF penetration is repeatedly ineffective:
    disengage; change weapon class or use consumable solution
```

### Autoexplore

- This is the safest of the listed builds for limited autoexplore because bioscanner data improves classification.
- Still stop when an unclassified hostile appears; the scanner is information, not proof the matchup is safe.
- Never fire through allies or neutral targets; require a ray-traced clear line of fire.

---

## 3. Limb-Off — durable multiple-arms axe mutant

**Sources:** [Build Library: Limb-Off](https://wiki.cavesofqud.com/wiki/Build_Library#Limb-Off); [How to Make a Build](https://www.qudzoo.com/advice/build-making); [Steam discussion on many-limbed weapon choices](https://steamcommunity.com/app/333640/discussions/0/830448456536436248/).

### Sourced starting configuration

| Field | Value |
|---|---|
| Genotype/calling | Mutated Human, Marauder |
| Strength | 20 |
| Agility | 18 |
| Toughness | 19 |
| Intelligence | 16 |
| Willpower | 18 |
| Ego | 14 |
| Mutations | Carapace, Multiple Arms, Night Vision, Regeneration |
| Starting skills | Dismember, Charge, Butchery |

The submitted build explicitly describes an aggressive melee character that can remove enemy limbs and regrow its own.

### Progression

**Community-supported constraints:** axes need Strength; multiweapon builds should not be treated as online until their supporting skills are acquired. The Qudzoo guide advises using a two-handed weapon early and switching once the multiweapon package is functional.  
**Agent policy (inference):**

1. Early: one strong two-handed axe; prioritize core Axe offense.
2. Mid: acquire Multiweapon Fighting prerequisites and only then equip multiple one-handed weapons for output.
3. Rank Carapace if incoming physical damage is the bottleneck; rank Multiple Arms if attack frequency and equipment supply justify it.
4. Preserve Regeneration as recovery insurance; do not deliberately accept limb loss because recovery timing can still be unsafe.
5. Carry a ranged backup for flying, unreachable, explosive, or otherwise unsafe melee targets.

### Desired items

| Phase | Policy target | Basis |
|---|---|---|
| Early | Best two-handed axe available; light source backup despite Night Vision; basic ranged weapon | Community/inference |
| Mid | Several good one-handed axes after multiweapon skills; armor compatible with Carapace plan; recoiler | Inference |
| Late | High-tier axes; at least one alternative that handles very high AV; resistance and escape items | Inference |

Exact named best-in-slot axes are **not sourced** by the build entry and should remain loot-adaptive.

### Tactical policy

```text
IF ranged threat and safe Charge line exists:
    Charge
IF priority target has dangerous wielded/body-part capability AND Dismember ready:
    Dismember
ELSE:
    basic multiweapon attack
IF surrounded beyond modeled survivability:
    do not Berserk/commit deeper
    retreat toward a one-tile choke or zone edge
```

Do not use dismemberment as the only answer to robots, amorphous enemies, or other targets for which anatomy removal may be irrelevant.

### Autoexplore

- Allow autoattack only for classified trivial enemies and only when no explosive, ranged, or disabling threat is present.
- Stop before pathing adjacent to unknown enemies; this build is strong in melee but can still be disabled before its turn economy comes online.

---

## 4. Esper-ited Away — high-Willpower clairvoyant Esper

**Sources:** [Build Library: Esper-ited Away](https://wiki.cavesofqud.com/wiki/Build_Library#Esper-ited_Away); [Kill things with your mind: How to play an Esper](https://steamcommunity.com/sharedfiles/filedetails/?id=485294321); [Attributes](https://wiki.cavesofqud.com/wiki/Attributes).

### Sourced starting configuration

| Field | Value |
|---|---|
| Genotype/calling | Mutated Human, Greybeard |
| Strength | 13 |
| Agility | 16 |
| Toughness | 18 |
| Intelligence | 18 |
| Willpower | 22 |
| Ego | 18 |
| Mutations | Esper, Clairvoyance, Force Wall, Light Manipulation, Sunder Mind |
| Defect | Socially Repugnant |
| Starting skills | Cudgel Proficiency, Berate, Calloused |

The Build Library recommends raising Light Manipulation for the first few levels, then raising Ego and acquiring more mental mutations. The dedicated Steam guide is older and should be treated as conceptual rather than patch-exact; it emphasizes Ego/Willpower, Light Manipulation, Teleportation, and maintaining backup equipment.

### Progression

1. **Community recommendation:** first levels into Light Manipulation for stable damage.
2. Raise Ego after the early damage floor is secure; Ego modifies mental-mutation levels.
3. Prefer a dependable escape/control mutation when offered; Teleportation is specifically highlighted by the Esper guide.
4. Do not collect every mental mutation indiscriminately. **Agent inference:** score new mutations by `damage`, `escape`, `information`, `control`, and cooldown overlap.
5. Use skill points on survivability, mobility, and utility because mental powers do not require a weapon skill tree.

### Desired items

| Phase | Target | Evidence |
|---|---|---|
| Early | Backup light source/floating glowsphere; ordinary ranged/melee backup | Esper guide explicitly warns Light Manipulation's light can diminish as charges are used |
| Mid | Recoiler; Ego-enhancing equipment when safe; defensive/resistance gear | Community-supported category |
| Late | Vibro/gaslight weapon or ceremonial vibrokhopesh as low-Strength melee fallback | Named by the Esper guide; availability uncertain |

The older guide also discusses face equipment for Ego and the Fist of the Ape God, but those are situational and should not be encoded as required progression.

### Tactical policy

```text
BEFORE entering uncertain room/corridor:
    use Clairvoyance if ready and information value is high
IF single susceptible priority target at range:
    Sunder Mind only when interruption risk is acceptable
ELSE IF immediate ranged damage needed:
    use Light Manipulation
IF melee rush or projectile pressure threatens position:
    place Force Wall to break path/line of effect
IF powers are cooling down:
    kite; use backup weapon only against low-risk targets
IF hostile esper / unknown psychic threat appears:
    elevate to manual-review; preserve escape
```

### Autoexplore

- Default to off in unfamiliar zones: this build depends on first-move information and cooldown availability.
- Require a backup light source; do not continue if Light Manipulation use would leave the agent unable to see.
- Stop for any psychic hunter/mental threat regardless of displayed difficulty.

---

## 5. Uncle Iroh — electrical/fire control caster

**Source:** [Build Library: Uncle Iroh](https://wiki.cavesofqud.com/wiki/Build_Library#Uncle_Iroh).

### Sourced starting configuration

| Field | Value |
|---|---|
| Genotype/calling | Mutated Human, Greybeard |
| Strength | 14 |
| Agility | 18 |
| Toughness | 18 |
| Intelligence | 18 |
| Willpower | 22 |
| Ego | 15 |
| Mutations | Unstable Genome, Electrical Generation, Flaming Ray (Hands), Heightened Hearing, Force Wall |
| Defect | Tonic Allergy |
| Starting skills | Cudgel Proficiency, Berate, Calloused |

The build note states that Electrical Generation supplies burst damage, including attacks through walls when paired with Heightened Hearing and Force Wall, while Flaming Ray supplies ranged damage on a short cooldown.

### Progression

**Agent policy (inference):**

1. Rank Electrical Generation and Flaming Ray according to observed damage/cooldown bottleneck; do not dilute both with too many rank-hungry additions.
2. Preserve Heightened Hearing as a targeting/information tool.
3. Favor Willpower where it meaningfully improves cooldown cycling; exact breakpoints should be read from the current game, not hard-coded from old guides.
4. Treat Tonic Allergy as a hard safety constraint. Never auto-use a tonic without modeling the allergy outcome.

### Desired items

The source names no staged equipment. Inferred targets:

- **Early:** armor, non-fire backup weapon, light, ranged mundane option.
- **Mid:** recoiler, resistance gear, energy-management equipment if the current mutation implementation benefits from it.
- **Late:** alternatives for heat/electric immune or resistant targets; defensive items that buy cooldown time.

### Tactical policy

```text
IF dangerous target is detected behind a wall via Heightened Hearing:
    keep wall intact when possible
    use Electrical Generation only if current mechanics confirm valid targeting and no ally risk
IF clear ranged lane:
    Flaming Ray
IF enemies close or cooldown recovery is needed:
    Force Wall, reposition, wait safely
IF target resists heat and electricity:
    disengage or use backup physical/consumable solution
```

### Autoexplore

- Stop on any detected-but-unseen hostile; auditory knowledge is incomplete.
- Never automate area/burst attacks without a friendly/neutral occupancy check.
- Keep autoattack off because the build's value comes from sequencing, not bump attacks.

---

## 6. Bullet Specter — phased mutant gunslinger

**Sources:** [Build Library: Bullet Specter](https://wiki.cavesofqud.com/wiki/Build_Library#Bullet_Specter); [How to Make a Build](https://www.qudzoo.com/advice/build-making).

### Sourced starting configuration

| Field | Value |
|---|---|
| Genotype/calling | Mutated Human, Gunslinger |
| Strength | 16 |
| Agility | 23 |
| Toughness | 18 |
| Intelligence | 16 |
| Willpower | 18 |
| Ego | 16 |
| Mutations | Night Vision, Phasing, Triple-jointed, Sunder Mind, Time Dilation |
| Defect | Tonic Allergy |
| Starting skill listed | Weak Spotter |
| Other | +200 reputation with mysterious strangers |

The build entry says it uses phase-harmonic weapon mods for rapid-fire attacks before returning to phase. The Qudzoo guide notes that pistol builds have high late-game damage but consume large quantities of ammunition and require multiple good weapons; rifles are often stronger before pistol skills and gear mature.

### Progression

**Agent policy (inference):**

1. Early: use the best reliable ranged weapon, including rifles if pistol ammunition or weapon quality is poor.
2. Buy core Pistol skills as prerequisites allow; prioritize reliable firing/accuracy before luxury effects.
3. Rank Phasing enough for the attack/escape loop; rank Triple-jointed when it unlocks meaningful Agility-dependent skill reliability.
4. Treat Sunder Mind as a supplemental answer, not primary rotation, because Ego is only 16.
5. Add Time Dilation for emergency local control when enemies breach range.

### Desired items

| Phase | Target | Basis |
|---|---|---|
| Early | Any accurate rifle or serviceable pistols; large ammo reserve; non-tonic healing options | Community/inference |
| Mid | Matched quality pistols; phase-harmonic/phase-conjugate support as available; recoiler | Build comment/community |
| Late | Multiple high-tier pistols with suitable mods; ammunition/power logistics; defensive escape item | Community/inference |

Exact weapon names and the timing of phase-related mods are **loot-dependent and not specified** by the source.

### Tactical policy

```text
IF out_of_phase and clean firing lane exists:
    fire priority target; preserve distance
IF enemies approach effective melee range:
    Time Dilation or phase transition, then reposition
IF in_phase:
    do not waste incompatible attacks
    move to a firing tile and schedule reappearance only with escape path
IF ammunition falls below mission reserve:
    stop using pistols on trivial enemies; switch backup
```

### Autoexplore

- Require phase state and cooldown tracking before every automated step.
- Disable automatic adjacent attacks; they can waste the phase window or ammunition.
- Stop when a target is immune/inaccessible because of phase mismatch.

---

## 7. Classic Punchkin — cybernetic unarmed True Kin

**Sources:** [Build Library: Classic Punchkin](https://wiki.cavesofqud.com/wiki/Build_Library#Classic_Punchkin); [current Punchkin discussion](https://www.reddit.com/r/cavesofqud/comments/1sxcrnf/punchkin_build_help/); [True Kin archetype discussion](https://www.reddit.com/r/cavesofqud/comments/yzbi0y/); [Attributes](https://wiki.cavesofqud.com/wiki/Attributes).

### Sourced starting configuration

| Field | Value |
|---|---|
| Genotype/caste | True Kin, Child of the Hearth |
| Strength | 22 |
| Agility | 18 |
| Toughness | 18 |
| Intelligence | 18 |
| Willpower | 18 |
| Ego | 18 |
| Cybernetic | Carbide hand bones |
| Starting skills | Slam, Calloused, Strapping Shoulders |
| Other | +15 heat resistance |

Current community discussion consistently describes Punchkin as scaling through stronger hand-bone cybernetics and Strength, with Cudgel, Single Weapon Fighting, and Shield as common supporting trees. Community comments also emphasize that True Kin progression is loot- and credit-dependent, so implant plans must remain adaptable.

### Progression

1. Raise Strength; the archetype depends on unarmed penetration/damage scaling.
2. Acquire Cudgel skills that improve daze/stun pressure.
3. Add Single Weapon Fighting and/or Shield according to current equipment and prerequisites.
4. Upgrade hand bones when stronger variants become available and licenses permit.
5. Build a ranged fallback instead of assuming every late-game target is safely punchable.

### Desired items/cybernetics

| Phase | Target | Evidence |
|---|---|---|
| Early | **Sourced:** carbide hand bones; shield if pursuing that branch; armor and ranged backup | Build/community |
| Mid | Higher-tier hand bones; useful survivability/mobility implants; license credits | Community |
| Late | Crysteel or better hand-bone option when found; optional ranged cybernetic pivot; high-value defensive gear | Community; exact best-in-slot uncertain |

Claims involving rare unique fist combinations or a guaranteed Helping Hands/Giant Hands setup are **not reliable enough to make mandatory policy**.

### Tactical policy

```text
IF target can be safely reached:
    close using cover/chokes
    Slam when displacement or collision creates value
    maintain cudgel stun pressure
IF target is flying, explosive, kiting, or lethal in melee:
    use ranged fallback or disengage
IF repeated punches fail to penetrate:
    stop; do not grind turns into armor
    switch damage type or retreat
```

### Autoexplore

- May autoattack only classified trivial melee enemies with no hazardous on-death effect.
- Stop for ranged enemies across open terrain; closing automatically is unsafe.
- Require a path-to-safety check because the build lacks an innate teleport/phase escape.

---

## 8. Gunkin — gun-rack Akimbo True Kin

**Sources:** [True Kin archetype discussion](https://www.reddit.com/r/cavesofqud/comments/yzbi0y/); [2026 Punchkin vs. Gunkin discussion](https://www.reddit.com/r/cavesofqud/comments/1wktt02/stronger_true_kin_build_punchkin_or_gunkin/); [How to Make a Build](https://www.qudzoo.com/advice/build-making).

### Evidence and uncertainty

Unlike the previous entries, this is a broad community archetype rather than one canonical submitted build. The sources agree on the core:

- Gun rack adds missile-weapon capacity.
- Akimbo is the key pistol skill for firing multiple equipped pistols.
- Giant Hands supports one-handing normally two-handed weapons; Rapid Release Finger Flexors supports faster pistol firing.
- The build is extremely item-, ammunition-, power-, license-, and credit-dependent.

**Starting stats:** no single current canonical spread is supported. Community advice commonly treats Agility as primary. One 2026 discussion says 18 starting Agility can remain workable, but this is opinion rather than a verified threshold.  
**Suggested agent start (inference):** True Kin with high Agility, at least 18 Toughness, and enough Intelligence for desired utility; use a caste that supplies a functional early ranged/melee kit. Do not label this spread canonical.

### Progression

1. Establish a reliable single-weapon ranged plan before the four-gun suite exists.
2. Acquire Pistol prerequisites and Akimbo.
3. Install gun rack only when enough good weapons, ammo/power, and license points exist to justify it.
4. Choose Giant Hands for larger-weapon configurations or Rapid Release Finger Flexors for pistol action economy; verify current slot conflicts.
5. Preserve an emergency mobility/defense option because damage output does not itself prevent contact.

### Desired items/cybernetics

| Phase | Target | Evidence |
|---|---|---|
| Early | Reliable rifle or pistols; large slug reserve; armor; melee backup | Community guide |
| Mid | Gun rack, several comparable pistols, Akimbo, license credits; power cells if needed | Community archetype |
| Late | Four synergistic high-tier guns; Giant Hands **or** Rapid Release Finger Flexors depending loadout; robust ammo/power supply | Community archetype |

No exact acquisition route is guaranteed; merchant inventories and loot make rigid shopping scripts brittle.

### Tactical policy

```text
BEFORE burst:
    verify all gun slots loaded/powered
    verify line of fire and no friendly/neutral in lane
    estimate ammo reserve after burst
IF priority target merits burst:
    Akimbo
ELSE:
    fire the most efficient single weapon
IF enemy enters melee threat radius:
    use mobility/control item and reopen range
IF fewer than two useful guns are operational:
    fall back to rifle/single-gun policy
```

### Autoexplore

- Do not allow automated Akimbo.
- Stop on every target until friendly-fire lanes and ammunition economics are evaluated.
- Keep a per-gun reload/power state; an apparently equipped gun is not necessarily ready.

---

## 9. Gas Giant — continuous corrosive/sleep gas mutant

**Sources:** [Build Library: Gas Giant](https://wiki.cavesofqud.com/wiki/Build_Library#Gas_Giant); [How to Make a Build](https://www.qudzoo.com/advice/build-making).

### Sourced starting configuration

| Field | Value |
|---|---|
| Genotype/calling | Mutated Human, Greybeard |
| Strength | 14 |
| Agility | 18 |
| Toughness | 18 |
| Intelligence | 18 |
| Willpower | 21 |
| Ego | 17 |
| Mutations | Adrenal Control, Carapace, Corrosive Gas Generation, Heightened Quickness, Sleep Gas Generation |
| Defect | Irritable Genome |
| Starting skills | Cudgel Proficiency, Berate, Calloused |

The Build Library says Corrosive Gas is intended as the exclusive damage source, with Sleep Gas as support. It recommends raising Willpower and says that at 28 Willpower the listed cooldowns are low enough for continuous generation. It also recommends acquiring a gas tumbler for damage and control, ideally protecting allies.

### Progression

1. **Sourced:** raise Willpower toward 28 for the build's intended continuous cycle.
2. Rank Corrosive Gas as the primary damage mutation.
3. Rank Sleep Gas enough to create safe control windows.
4. Use Adrenal Control to enhance the mutation package when a meaningful encounter justifies the cooldown.
5. Raise Carapace/Heightened Quickness as support after gas reliability.

The 28-Willpower claim should be verified against the installed build before hard-coding because cooldown rules can change.

### Desired items

| Phase | Target | Evidence |
|---|---|---|
| Early | Defensive armor plan, ordinary ranged backup, light, recoiler | Inference |
| Mid | **Sourced:** gas tumbler; resistance/status coverage; ranged answer to gas-immune targets | Build entry + inference |
| Late | Improved gas-control gear if found; high-tier non-acid fallback; ally-safe equipment/policy | Inference |

### Tactical policy

```text
BEFORE gas release:
    map allies/neutrals, airflow/open tiles if modeled, and escape path
IF cluster can be controlled without ally exposure:
    Sleep Gas
    reposition so targets remain inside cloud
    Corrosive Gas
IF target is acid-immune/resistant OR gas cannot be contained:
    do not spend turns on failed loop
    switch ranged fallback or retreat
IF cloud threatens allies or blocks own escape:
    stop generation and reposition
```

### Autoexplore

- Autoattack must remain off.
- Do not generate gas under generic hostile-response automation.
- Require a fully observed local map and explicit ally check before either gas ability.
- Stop if gas tiles, fire, liquids, or other environmental interactions are not represented in the agent's world model.

---

## Skill-order policy without pretending Qud has fixed rotations

Qud is turn-based and highly stateful. A rigid MMO-style rotation is usually the wrong abstraction. The more robust model is a priority system:

```text
1. Prevent immediate death.
2. Preserve or create an escape route.
3. Use information abilities before committing.
4. Apply control if it changes the engagement safely.
5. Use the cheapest reliable attack that solves the target.
6. Save scarce ammunition, charges, and long cooldowns against trivial targets.
7. Stop repeating an attack after evidence of immunity or failed penetration.
8. Reassess whenever a new hostile, status effect, terrain hazard, or ally enters the model.
```

For skill purchases, use this evidence-informed order from [How to Make a Build](https://www.qudzoo.com/advice/build-making):

1. Core offense needed to make the build function.
2. Survivability such as mobility, resistance, and recovery skills.
3. Accessory systems such as Tinkering or secondary weapons.

The exact order must remain conditional on attribute prerequisites, discovered equipment, schematics, mutations, cybernetics, and the current run's threats.

## Item evaluation rules for an agent

Instead of a brittle universal loot table, score each candidate item:

```yaml
item_score:
  enables_core_build: 0..5
  improves_primary_damage: 0..5
  improves_survivability: 0..5
  provides_escape_or_control: 0..5
  covers_build_counter: 0..5
  weight_burden: -5..0
  ammo_or_power_burden: -5..0
  slot_conflict: -5..0
  friendly_fire_risk: -5..0
  rarity_or_replacement_risk: -3..0
```

Hard overrides:

- Never discard the only reliable light source, ranged option, escape item, or recoiler merely for marginal damage.
- Never equip an upgrade that silently disables the core mutation/cybernetic/weapon configuration.
- Do not sell unidentified or build-critical artifacts solely on value-per-weight heuristics.
- Maintain separate reserves for ordinary fights and emergency consumables.

## Recommended machine-readable build schema

```yaml
build_id: string
build_name: string
evidence:
  primary_sources: []
  last_reviewed: 2026-09-29
  branch_assumptions: []
start:
  genotype: mutant|true_kin
  calling_or_caste: string
  attributes: {str: 0, agi: 0, tou: 0, int: 0, wil: 0, ego: 0}
  mutations: []
  cybernetics: []
  defects: []
  skills: []
progression:
  skill_priorities: []
  mutation_priorities: []
  cybernetic_preferences: []
  attribute_policy: []
items:
  early: []
  mid: []
  late: []
  mandatory_capabilities: [light, ranged_backup, escape, recoiler]
tactics:
  engage_conditions: []
  ability_priority: []
  disengage_conditions: []
  immunity_fallbacks: []
automation:
  autoexplore_allowed_when: []
  interrupt_conditions: []
  autoattack_max_threat: none|trivial|easy
  friendly_fire_check: true
uncertainties: []
```

## Source quality and unresolved questions

### High confidence

- Exact starting attributes, mutations/cybernetics, defects, and starting skills copied from the official wiki's player-submitted Build Library.
- Attribute roles documented on the official wiki.
- Ongoing autoexplore changes documented in current patch material.

### Medium confidence

- General progression patterns from Qudzoo and long-standing community guides.
- Punchkin and Gunkin archetype components that recur across multiple community discussions.

### Explicitly uncertain

- A universal exact skill-buy order. Runs diverge because equipment, prerequisites, mutations, implants, recipes, and threats diverge.
- Fixed early/mid/late item lists for builds whose source entries name no gear.
- Best-in-slot claims, rare-item acquisition paths, and exact cooldown breakpoints across stable versus beta branches.
- Whether a particular target is susceptible to dismemberment, sleep, acid, heat, electricity, freezing, mental attacks, stun, or phase interaction without live inspection/current data.
- Current UI labels and defaults for all automation settings on every platform and branch.

## References

### Official/developer-maintained

- [Caves of Qud Wiki — Build Library](https://wiki.cavesofqud.com/wiki/Build_Library) — player-submitted builds hosted on the official wiki.
- [Caves of Qud Wiki — Attributes](https://wiki.cavesofqud.com/wiki/Attributes) — attribute mechanics and skill dependencies.
- [Caves of Qud Wiki — Mutations](https://wiki.cavesofqud.com/wiki/Mutations)
- [Caves of Qud Wiki — Cybernetics](https://wiki.cavesofqud.com/wiki/Cybernetics)
- [Caves of Qud Wiki — Skills](https://wiki.cavesofqud.com/wiki/Skills)
- [Freehold Games — Caves of Qud devlog](https://freeholdgames.itch.io/cavesofqud/devlog)
- [Autoexplore Beta, build 211.52 — patch mirror](https://steamdb.info/patchnotes/25160080/)

### Community strategy

- [Qudzoo — How to Make a Build](https://www.qudzoo.com/advice/build-making)
- [Qudzoo — Fundamentals](https://www.qudzoo.com/advice/novice/fundamentals)
- [Qudzoo — Cheat Sheet](https://www.qudzoo.com/advice/novice/sheet)
- [Steam — Kill things with your mind: How to play an Esper](https://steamcommunity.com/sharedfiles/filedetails/?id=485294321) — useful conceptual guide, but old; verify numerical details.
- [Reddit — True Kin Builds?](https://www.reddit.com/r/cavesofqud/comments/yzbi0y/) — Punchkin/Gunkin archetypes; community opinion.
- [Reddit — Punchkin build help (2026)](https://www.reddit.com/r/cavesofqud/comments/1sxcrnf/punchkin_build_help/) — current community discussion; not authoritative.
- [Reddit — Punchkin or Gunkin? (2026)](https://www.reddit.com/r/cavesofqud/comments/1wktt02/stronger_true_kin_build_punchkin_or_gunkin/) — current comparative discussion; not authoritative.

## Bottom line

For a first automation prototype, implement the **Praetorian Generalist** or **Auspicious Beginnings**. Both have a complete early kit, straightforward fallback behavior, and fewer environment-wide side effects. Defer Esper, phase, multi-gun, and gas automation until the controller reliably models cooldowns, resistances, line of fire, allies, escape paths, ammunition/power, and branch-specific autoexplore behavior.
