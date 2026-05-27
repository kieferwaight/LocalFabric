# Classification Remediation Workflow

## Objective
Resolve the findings in `14_data/runs/classification_audit/findings.jsonl`
through small dependency-aware remediation clusters. Each cluster is reviewed
by rerunning the audit and focused tests before proceeding to the next one.

## Agent Loop
1. **Select** the next open high-severity finding and any records that depend on
   the same implementation boundary.
2. **Verify** that each cited evidence line is still present and decide whether
   the record needs decomposition or dismissal.
3. **Implement** only the ownership moves needed for that cluster, preserving
   supported APIs with delegation when appropriate.
4. **Validate** with focused tests, compilation, and a refreshed audit queue.
5. **Record** the audit delta and any rule/process adjustment in
   `14_data/runs/classification_audit/remediation_log.jsonl`.

## Planned Order
| Cluster | Scope | Reason For Order |
| --- | --- | --- |
| `vision-prompts` | Vision tool client, executable prompt wrappers, shell legacy flows, model registration, CLI preflight | Establishes the canonical provider/prompt boundary used by later work |
| `mcp-research` | MCP local tools and router imports | Moves internal capability implementation below the exposure layer |
| `embeddings` | Embedding provider call and cache persistence | Reuses the established harness pattern |
| `artifact-io` | Workflow file writes and PDF-specific core execution | Establishes driver ownership for persistent/document operations |
| `service-runtime` | Docker lifecycle duplication | Consolidates runtime behavior after application paths are stable |

## Completion Criteria
- Supported behavior has an owning bucket consistent with `REPO_STRUCTURE.md`.
- Legacy-only executable paths are archived or removed from active execution.
- The audit emits no open actionable findings.
- Focused tests and structural compilation pass after each cluster.

## Completed Run
The initial remediation run resolved all `19` generated findings in five
dependency-aware clusters:
| Cluster | Finding Delta | Process Learning |
| --- | ---: | --- |
| `vision-prompts` | `19` to `7` | Archive historical executables before consolidating the supported path |
| `mcp-research` | `7` to `5` | Keep MCP thin and avoid introducing optional config dependencies at import time |
| `embeddings` | `5` to `4` | Provider invocation and persistent cache state require separate owners |
| `artifact-io` | `4` to `1` | Workflow nodes should delegate persistent artifact writes to drivers |
| `service-runtime` | `1` to `0` | The runtime resolves bindings; the harness executes lifecycle operations |