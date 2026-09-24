---
trigger: always_on
---

---
type: rule
name: L2 – Alpha Research Methodology
---

# L2 – Alpha Research Methodology

**Priority:** PROJECT RESEARCH POLICY (Level 2). This rule is subordinate to L0 Financial Safety and L1 Engineering Process. It is mandatory for alpha discovery, strategy research, event studies, replay/backtest work, factor research, strategy promotion/falsification, and any claim about expected return, PnL, economic edge, or strategy quality.

## 1. Core Principle

Alpha is **not** defined by per-trade certainty, monotonic behavior, or win rate alone.

A strategy may qualify as an `alpha_candidate` only when a preregistered and implementable rule shows evidence of **positive expected value after realistic costs across independent opportunities**, while drawdown, tail loss, margin stress, execution failure and net-exposure uncertainty remain survivable under L0 constraints.

Therefore:

```text
some losing trades != falsified alpha
high win rate != proven alpha
observed market phenomenon != alpha
positive gross return != executable alpha
positive expectancy != permission to trade
```

Safety invariants remain deterministic. Alpha claims are probabilistic and must state their uncertainty.

## 2. Research Status Vocabulary

Use these meanings consistently:

- `hypothesis_only`: economic mechanism proposed; evidence not yet sufficient to establish the phenomenon.
- `phenomenon_supported`: the market/event pattern is supported by admissible evidence, but no strategy edge is claimed.
- `alpha_candidate`: a preregistered rule has credible evidence of positive cost-adjusted expectancy under the required research gates; live safety is not implied.
- `alpha_validated`: the candidate has passed robustness, executable-cost, capacity, survival and required shadow gates for the scope explicitly tested. This is still not live-trading authority.
- `evidence_insufficient`: current evidence cannot decide the research claim; do not force pass/fail.
- `falsified`: the preregistered claim failed its valid kill criteria with sufficient admissible evidence.

Do not use `falsified` merely because some observations lose, move in the opposite direction, or fail to behave monotonically.

## 3. Mandatory Separation of Claims

Every alpha-research Design must distinguish at least:

```text
phenomenon_claim
statistical_edge_claim
economic_edge_claim
execution_feasibility_claim
capital_survival_claim
live_permission_claim
```

A lower claim must never silently upgrade a higher claim. In particular:

```text
phenomenon_supported
!= alpha_candidate
!= executable_edge
!= live_safe
```

If current stage permissions set `alpha_interpretation_allowed = False` or equivalent, the stage may produce only the explicitly permitted lower-level diagnostic claims.

## 4. Independent Opportunity Is the Statistical Unit

Before any win rate, confidence interval, bootstrap, split, cross-validation, or significance calculation, define the independent sampling unit.

Examples include:

- one `parent_article_id` when multiple contracts share one announcement;
- one independent funding episode rather than every settlement inside the same episode;
- one launch event rather than every derived symbol row if they share the same catalyst;
- one regime episode rather than overlapping rolling windows.

Rules:

1. Correlated children from the same parent event must not be counted as independent evidence.
2. The same parent/episode must not cross train/test or in-sample/out-of-sample boundaries.
3. Calendar duration is not a substitute for independent sample count. A year with five independent events is still a five-event sample.
4. Contract-level results may be reported diagnostically, but promotion/falsification decisions must use the declared independent unit.

## 5. Pre-Registration and Anti-Hindsight

Before evaluating outcomes, freeze the research rule appropriate to the current stage:

```text
hypothesis
independent unit
entry/observation anchor
exit or evaluation horizon
allowed features
cost assumptions permitted at this stage
loss/MAE analysis method
kill criteria
promotion criteria
```

Do not tune thresholds, stops, horizons, filters, or subgroup definitions after seeing outcomes and then present the tuned result as confirmatory evidence.

Exploratory findings are allowed, but they must be labeled `exploratory` and require a new preregistered validation stage or independent sample before promotion.

## 6. Outcome Distribution, Not Win Rate Alone

Where the stage permits strategy-like evaluation, report the distribution rather than a single success rate. At minimum, when sample size allows:

```text
n_independent_opportunities
win_rate
mean_outcome
median_outcome
average_win
average_loss
payoff_ratio
P10/P25/P50/P75/P90
maximum_loss
MAE
MFE
```

The core economic quantity is expectancy, conceptually:

```text
Expected Value
= P(win) * AvgWin
- P(loss) * AvgLoss
- Realistic Costs
```

A low-win-rate/high-payoff strategy may be valid. A high-win-rate/large-tail-loss strategy may be invalid.

Do not impose a universal `win_rate > 50%` rule.

## 7. Cost, Friction and Executability Layers

`AGENTS.md` requires strategy discussions to consider fees, slippage, liquidity, holding risk, margin, net exposure and exchange-specific failure modes. Under L2, they participate in alpha evaluation as follows.

### 7.1 Expected-Value Cost Layer

Where evidence exists, include or reserve for:

- exchange fees;
- funding payments/receipts;
- borrow/financing cost;
- expected slippage;
- ordinary spread crossing;
- settlement/closing fees;
- other directly attributable holding costs.

Do not fabricate a precise net PnL when executable prices or required cost evidence are absent. Use `gross_only`, `cost_context_only`, or `evidence_insufficient` as appropriate.

### 7.2 Liquidity and Capacity Layer

Evaluate whether the observed edge can support economically meaningful size:

- visible/executable depth;
- spread and market impact;
- position-size sensitivity;
- event frequency;
- deployable capital;
- dollar alpha relative to engineering and operational burden.

A statistically positive edge with negligible deployable capacity may be economically irrelevant.

### 7.3 Holding and Path-Risk Layer

Evaluate the path, not only entry-to-exit endpoints:

- MAE / adverse basis expansion;
- drawdown duration;
- Funding Flip or carry reversal;
- gap risk;
- liquidation distance;
- correlated losses during the same market regime.

A strategy whose terminal thesis is correct but whose path commonly causes liquidation or unacceptable drawdown fails the survival gate.

### 7.4 L0/L1 Safety Boundary

Net exposure uncertainty, partial fills, unknown remote order state, API failures, exchange rule mutation, rollback, margin failure, deposit/withdrawal restrictions and similar failure modes are not merely statistical costs. They remain governed by L0/L1 and execution invariants.

L2 may require them to be measured or modeled; it must never redefine or weaken the underlying safety invariant.

## 8. Losses, Stop-Losses and Tail Risk

Losses are expected observations, not automatic research failures. However, accepting losses requires an explicit loss model.

Every strategy-like study must identify, as applicable:

```text
normal_loss_mechanism
abnormal/tail_loss_mechanism
maximum_observed_loss
MAE_distribution
consecutive_loss_risk
correlated_event_loss
liquidation_or_gap_risk
```

A stop-loss is a research object, not a magic safety guarantee.

Rules:

1. Do not optimize a dense grid of stop thresholds and select the best after the fact.
2. First inspect the MAE distribution and execution semantics.
3. Candidate stops must be preregistered or clearly exploratory.
4. A price threshold is not an `executable_stop` unless market depth, gap/slippage and order behavior support that claim.
5. Positive expectancy must not be used to excuse unbounded tail loss or material risk of ruin.

## 9. Outlier and Concentration Dependency

A strategy may legitimately earn much of its return from fewer large winners, but that dependence must be measured.

Where sample size permits, report:

```text
top_1_contribution
top_3_contribution
top_10pct_contribution
result_without_best_event
parent/regime concentration
```

Classify results as `outlier_dependent` when removal of a very small number of independent events destroys the claimed edge. Such a result is not automatically falsified, but it cannot be promoted without an explicit economic mechanism and independent validation.

## 10. Conditional Alpha Is Allowed

An unconditional event family may have no edge while a preregistered, economically motivated subset does.

Permitted logic:

```text
event + pre-existing context/state -> conditional expectancy
```

Examples of admissible context may include liquidity regime, normalized OI state, basis state, funding state, volatility regime, or market-wide regime, provided the context is point-in-time available and defined before outcome inspection.

Do not create ever-narrower post-hoc subgroups until one becomes profitable.

## 11. Research Gate Ladder

Use the following conceptual ladder. A stage may intentionally stop at an earlier gate.

### Gate A — Mechanism / Phenomenon

Question: Is the hypothesized market phenomenon real and correctly measured?

Possible outcome:

```text
phenomenon_supported | evidence_insufficient | falsified
```

### Gate B — Candidate Statistical Edge

Question: Does a preregistered rule show a plausible positive outcome distribution across independent opportunities?

Win rate alone is insufficient.

### Gate C — Robustness

Check as applicable:

- independent out-of-sample evidence;
- parent/regime grouped splits;
- sensitivity to reasonable rule perturbations;
- outlier dependence;
- temporal and cross-symbol stability;
- multiple-testing / parameter-search contamination.

### Gate D — Economic / Executable Edge

Question: After admissible costs, liquidity, slippage and capacity, does meaningful edge remain?

### Gate E — Capital Survival

Question: Are drawdown, MAE, margin stress, tail loss, correlated losses and execution failure paths compatible with L0 capital preservation?

### Gate F — Shadow Validation

Any entry/exit/sizing behavior intended for live use must still satisfy L0-required shadow validation for at least one complete strategy cycle before live-safe treatment.

No L2 gate grants live or paper-trading permission.

## 12. Promotion, Kill and Evidence-Gap Semantics

Each alpha-research Design must predefine stage-appropriate outcomes.

### Promote

Promotion is allowed only when the current stage's exact claim is supported without silently claiming a higher gate.

### Kill

Valid kill reasons include, as applicable:

- admissible evidence shows cost-adjusted expectancy at or below the benchmark;
- the claimed phenomenon is absent;
- edge exists only after the actionable window;
- tail/MAE behavior is incompatible with survival constraints;
- capacity/economic significance is negligible for the project's capital scale;
- results are irreducibly dominated by invalid or non-PIT evidence;
- robustness tests invalidate the preregistered rule.

The existence of losing trades by itself is not a kill criterion.

### Evidence Gap

Use `evidence_insufficient` / `EVIDENCE_GAP` when the required conclusion cannot be supported or falsified from current admissible evidence. Do not convert missing data into a negative alpha conclusion.

## 13. Historical Falsifications Are Not Automatically Reopened

Adopting this methodology does not retroactively revive `falsified`, `stopped`, or `superseded` strategies.

A historical route may be reconsidered only through a separate documented methodology audit showing that:

1. the old kill decision materially depended on a criterion now recognized as invalid or incomplete (for example, win rate alone without payoff/expectancy analysis); and
2. the original evidence remains admissible or can be re-evaluated without hindsight contamination.

Routes killed because cost-adjusted edge was non-positive, evidence was invalid, or safety/execution constraints failed remain closed unless genuinely new evidence changes the claim.

## 14. Research Portfolio Perspective

The project may accept multiple low-frequency or modest-capacity alpha sources if each has a defensible positive expectancy and their risk drivers are sufficiently distinct.

Do not require one strategy to provide all project returns. Evaluate, when relevant:

```text
opportunity_frequency
capital_occupancy
deployable_capacity
correlation_to_other_alpha
marginal_portfolio_drawdown
engineering/operational_cost
```

Portfolio diversification never authorizes relaxing strategy-level evidence or L0 safety gates.

## 15. Mandatory Design Requirements for Alpha Research

Any Design whose purpose includes alpha discovery, strategy evaluation, replay/backtest, event study, factor research, strategy promotion/falsification, or economic-edge claims must explicitly define or mark `N/A` with justification for:

```text
1. Alpha / economic mechanism hypothesis
2. Exact claim level for this stage
3. Independent sampling unit and cluster rules
4. Point-in-time / anti-hindsight boundary
5. Preregistered observation or strategy rule
6. Outcome-distribution metrics
7. Cost/friction scope for this stage
8. Liquidity/capacity scope
9. Loss / MAE / tail-risk analysis
10. Outlier/concentration dependency test
11. Conditional-alpha rules, if any
12. Promotion criteria
13. Kill criteria
14. Evidence-gap semantics
15. Explicit claims deferred to later gates
```

A Design must not manufacture strategy thresholds solely to satisfy this checklist. If current evidence is descriptive only, the Design should say so and defer strategy-like gates.

## 16. Plan and Implementation Discipline

Implementation Plans and executors must not invent or optimize research semantics that were not approved in the Design.

In particular, a Plan must not independently choose:

```text
entry threshold
exit threshold
stop-loss
holding horizon
subgroup filter
cost assumption
benchmark
promotion threshold
kill threshold
```

unless the approved Design explicitly delegates that choice with a bounded deterministic procedure.

Unexpected need to change these semantics is `BLOCKED_SPEC_DRIFT` or requires a new/revised Design, not an implementation-time convenience.

## 17. Final Rule

For alpha discovery, ask:

> Is risk being mispriced in a way that produces a reproducible, cost-adjusted positive expectancy across independent opportunities, while the path and failure modes remain survivable?

Do **not** ask only:

> Does every trade win?

And do **not** accept:

> The average backtest is positive, therefore it is safe or executable.
