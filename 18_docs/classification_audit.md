# Classification Boundary Audit

## Purpose

The classification audit identifies files that contain responsibilities belonging
to multiple numeric buckets. It produces planning records only. Remediation
agents consume those records and make scoped changes after reviewing evidence.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `01_schemas/audit.classification_finding.schema.yaml` | Contract for one JSONL finding |
| `17_scripts/audit_classifications.py` | Deterministic crawler and finding generator |
| `14_data/runs/classification_audit/findings.jsonl` | Open decomposition work queue |
| `14_data/runs/classification_audit/summary.json` | Scan statistics and rule counts |

## Run The Audit

From the repo root:

```bash
python3 17_scripts/audit_classifications.py
```

The crawler reads source, configuration, workflow, and documentation files
under active numeric-prefixed buckets. It excludes persistent run data and
`19_archive/`, whose contents are retained for historical reference only. Re-running it
refreshes current evidence while stable `finding_id` values preserve any
existing `status` value for findings that remain present.

## Initial Rule Families

| Rule | Boundary Being Enforced |
| --- | --- |
| `executable_provider_wrapper_in_prompt_bucket` | `12_prompts` stores templates, not API clients |
| `provider_execution_in_tool_bucket` | `07_tasks` exposes reusable capabilities, not provider invocation |
| `provider_health_probe_in_adapter` | `03_adapters` translates/presents input and output, while harnesses query providers |
| `mcp_tool_combines_provider_prompt_and_fetch_execution` | `11_mcp` exposes tools without becoming the implementation layer |
| `workflow_executes_prompt_bucket_as_scripts` | `06_workflows` orchestrates named prompt tasks without running prompt assets as programs |
| `workflow_owns_persistent_file_io` | `08_drivers` owns persistent read/write operations |
| `external_document_tool_execution_in_core` | `02_core` remains domain-neutral |
| `router_depends_on_mcp_exposure_layer` | `05_router` dispatches internal capabilities rather than importing exposure adapters |
| `configured_model_missing_from_registry` | `13_models` is authoritative for model availability (one YAML per model) |
| `duplicate_docker_service_lifecycle_paths` | Runtime and harness layers do not duplicate lifecycle execution |

## Remediation Agent Pipeline

Use the JSONL as an ordered queue, processing high severity records first.

1. **Triage agent** reads a record, verifies evidence still exists, and marks it
   accepted or dismissed in its working plan.
2. **Contract agent** defines or updates the internal contract before behavior is
   moved, especially when prompts, harnesses, or drivers are involved.
3. **Decomposition agent** extracts functionality into the listed destination
   buckets while preserving existing entry points through delegation.
4. **Verification agent** runs focused tests and the classification audit again.
   A resolved record must disappear or be explicitly documented as intentional.

One remediation change should target one finding or one tightly coupled finding
cluster. For example, the Ollama vision prompt wrappers and the vision tool
client form a single cluster because they define competing contracts for the
same task.

## Finding Interpretation

Each JSONL line includes:

- `file`: absolute source path under review.
- `violation`: rule, severity, evidence lines, and audit confidence.
- `decomposition_classes`: destination ownership suggestions with naming guidance.
- `related_files`: files that should be inspected during the same remediation.
- `remediation_guidance`: sequencing guidance for the next agent.
- `status`: planning lifecycle field; generated findings begin as `open`.

The audit intentionally favors false negatives over broad guesses. Add a new
rule only when its ownership boundary can be stated clearly and its evidence can
be detected without interpreting arbitrary business logic.

Ephemeral workflow-runtime IPC files created with `tempfile.mkstemp` are
execution plumbing rather than persistent data targets and are excluded from
the persistent-file-I/O finding rule.
