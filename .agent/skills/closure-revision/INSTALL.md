# Install closure-revision in Antigravity IDE (project-local)

Recommended target:

```text
<project-root>/.agent/skills/closure-revision/
├── SKILL.md
└── references/
    ├── design-plan-checklists.md
    ├── revision-control-packet.md
    └── revision-failure-patterns.md
```

## macOS / Linux

From the project root:

```bash
mkdir -p .agent/skills
unzip -q ~/Downloads/closure-revision-skill-bundle.zip -d .agent/skills/
```

If the bundle is elsewhere, replace the zip path.

Verify:

```bash
test -f .agent/skills/closure-revision/SKILL.md
head -n 8 .agent/skills/closure-revision/SKILL.md
find .agent/skills/closure-revision -maxdepth 2 -type f -print
```

Expected main frontmatter:

```text
name: closure-revision
```

Then reload/restart the Antigravity workspace/session so its skill index is refreshed.

## Manual installation

Create:

```text
.agent/skills/closure-revision/
```

Copy `SKILL.md` and the entire `references/` directory into it.

Do not flatten the reference files into `.agent/skills/`.

## Recommended project-level routing rule

Add the following to the project instruction file already loaded by Antigravity (for example the project's existing `GEMINI.md` if that is what your workspace uses):

```text
### Mandatory Closure Revision Routing

When revising a high-risk Design or Implementation Plan after Closure Audit or Closure Confirmation findings, MUST invoke `.agent/skills/closure-revision/SKILL.md` before editing.

If `proof_graph_frozen=true`, revisions must stay inside the frozen proof graph/trust boundary/scope. Do not use incremental issue-by-issue editing. Build the full blocker ledger, Mutable/No-Touch sets, impact cones, one coherent patch, and author-side mini Closure Confirmation before returning the revision for review.

The revision agent may not self-approve the document and may not enable implementation, deployment, runtime, paper, live, execution, or trading authority.
```

## Verify triggering

Start a fresh Antigravity session and use a prompt such as:

```text
请使用 closure-revision skill，根据这份 Closure Confirmation 的 P0/P1 一次性修订当前 Design。proof graph 已冻结，不允许扩大 scope；修订前先生成 blocker ledger、Mutable/No-Touch set 和 impact cone，修订后执行 author-side mini Closure Confirmation。
```

The agent should explicitly load/use `closure-revision` before editing.
