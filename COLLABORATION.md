# Collaboration

## Purpose

LocalFabric uses isolated agent worktrees so multiple AI providers can contribute without sharing a working branch or overwriting another agent's in-progress changes.

The integration workspace is:

```text
/Users/kwaight/scratch
```

The `main` branch is the integration branch. Agent implementation work must be performed in the provider's assigned worktree and proposed to `main` through a pull request.

## Agent Worktrees

| Provider | Workspace | Branch Prefix |
| --- | --- | --- |
| Codex | `~/agents/codex/LocalFabric` | `codex_` |
| Claude | `~/agents/claude/LocalFabric` | `claude_` |
| Copilot | `~/agents/copilot/LocalFabric` | `copilot_` |
| Gemini | `~/agents/gemini/LocalFabric` | `gemini_` |

These directories are Git worktrees from the same LocalFabric repository. Each worktree starts at a detached `main` baseline so a provider creates a purpose-specific branch when assigned work begins.

## Branch Naming

Every agent branch must use this format:

```text
<provider>_<type>_<short-description>
```

Allowed provider prefixes:

```text
codex_
claude_
copilot_
gemini_
```

Recommended task types:

| Type | Use For |
| --- | --- |
| `feature` | New user-facing or platform capability. |
| `bug` | Correctness fixes and regressions. |
| `docs` | Documentation-only work. |
| `refactor` | Structural improvements without intended behavior changes. |
| `test` | Test coverage and validation improvements. |
| `chore` | Tooling, dependency, and maintenance work. |
| `audit` | Architecture audits and classification remediation. |

Examples:

```text
claude_feature_research-router
copilot_bug_prompt-resolution
gemini_docs_service-catalog
codex_audit_driver-boundaries
```

## Starting Assigned Work

Before editing files, an agent should move to its worktree, refresh its baseline from the integration workspace, and create a new branch:

```bash
cd ~/agents/claude/LocalFabric
git switch --detach main
git switch -c claude_feature_short-description
```

Substitute the provider, task type, and short description for the assignment. Do not implement changes directly on `main`, and do not reuse an old branch for a new prompt.

If another branch is still checked out in that worktree, commit or otherwise preserve its work before switching branches.

## Change Ownership

- Work only in the provider workspace assigned to the active session.
- Keep each branch scoped to one prompt or a tightly related set of requested changes.
- Do not modify another agent's worktree or branch.
- Do not rewrite, reset, or discard another agent's pending work.
- Rebase or merge the current `main` branch into an active branch before proposing it when the integration baseline has changed materially.
- Run focused validation appropriate to the change before opening a pull request.

## Commit And Pull Request Workflow

An agent's task is not complete when local edits or a local commit are ready.
Unless the assigned prompt explicitly says not to publish, completion requires:

1. Validate the scoped change.
2. Commit the intended files on the agent branch.
3. Push that branch to `origin`.
4. Open a pull request targeting `main`.
5. Include a work summary and validation results in the pull request.

Use this publishing sequence after implementation and validation:

```bash
git status --short
git add <changed-paths>
git commit -m "<concise change summary>"
git push -u origin <provider>_<type>_<short-description>
```

Then open a pull request into `main`. Do not report the assigned task as
complete until the push and pull request have succeeded, or report the exact
blocking condition if publishing cannot be completed. Publishing a branch and
pull request requires the LocalFabric repository to have an `origin` remote
configured.

Every pull request must clearly include:

- **Purpose:** What outcome the change is intended to accomplish.
- **Assigned prompt:** The user instruction or task statement that initiated the work, quoted or faithfully summarized.
- **Work summary:** A concise account of files or areas changed and the delivered behavior or documentation.
- **Approach:** The implementation decisions and affected architectural classifications.
- **Validation:** Tests, audits, or inspections run and their outcomes.
- **Risks or follow-ups:** Known limitations, migration implications, or deferred work.

The repository pull request template supplies these fields and should not be removed from a submission.

## Integration Rules

- Pull requests target `main`.
- Review branch scope, classification ownership, validation, and prompt alignment before merging.
- Resolve overlapping changes through review rather than editing another provider's active worktree.
- After a pull request is merged, return the provider worktree to a clean detached `main` baseline before accepting its next assignment:

```bash
git switch --detach main
```

The integration owner may remove merged local branches once their history is preserved in `main` and any remote pull request record.

## Current Setup Note

The local worktree model is sufficient for isolated development and commits. A Git remote named `origin` must be configured before agents can push their branches and open pull requests against `main`.
