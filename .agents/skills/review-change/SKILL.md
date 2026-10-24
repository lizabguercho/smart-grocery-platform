---
name: review-change
description: Review uncommitted CompetitorIQ changes for correctness, maintainability, architecture, security, testing, documentation, and scope without modifying files.
---

# Review Change

## Purpose

Use this skill when the user asks to review current repository changes.

This skill performs analysis only.

It must not:

- modify files;
- run automatic fixes;
- update the changelog;
- stage files;
- create commits;
- push branches.

The agent provides judgment. Repository inspection must be performed through the deterministic finalization script.

---

## Step 1: Inspect the Repository

Run:

```bash
uv run python scripts/finalize_change.py inspect
```

If the command fails, report the failure and stop.

Do not bypass the script with improvised Git commands unless the script itself is being repaired.

---

## Step 2: Read the Complete Changes

Review all changed files reported by the inspection command.

Inspect:

- unstaged changes;
- staged changes;
- newly created files;
- deleted files;
- renamed files.

Do not review only the diff summary.

Read enough surrounding code to understand:

- the intended behavior;
- the owning module, package, or service;
- relevant interfaces;
- relevant tests;
- architectural context.

Do not assume that untracked files are irrelevant.

---

## Step 3: Review Criteria

Evaluate the change using the following criteria.

### Correctness

Check whether:

- the implementation satisfies its intended behavior;
- important edge cases are handled;
- errors are handled appropriately;
- existing behavior is accidentally changed;
- return values and state transitions are correct;
- assumptions are explicit and valid.

### Maintainability

Check whether:

- names clearly communicate intent;
- responsibilities are cohesive;
- functions and classes remain reasonably focused;
- unnecessary complexity is introduced;
- duplicated knowledge is introduced;
- abstractions are justified by real usage;
- future modifications can be made safely.

### Architecture

Check whether:

- repository ownership boundaries are respected;
- packages do not depend on services;
- domain logic remains independent of delivery frameworks;
- application logic does not depend directly on infrastructure details;
- shared concepts have one authoritative owner;
- code is located at the narrowest appropriate scope;
- a durable architectural decision requires an ADR.

### Security

Check whether:

- secrets or credentials are exposed;
- untrusted input is validated;
- model output is treated as untrusted;
- authorization or business invariants depend on model judgment;
- logs expose sensitive information;
- subprocesses, paths, files, or external inputs are handled safely;
- destructive behavior is adequately guarded.

### Testing

Check whether:

- relevant tests are present;
- bug fixes include regression coverage when practical;
- expected behavior is tested;
- important failure paths are tested;
- tests are deterministic;
- external systems are replaced with controlled substitutes;
- tests meaningfully verify behavior rather than implementation trivia.

### Documentation

Check whether the change requires updates to:

- `README.md`;
- `docs/setup.md`;
- `docs/architecture.md`;
- `CONTRIBUTING.md`;
- environment-variable documentation;
- service or package documentation;
- ADRs.

Do not require documentation changes when the change has no documentation impact.

### Scope

Check whether:

- the change has one coherent objective;
- unrelated refactoring is included;
- broad dependency upgrades are mixed into feature work;
- generated files or caches are present;
- temporary debugging code remains;
- the contribution is reasonably reviewable.

---

## Step 4: Classify Findings

Classify every finding as either:

### Blocking

The workflow should not proceed until the issue is resolved.

Examples include:

- incorrect behavior;
- a security vulnerability;
- exposed credentials;
- broken architectural boundaries;
- missing essential validation;
- missing essential tests;
- destructive or unsafe behavior;
- changes whose purpose cannot be determined;
- a diff too broad to review safely.

### Non-blocking

The change can proceed, but an improvement is recommended.

Examples include:

- minor naming improvements;
- optional refactoring;
- additional test coverage that is useful but not essential;
- documentation polish;
- stylistic preferences not enforced by project tooling.

Do not classify personal preferences as blocking.

---

## Step 5: Produce the Review Result

Return the result using this structure:

```markdown
## Review result

**Decision:** Pass | Blocked

### Blocking findings

- None

or:

1. **Finding title**
   - File:
   - Problem:
   - Why it matters:
   - Required change:

### Non-blocking findings

- None

or:

1. **Finding title**
   - File:
   - Suggestion:
   - Benefit:

### Review coverage

- Correctness: Reviewed
- Maintainability: Reviewed
- Architecture: Reviewed
- Security: Reviewed
- Testing: Reviewed
- Documentation: Reviewed
- Scope: Reviewed
```

When possible, include exact file paths and relevant symbols or line locations.

Do not claim that tests, Ruff, formatting, or type checking passed during a review unless those commands were separately executed and verified.

---

## Decision Rule

Return `Pass` only when no blocking findings remain.

Return `Blocked` when at least one blocking finding exists.

A passing review does not authorize:

- formatting;
- changelog updates;
- commits;
- pushes.

Those actions belong to the `finalize-change` workflow.