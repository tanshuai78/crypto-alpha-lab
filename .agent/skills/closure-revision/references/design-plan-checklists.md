# Closure Revision Detailed Checklists

## 1. State × Artifact Sibling-State Prompts

For every affected terminal/state machine contract ask:

```text
What exists after success?
What exists after blocked?
What exists after failed?
What exists for not-probed/skipped siblings?
What exists after local write failure?
What exists after read-back/hash failure?
What must explicitly NOT exist?
What is consumable?
Can later work continue?
Can root/run be retried/resumed/reused?
```

Typical artifacts:

```text
raw
observation
state row
summary
terminal
manifest/seal
checkpoint/watermark
recovery/quarantine evidence
```

## 2. Transition × Failure Prompts

For every adjacent transition:

```text
A -> B
```

ask:

```text
failure before B?
partial B?
B durable but C not started?
read-back failure?
second simultaneous failure?
crash/restart behavior?
retry allowed?
resume allowed?
```

Freeze precedence when multiple failures coexist.

## 3. Authority Prompts

For every changed action verify:

```text
Who may approve document revision?
Who may modify src/config/scripts/tests?
Who may create production root?
Who may make external request?
Who may deploy/restart?
Does this revision accidentally upgrade authority?
```

Always preserve:

```text
Design approval != Plan approval
Plan approval != implementation authorization
implementation complete != deployment authorization
sealed evidence != alpha/trading authority
```

## 4. Invariant × Mechanical Evidence Prompts

For each changed invariant require:

```text
implementation owner
positive evidence
negative test
completion gate
```

Reject weak proxies.

## 5. Design Revision Checklist

```text
final claim unchanged
scope/non-goals unchanged
source-of-truth single and explicit
schema/enums exact
identity/hash projection exact
failure precedence unique
all sibling states modeled
artifact producer all required states
consumer/validator aligned
crash/restart/no-resume complete
PIT anti-hindsight preserved
manifest/seal exact
permission boundary unchanged
TCB unchanged
examples agree with normative text
```

## 6. Implementation Plan Revision Checklist

```text
Design invariant -> task -> RED test -> implementation -> GREEN -> completion gate
configs/base.py exact allowed delta
no old risk binding changes
changed-path allowlist exact
fresh baseline/provenance executable
Plan/Design SHA rebind executable
raw-before-parse/persistence ordering exact
failure precedence tested
lock primitive separate from runner lifecycle
shared resource values from current SSOT
all required artifact producer tasks exist
blocked/failed/not-probed producer paths exist
same-ID collision obeys fresh/no-resume
static gates do not reject approved schema literals
final code-review loop covers final diff
completion audit after final review
implementation/deployment permissions remain false
```
