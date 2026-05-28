# reviewing-implementation-plans v2

This skill reviews implementation, refactor, replay, research, deployment, and trading-strategy plans before execution.

Version 2 adds explicit red lines for market-data evidence semantics:

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
