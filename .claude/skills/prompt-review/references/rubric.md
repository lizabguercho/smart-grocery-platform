# Prompt review rubric

Everything here is a heuristic grounded in the sources at the bottom. Thresholds are starting points to recalibrate against our own evaluation data (see "Calibration").

## 1. Load (intrinsic task difficulty)
Question: how much must the model get right at once?

**Constraint units K.** Count independent requirements the output must satisfy (rule bullets, field-level rules, format rules). Research finds compliance collapses multiplicatively: if each constraint passes with probability p, all pass with p^K; reported breakdown is around 5-6 simultaneous constraints for weaker models and beyond ~10 for stronger ones. Bands used by the script (K per call): small ≤6 comfortable / ≤10 risky; mid ≤10 / ≤16; frontier ≤16 / ≤28. Over the band -> recommend SPLIT.

**Decision table.** Classify each required decision:
| Class | What it is | Typical failure | Mitigation |
|---|---|---|---|
| Copy | Reproduce a span from the input | typos, normalising what should be verbatim | verify with substring check in code |
| Classify | Closed-set label by an explicit rule | boundary cases, label drift | define each label and its boundary; test per-label |
| Recall | Needs knowledge not in the input (memory) | confident invention | forbid or allow-null; supply the fact or look it up |
| Compute | Arithmetic, unit conversion, counting, sorting | silent errors, compounding | **move to code**; ask only for source values |
| Multi-hop | Decision B depends on decision A's result | error propagation across steps | split into stages, validate between stages |
| Judge | Open-ended quality call | inconsistency | rubric with anchors, or drop |
Compute and Multi-hop are the expensive classes: models learn single steps but struggle to chain them, and errors compound with depth (Faith and Fate). The cheapest reductions are: (a) delete decisions the code can derive, (b) delete duplicated output fields, (c) replace Recall with provided data, (d) split Multi-hop chains.

Also note width (many parallel fields) versus depth (chained dependencies): width is cured by splitting independent groups, depth by staged calls with checks.

## 2. Coherence (does it agree with itself and its surroundings)
Check: contradictory rules; a rule that makes another unreachable; priority undefined when two rules collide; schema versus rules (field described in rules but absent or named differently in schema, or the reverse); prompt versus annotation guidelines / validator (what the prompt asks may differ from what is scored); one term used for two things, or two terms for one; examples that violate the rules (none allowed in zero-shot prompts). Fix: delete the weaker rule, state a priority order, align names, or change the guideline on purpose (and version it).

## 3. Ambiguity (could two careful readers act differently)
Check: undefined terms and thresholds; vague quantifiers and hedges ("relevant", "plausible", "usually", "similar", "if needed", "etc."); missing null/unknown policy; no tie-break when several candidates qualify; no acceptance criterion or output format for an edge case; scope of a condition unclear ("only if" attached to what?); implicit reference to knowledge the model may not have. Test: give the prompt to a colleague with no context; where they would ask a question, that is a finding. Fix: define, bound with a rule, give the null policy.

## 4. Structure
Check: critical constraints buried in the middle of a long prompt (models use the start and end best; earlier instructions tend to win); rules mixed with schema mixed with background; absent separation between instructions and data; rules that are structural/format-exact (these degrade faster than lexical ones) -> enforce in the parser or with constrained decoding instead of prose; negations stacked on negations. Fix: order (task, schema, rules, null policy, final reminder of the 1-2 most critical rules), group by purpose, delimit the input.

## 5. Efficiency (extraneous load)
Check: near-duplicate sentences; background the task does not use; rules that restate the schema; fields the downstream code ignores or can derive; length relative to the task. Extraneous load, not just difficulty, drives failures. Fix: delete; shortest wording that keeps the behaviour; re-measure.

## 6. Hygiene
- **Leakage**: any real item from dev or test data in the prompt (titles, nouns, number patterns), including "illustrative" ones. Blocker. The script flags corpus overlap; also judge by eye.
- **Versioning**: prompt hash stored with each run; one change per version.
- **Testability**: every rule maps to a measurable check or a label in the evaluation; a rule that no metric can see cannot be tuned.
- **Output contract**: parser failure modes (escaping, truncation) handled outside the prompt.

## Output semantics: independent actions, validity, measured evidence
A review answers three different questions; they are never collapsed into one score.
1. **What should change?** A set of independent *actions*, one per dimension that has a finding: SPLIT (load, chained decisions), MOVE-TO-CODE (compute, derivable fields), FIX-COHERENCE, CLARIFY (ambiguity), REORDER (structure), TRIM (efficiency). They are orthogonal: a high-load but coherent prompt needs SPLIT; an easy prompt with contradictions needs FIX-COHERENCE; one is not "better" than the other, and a prompt can need several. Labels carry no priority.
2. **Can the scores be trusted?** *Validity*: `invalid` if dev/test data leaked into the prompt or the output contract is unreadable by design. This is a property of the evaluation, not of the prompt's quality.
3. **How well does it work?** *Measured evidence* only: consistency and accuracy from runs (below). A static review can say why something might fail; it cannot say how often it does. Until measured, the table says "not measured".
The **order of work** is decided by evidence: first the actions aimed at errors already measured, then cost to verify. K and P(all pass) are shown to explain a SPLIT, not as a goal: deleting rules to lower K while the behaviour is still required only moves the work.

## Measured evidence: consistency
Consistency is not one thing. Measure four, each answering a different cause (`src/prompt_registry/consistency.py` has the pure functions):
- **Run-to-run (sampling) agreement**: k samples per item (e.g. k=5, temperature 0.5-0.8; temperature 0 only tests batching/quantization noise). Per field: share of samples giving the modal answer, and entropy of the answer distribution; invalid output counts as a disagreement ("<failed>"), never as empty. For short discrete answers, answer-level instability tracks errors well and needs no semantic model (ACL SRW 2026 result in sources). Limit: an overconfident model can be consistently wrong.
- **Prompt sensitivity**: score the same items under 3-5 intent-preserving variants (reordered rules, paraphrased wording, different delimiters). Report the **range**, not one number (FormatSpread; POSIX is the likelihood-based version and needs logits). Reported effects are large and not removed by model size or instruction tuning; one exemplar often reduces sensitivity (POSIX), which conflicts with our no-real-examples rule: use placeholder-only demonstrations if a test shows the gain.
- **Model sensitivity**: the same measurements on the target model and on a larger reference. The gap isolates capacity from ambiguity.
- **Field attribution**: attribute instability to the field, then to the rules that govern that field (keep a field->rules map in the REVIEWS entry), so the fix points at specific lines.

Reading the pattern (`consistency.diagnose`; hypotheses to test, not proof):
| Pattern | Likely cause | Action |
|---|---|---|
| consistent, accurate | nothing visible | NONE |
| consistent, wrong | systematic misreading: prompt vs guideline/gold mismatch, or a contradiction resolved the same way each time | FIX-COHERENCE |
| inconsistent on small, consistent on reference | capacity: too much per call | SPLIT / MOVE-TO-CODE |
| inconsistent on both | ambiguity: prompt underdetermines the answer | CLARIFY |
| score range large over harmless rewrites | fragile prompt | REORDER, enforce structure in parser/decoding |
| inconsistent only on fields with chained rules | multi-hop | SPLIT into stages with a check between |

How much the model matters: report the consistency gap between tiers per field. A prompt that is stable on a strong model and unstable on a small one is a load problem; one unstable on both is a specification problem. This is why the review states a target tier.

## Calibration (must be done, then this section updated)
1. Back-test the static flags against measured consistency and per-field error on prompt versions with known results (measurement-qwen v0.1.0 and v0.2.0): do FIX-COHERENCE/CLARIFY/SPLIT findings coincide with the fields that are inconsistent or wrong? Record in `docs/models/*/CHANGELOG.md`.
2. Regress per-field error rates on the rules that govern them; a rule family with high error and high K contribution is where to split first.
3. Adjust the tier bands when a model's measured compliance differs from the literature.

### Back-test log
- 2026-11-14, tier small, measurement-qwen prompts: v0.1.0 K=7 (risky), 4 literal nouns/units that also occur in dev/test titles (leakage flag), ~500 tokens; v0.2.0 K=13 (over), no corpus overlap, ~940 tokens. The script flags validity (v0.1.0 leakage) and load (v0.2.0 over band) on different axes; neither is "worse" overall. Measured dev results: v0.2.0 better on presence recall and role/scope, but not on exact titles (66 vs 67), consistent with "more rules, same total compliance". One data point: not yet a calibration.

- Prompt sensitivity: Sclar et al., FormatSpread (arXiv 2310.11324, https://arxiv.org/abs/2310.11324: up to 76 accuracy points from formatting alone on LLaMA-2-13B; report ranges); POSIX prompt sensitivity index (arXiv 2410.02185, https://arxiv.org/abs/2410.02185: paraphrase vs template effects; one exemplar reduces sensitivity; size/instruction tuning do not necessarily).
- Consistency as signal: answer-level entropy / agreement across samples (ACL SRW 2026, https://aclanthology.org/2026.acl-srw.72.pdf); semantic entropy; self-consistency collapses when the model is consistently wrong.

## Sources
- Constraint count and compounding: RECAST, multi-constraint data (arXiv 2505.19030, https://arxiv.org/abs/2505.19030); How Many Instructions Can LLMs Follow at Once? (arXiv 2507.11538, https://www.alphaxiv.org/abs/2507.11538, early-instruction bias, degradation patterns by model size); Compositional constraint satisfaction phase transitions (arXiv 2608.12426, https://arxiv.org/html/2608.12426; single-paper, multiplicative model, structural > lexical degradation); UNSPECIFIC (arXiv 2608.09154).
- Composition, depth/width, error propagation: Faith and Fate: Limits of Transformers on Compositionality (NeurIPS 2023, https://arxiv.org/abs/2305.18654); circuit/communication-complexity survey (arXiv 2602.11175).
- Cognitive load (intrinsic versus extraneous): Cognitive Load Limits in LLMs (arXiv 2509.19517, https://arxiv.org/html/2509.19517v2); Cognitive Load Theory for LLM coordination (arXiv 2506.06843). Note: load components may not be additive.
- Prompt defects: A Taxonomy of Prompt Defects in LLM Systems (arXiv 2509.14404, https://arxiv.org/pdf/2509.14404) - six dimensions: specification and intent, input and content, structure and formatting, context and memory, performance and efficiency, maintainability.
- Underspecification: Ambig-SWE (arXiv 2502.13069); detecting and rewriting underspecified questions (arXiv 2602.11938); detection and asking are separate, weak skills in models.
- Position: Lost in the Middle (arXiv 2307.03172, https://arxiv.org/pdf/2307.03172).
- Decomposition: Anthropic, chain prompts (https://docs.anthropic.com/en/docs/chain-prompts) - split into subtasks, isolate and tune the failing step; chain only when it removes more errors than the handoffs cost.
- Eval hygiene: holdout, no eval items in prompts (https://arize.com/glossary/data-leakage/).
Several sources are preprints or single-team results; treat numbers as indicative.
