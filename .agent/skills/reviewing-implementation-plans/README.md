# reviewing-implementation-plans v3

This skill reviews implementation, refactor, replay, research, deployment, and trading-strategy plans before execution.

Version 3 adds bounded execution and impact-analysis gates:

- mandatory `Allowed Change Scope` for state-mutating plans;
- Ponytail minimality below safety, approved Design, compatibility, existing architecture, and SSOT requirements;
- targeted Graphify discovery followed by source verification;
- `Affected but unchanged` coverage for compatible consumers;
- `rg` fallback for schema, JSONL, CLI, and file-path dependencies.

It retains the version 2 red lines for market-data evidence semantics:

- partial exchange streams;
- liquidation side preservation;
- coverage duration;
- runtime data commit policy;
- proxy metrics versus full-data thresholds.

Install under:

```text
.agent/skills/reviewing-implementation-plans/
```

Recommended trigger rule:

```text
When reviewing any implementation, refactor, bugfix, replay, research, deployment, or strategy plan, use the reviewing-implementation-plans skill before approving execution.
```
