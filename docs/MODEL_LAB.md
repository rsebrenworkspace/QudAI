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

- **How models are loaded (v2, after the first real run).** With the `lms` command available, the lab **unloads everything first**, loads ONE model at a time with a fixed
  `--ctx` (default 8192), ONE parallel slot (`--parallel 1`; LM Studio's default of 4 slots multiplies the context cache by four) and full GPU offload, and at the end
  **reloads the model that was loaded when it started** with its old context and slots (`--no-restore` skips that, `--no-manage` leaves all loading to LM Studio).
  The first version only unloaded between models, so on 2026-10-06 it left ministral loaded next to gemma-4-12b (two models plus the game: GPU 15.7 of 16.3 GB, RAM 91%).
- **Close the game before comparing several models or `--all`**: even one at a time, a 12B plus the game is tight on a 16 GB card.
- A model whose first four calls return nothing usable is **abandoned** (reported as such), so a model that never answers cannot burn half an hour of timeouts.
- `--max-tokens N` and `--extra '<json>'` change the combat call for the run (the brain reads the same settings from `QUDAI_LLM_MAX_TOKENS` and `QUDAI_LLM_EXTRA`).
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
| empty | HTTP 200 but no text. With `finish=length` and `reasoning>0` in the progress lines it is a thinking model that spent its whole token budget thinking. |
| load s, GPU MiB, RAM GB | time to load, GPU memory and system RAM in use afterwards (`nvidia-smi`, Windows memory status; includes the game if it is running). |

## The scenarios (`data/model_lab_scenarios.json`)

Nine situations: the three deaths of this project (Gen 14 hunter, Gen 15 amoeba, Gen 16 jells), and everyday cases (a lone enemy at range, a pet in the
line of fire, a recruit chance, low HP with an enemy closing, two weak attackers). Each has `checks.must_not` (action prefixes that are wrong) and
`checks.should_any` (at least one must match). They encode **current policy** (for example "do not flee an adjacent below-Tough attacker"), not engine
rules, and are judged on the model's raw choice before the brain's own safety overrides. Edit or add scenarios freely: copy a state from
`last_state.json` after a bad moment and write the check you wish the model had passed.

## Thinking models (found 2026-10-06 with gemma-4-12b)

`google/gemma-4-12b` thinks before it answers. With the brain's 128-token cap every call ended `finish=length` with 390 to 456 characters of reasoning and an **empty answer**
(19 identical "Expecting value" errors in the first lab run). What worked and what did not, measured against the loaded model in LM Studio:

| extra request setting | result |
|---|---|
| `{"chat_template_kwargs": {"enable_thinking": false}}` | no effect: still thinks, still empty |
| `{"reasoning_effort": "low"}` | no effect: still thinks, still empty |
| `{"reasoning_effort": "none"}` | **works**: valid JSON replies in 4 to 5 seconds (measured with two models loaded and the game up, so a clean load should be faster) |

Use it with `python tools/model_lab.py --models google/gemma-4-12b --extra "{\"reasoning_effort\": \"none\"}"`, and for a real run with the same settings via the environment variable
`QUDAI_LLM_EXTRA` (and `QUDAI_LM_MODEL`). Other thinking models (Qwen3.5, gpt-oss, deepseek-r1) may want a different setting; the lab will show `empty` for them if it does not take.

## Caveats (be honest with the numbers)

- 9 scenarios x 3 repeats is a small sample: treat differences of one or two points as noise. Use `--repeat 5` and add scenarios before deciding.
- The lab judges single decisions, not whole runs. A model can score well here and still lose runs through slowness or a long chain of small mistakes.
- Policy checks reflect the project's current opinions. A model that disagrees with a check is not necessarily wrong; read the "Policy failures" list.
- Results depend on LM Studio settings (context length, GPU offload, KV cache). Record them with the results when you compare.

## First baseline (2026-10-06, `ministral-3-8b-instruct-2512`, 2 repeats)

score 83.3%, parse 100%, menu 100%, policy 83.3%, p50 2.93 s, p95 3.38 s, all in time, same-action 88.9%, GPU 7770 MiB with the game running.
Policy failures: fired Lase through the pet (`pet_in_line_of_fire`; the brain's line-of-fire guard normally catches it) and opened with Stunning Force against a
group of Impossible jells (`jell_group_at_range_full_hp`).

## Second data point (2026-10-06, `google/gemma-4-12b` with `{"reasoning_effort": "none"}`, 3 repeats, `--no-manage`)

score 77.8%, parse 100%, menu 100%, policy 77.8%, p50 3.51 s, p95 4.37 s, all in time, same-action **100%**. It failed the same two scenarios as ministral
(Lase on the Impossible jell group, Lase through the pet). Measured with ministral still loaded beside it and the game running (GPU 15.6 GB, RAM 27.7 GB in use), so
speed would likely be better on a clean load. On this sample it is **not better than ministral-3-8b** (77.8 vs 83.3 is within the noise of 27 vs 18 runs); it is more
stable run to run and costs 1.4 GB more VRAM. Neither model "knows" to keep Lase off Impossible enemies or off a line with the pet in it: the brain's own guards do that.

## Third data point (2026-10-06, `qwen/qwen3-vl-8b-instruct`, 5 repeats, managed load: context 8192, 1 slot, gpu max)

score **88.9%**, parse 100%, menu 100%, policy 88.9%, p50 **2.68 s**, p95 3.05 s, all in time, same-action 100%, load 26.7 s, GPU 9416 MiB and RAM 22.8 GB in use (the game was closed;
ministral restored afterwards). One policy failure: it opened with Stunning Force on the Impossible jell group (the brain's border retreat normally intercepts that).
It is the **only model so far that passed `pet_in_line_of_fire`** (it chose to move instead of firing through the pet).

| model | runs | score | p50 s | same-action | note |
|---|---|---|---|---|---|
| qwen/qwen3-vl-8b-instruct | 45 | 88.9% | 2.68 | 100% | no thinking, no extra settings needed |
| ministral-3-8b-instruct-2512 | 18 | 83.3% | 2.93 | 88.9% | current model; only 2 repeats, loaded with LM Studio's own settings |
| google/gemma-4-12b (reasoning off) | 27 | 77.8% | 3.51 | 100% | needs `{"reasoning_effort": "none"}`; measured with two models loaded |

The three were not measured under identical conditions (repeats and load settings differ), and the gaps are a few points on 18 to 45 runs: **treat the order as a lead, not a verdict**.
A like-for-like run of ministral (`--models ministral-3-8b-instruct-2512 --repeat 5`, same managed load) is the next fair comparison.
