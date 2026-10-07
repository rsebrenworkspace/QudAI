# Model lab: comparing LM Studio models on the brain's combat call

`tools/model_lab.py` replays fixed combat situations through the brain's **own** `query_llm_decision` (same prompt, same menu of valid actions,
same JSON parser) and scores each model. Written 2026-10-06 (HANDOFF issue 65). It changes nothing in the game or in the brain's settings.

## Run it

```
python tools/model_lab.py --list                   # models LM Studio has, LOADED marks the one in memory
python tools/model_lab.py                          # the loaded model, 3 repeats per scenario
python tools/model_lab.py --models google/gemma-4-12b,qwen/qwen3-vl-8b-instruct --repeat 5
python tools/model_lab.py --all                    # every chat model, loaded one after another
```

- **Close the game before `--models` with several models or `--all`.** Each model is loaded into VRAM in turn (LM Studio's just-in-time loading must be on;
  `lms unload --all` runs between models when the `lms` command exists, `--no-unload` skips it). A single already-loaded model is safe with the game open.
- The brain is imported against a **temporary** exchange folder, never the live one.
- `--timeout` (default 30 s) is how long the lab waits for a reply, so slow models still produce numbers. `--brain-timeout` (default 6) is the real limit in
  `brain.py` (`QUDAI_LLM_TIMEOUT`); the "in time %" column says how many replies would have fit it.
- Reports go to `memory/model_lab/lab_<time>.md` and `.json` (not committed).

## How to read the table

| column | meaning |
|---|---|
| score% | parsed AND the action is in the offered menu AND it passes the scenario checks. Rank by this. |
| parse% | the reply was JSON the brain can read. Reasoning models that think aloud (`<think>`) fail here ("think" column). |
| menu% | the action is one of the VALID ACTIONS offered (a model that invents actions fails). |
| policy% | the scenario's checks pass (see below). |
| p50 / p95 s, in time% | reply time, and the share that fits the brain's call timeout. |
| same% | repeated runs of one scenario give the same action (temperature 0.1, so this measures stability). |
| load s, GPU MiB | time to load, and GPU memory in use afterwards (`nvidia-smi`; includes the game if it is running). |

## The scenarios (`data/model_lab_scenarios.json`)

Nine situations: the three deaths of this project (Gen 14 hunter, Gen 15 amoeba, Gen 16 jells), and everyday cases (a lone enemy at range, a pet in the
line of fire, a recruit chance, low HP with an enemy closing, two weak attackers). Each has `checks.must_not` (action prefixes that are wrong) and
`checks.should_any` (at least one must match). They encode **current policy** (for example "do not flee an adjacent below-Tough attacker"), not engine
rules, and are judged on the model's raw choice before the brain's own safety overrides. Edit or add scenarios freely: copy a state from
`last_state.json` after a bad moment and write the check you wish the model had passed.

## Caveats (be honest with the numbers)

- 9 scenarios x 3 repeats is a small sample: treat differences of one or two points as noise. Use `--repeat 5` and add scenarios before deciding.
- The lab judges single decisions, not whole runs. A model can score well here and still lose runs through slowness or a long chain of small mistakes.
- Policy checks reflect the project's current opinions. A model that disagrees with a check is not necessarily wrong; read the "Policy failures" list.
- Results depend on LM Studio settings (context length, GPU offload, KV cache). Record them with the results when you compare.

## First baseline (2026-10-06, `ministral-3-8b-instruct-2512`, 2 repeats)

score 83.3%, parse 100%, menu 100%, policy 83.3%, p50 2.93 s, p95 3.38 s, all in time, same-action 88.9%, GPU 7770 MiB with the game running.
Policy failures: fired Lase through the pet (`pet_in_line_of_fire`; the brain's line-of-fire guard normally catches it) and opened with Stunning Force against a
group of Impossible jells (`jell_group_at_range_full_hp`).
