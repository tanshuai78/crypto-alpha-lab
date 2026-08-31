# Known Closure Revision Failure Patterns

These patterns are drawn from repeated Design/Plan revision failures in this project. Use them as adversarial self-checks.

## Pattern 1 — Shape Fixed, Primitive Contract Still Ambiguous

Bad revision:

```text
review asks to freeze nested schema
revision names required fields
but leaves integer/decimal/timestamp token grammar undefined
```

Check the entire serialized contract, not just key names.

## Pattern 2 — Precedence Fix Creates A Second Reducer Conflict

Bad revision:

```text
first-match response reducer
+ separate post-outcome durability failure
without explicit supersession
```

Check multi-layer precedence and simultaneous failures.

## Pattern 3 — Fix Introduces A Serialization State With No Legal Enum

Bad revision:

```text
new terminal intent = complete:null
observation enum has only continue/blocked/failed
```

Every new internal intent must have an exact serialized mapping or remain explicitly non-serialized.

## Pattern 4 — Safety Static Gate Rejects An Approved Literal

Bad revision:

```text
ban substring "event_time"
approved ProfileCore contains "realized_funding_event_time_ms"
```

Use specific forbidden dependencies, not generic semantic words.

## Pattern 5 — Lock Test Accidentally Creates Root Resume

Bad revision:

```text
runner B same run ID waits for runner A lock
then acquires existing root after release
```

Lock primitive handoff is not runner/root lifecycle authority. Fresh/no-resume runner must hard reject existing root.

## Pattern 6 — Artifact Producer Exists Only On Happy Path

Bad revision:

```text
capability_summary produced only after final P4 success
but blocked/failed states also require complete state vector
```

Check every sibling terminal state in State × Artifact matrix.

## Pattern 7 — Verifier Mistaken For Producer

Bad revision:

```text
closed-tree verifier expects capability_summary.json
Plan never schedules code to write it
```

Every required artifact needs a production owner/task.

## Pattern 8 — Config Gate Checks One Safety Flag, Not Exact Delta

Bad revision:

```text
configs/base.py is allowlisted
completion only asserts RISK_LIVE_TRADING_ENABLED=False
```

Prove exact additive AST/module delta where required.

## Pattern 9 — Capacity Formula Omits Reserved Bytes

Bad revision:

```text
ROOT_MAX >= workload
```

when Design requires:

```text
ROOT_MAX - ordinary_reserve - emergency_reserve >= workload
```

Reproduce exact invariant algebra.

## Pattern 10 — Review Fix Is Semantically Right But Evidence Is Weaker

Bad revision:

```text
review requires all-terminal-path summary coverage
revision adds prose but only P4 success test
```

Mechanical evidence must match exact closure criterion.

## Pattern 11 — Review Feedback Applied Sequentially

Bad process:

```text
fix P0-1
save
fix P0-2
save
fix P0-3
```

without checking that P0-3 invalidated P0-1.

Use one blocker ledger, interaction analysis, one patch, cross-fix pass.

## Pattern 12 — No-Touch Drift

Bad revision:

```text
fix reducer
also rename endpoint/profile fields for cleanliness
```

Unrelated frozen edits create fresh review surface. Enforce Mutable / No-Touch sets.
