# GitHub Publication Instructions

Target repository:

```text
https://github.com/Adwd23/contractguard-ai-capstone
```

## Required repository metadata

The repository must be public if direct trainer access is required.

The GitHub **About** description must be:

```text
Secure LangGraph multi-agent system for vendor contract auditing, compliance analysis, guardrails, human approval, and production monitoring.
```

This is repository metadata, not README content, so verify it on the repository landing page before submission.

## Final verification

The submission is intentionally independent of GitHub Actions. The implementation and captured runtime evidence are committed directly in the repository.

Run either the full fresh validation:

```bash
python scripts/prepublish_check.py
```

or validate the already-captured evidence:

```bash
python scripts/prepublish_check.py --skip-runtime
```

Also verify:

1. `EVALUATION.json` parses and reports `all_static_checks_pass: true`.
2. `evidence/runtime_grader_probe.json` parses and reports `all_runtime_checks_pass: true`.
3. `evidence/07_minio_docker_smoke.json` reports `storage_backend: "minio-s3"` and `verified_via_s3_sdk: true`.
4. `notebooks/ContractGuard_Capstone_Executed.ipynb` contains execution counts and captured output.
5. The README displays the project description, setup steps, expected outputs, architecture, training attribution, cohort/session, and SDAIA Academy link.

Submit the public repository URL only after those checks pass.
