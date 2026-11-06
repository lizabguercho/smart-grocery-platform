# Model lifecycle

The process every model in this repository follows, whatever the model is
(rules, a prompted LLM, a fine-tuned model, a cascade of those). It exists so
that any conversation can be closed and any colleague can take over a model
and know exactly where it stands and what comes next.

Where each model stands today: [MODEL_STATUS.md](MODEL_STATUS.md) (generated).
How to record a change: the **Procedure** section below and
[CONTRIBUTING.md](../CONTRIBUTING.md#model-lifecycle-and-status).

## The loop

```text
 define task ─► data & gold ─► baseline inference ─► error analysis
                                                          │
              ┌───────────────────────────────────────────┤
              ▼                                           ▼
     prompt / rule engineering ─► inference ─►  (back to error analysis)
              │
              │  prompt plateau + enough separate training data
              ▼
         fine-tuning ─► inference ─► error analysis ─► prompt engineering ─► inference ─► …
                                          │
                                          ▼
                       freeze ─► frozen evaluation (test, once) ─► released ─► monitoring
```

Every pass through the loop is one **version** with one changelog entry.

## Stages

| Stage | The model is here when | Exit criterion |
|---|---|---|
| `baseline-inference` | the first run of the simplest reasonable system (rules, or the zero-shot prompt) is being produced | predictions exist for the whole development set |
| `error-analysis` | predictions exist and are being read against gold | errors grouped by cause; the next change is chosen from them |
| `prompt-engineering` | prompt, rules, routing or decoding are being changed (rule engineering counts) | one change set is ready; nothing else changed with it |
| `inference` | the changed system is being run on the same development set | predictions exist; same scored titles as before |
| `fine-tuning` | training a new model or adapter on **training data separate from dev and test** | adapter or checkpoint saved and traceable |
| `frozen-evaluation` | everything is frozen and the test set is scored | one test run, results recorded, no tuning afterwards |
| `released` | the version passed the agreed bar and is accepted for use | – |
| `monitoring` | the released version is tracked on fresh samples for drift | a new loop starts when the bar is missed |

A model can step back to an earlier stage; it can never skip the evaluation
between two changes. Typical sequence: baseline-inference → error-analysis →
prompt-engineering → inference → error-analysis → … → fine-tuning → inference →
error-analysis → prompt-engineering → inference → … → frozen-evaluation.

## Rules that keep the loop honest

1. **Task and metrics first.** Written annotation guidelines and metric
   definitions exist before the first inference.
2. **Three disjoint data roles.** *Development* (tune freely), *training*
   (only for fine-tuning, never overlaps dev or test), *test* (fresh, hidden).
   Test titles are not read, mined or used for examples while developing.
3. **One change per version.** Change the prompt, or the rules, or the model,
   or the decoding, or the routing, not several at once, so a score change has
   one cause. If a bundle is unavoidable, say so in the entry.
4. **Same scored items.** Compare versions on the same gold items. Failed
   outputs (invalid JSON, timeouts) count as failures, never as "empty".
5. **Gold is human.** Model or assistant output may draft labels only when it
   stays identifiable (annotator field) and the human confirms; report such
   items separately.
6. **Test is spent once.** After a test evaluation, that test set becomes
   development data. A new independent claim needs a fresh test set.
7. **Fine-tuning needs its own data.** Do not fine-tune on the dev gold used
   for prompt decisions, and never on test labels.
8. **Cascades depend on versions.** A cascade names the exact versions of its
   components; it is re-evaluated whenever a component changes.

## Versioning

`MAJOR.MINOR.PATCH`, per model.

- `0.x.y`: before the first frozen evaluation.
- **MINOR** (`0.1.0 → 0.2.0`): any change that can alter predictions: prompt
  text, rules, model weights or revision, quantization, decoding settings,
  routing policy, fine-tuning.
- **PATCH**: nothing that alters predictions (a bug fix in logging, a doc fix,
  re-scoring with a corrected evaluator). Record why predictions are unchanged.
- `1.0.0`: the first version that passed a frozen evaluation and is released.
  Later changes are `1.1.0` and so on; a new frozen evaluation needs a fresh test set.

## Procedure (every time a model changes)

1. Make **one** change. Note the version you are moving to.
2. Run inference on the same development set. Keep the predictions file; do
   not overwrite the previous version's file (name it with the version or keep
   it in `predictions/`).
3. Score with the shared evaluator on the same scored items.
4. Add a **new entry at the top** of `docs/models/<model>/CHANGELOG.md`
   (format below) and update its header's `Next step`.
5. Run `PYTHONPATH=. uv run python scripts/build_model_status.py` and commit
   the regenerated `docs/MODEL_STATUS.md` together with the changelog.
6. Commit the code and artifacts the entry refers to, and write the commit
   hash in the entry (or `uncommitted` if it truly is not committed yet, and
   fix that before handing over).

## Changelog format

`docs/models/<model-id>/CHANGELOG.md`:

```markdown
# Changelog — <model-id>
Owner: <github login>
Task: <one line>
Depends on: <other model ids and versions, or empty>
Next step: <the single next action>

## 0.2.0 — 2026-11-05 — stage: prompt-engineering
- **Change:** what changed, and only that.
- **Why:** the error-analysis finding that motivated it.
- **Artifacts:** files, prompt hash, model revision, decoding, commit.
- **Evaluation:** which set, which items, the numbers, a link to the report.
- **Findings:** what the results say; limits (sample size, tuned-on-dev).
- **Decision / next:** what happens next and why.

## 0.1.0 — 2026-11-01 — stage: error-analysis
...
```

Rules for the file: newest entry first, unique ascending-valid versions, the
`stage:` is the stage the model is **in after** that entry, and the header
block (`Owner`, `Task`, `Next step`) is always present. `build_model_status.py`
refuses malformed changelogs.

## Handover checklist (closing a conversation or changing owner)

- The newest changelog entry is complete and its commit exists.
- `Next step` in the header states the single next action and who does it.
- `docs/MODEL_STATUS.md` is regenerated (`build_model_status.py --check` passes).
- Open questions or unresolved annotation decisions are written in the entry
  or in the task's guideline file, not only in a conversation.
- Running the next step needs only the repo and the entry (commands are written down).

## Backlog

Existing models not yet tracked here: the 12-class product classifier (Linear
SVM, ADR 0006) and the Hebrew→English name translator (`src/product_translation`).
Add a changelog for each when it is next touched, starting from its current
state as the first entry.
