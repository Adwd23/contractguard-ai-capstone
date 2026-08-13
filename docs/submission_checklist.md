# Submission Checklist — ContractGuard AI v1.3.1

- [ ] Repository is public and owned by **Adwd23**.
- [ ] Repository name is `contractguard-ai-capstone`.
- [ ] GitHub About description is populated with the text in `docs/github_publication.md`.
- [ ] README is visible from the repository landing page.
- [ ] Root `EVALUATION.json` parses as valid JSON and reports `all_static_checks_pass: true`.
- [ ] `StateGraph(AuditState)` is present in executable workflow code.
- [ ] At least five `add_conditional_edges(...)` calls are present in `workflow.py`.
- [ ] A bounded graph cycle is present and demonstrated in runtime evidence.
- [ ] `InputGuardrail.enforce()` blocks the real attack before any tool call.
- [ ] `OutputGuardrail.enforce()` masks PII and validates the report before storage.
- [ ] Ten independent specialist agent classes are visible under `src/contractguard/agents/`.
- [ ] Structured `AgentMessage` communication is captured in shared state.
- [ ] `interrupt(...)` and `Command(resume=...)` are both implemented and demonstrated.
- [ ] SQLite checkpoint state survives a service restart.
- [ ] `uvicorn` is imported and used by the actual API launcher.
- [ ] `ipykernel.kernelspec.make_ipkernel_cmd()` is used by the notebook evidence builder.
- [ ] Dockerfile and Docker Compose artifacts are present.
- [ ] `evidence/07_minio_docker_smoke.json` proves successful MinIO/S3 persistence.
- [ ] JSONL logs and Prometheus metrics are committed as runtime evidence.
- [ ] `evidence/runtime_grader_probe.json` reports `all_runtime_checks_pass: true`.
- [ ] Executed notebook has captured output and no unexecuted code cells.
- [ ] `evidence/pytest_results.txt` shows the regression suite passed.
- [ ] No `.env`, API key, runtime checkpoint DB, or generated cache is committed.
- [ ] Incremental, meaningful Git history is present.
- [ ] Training program, June 2026 cohort/session, and SDAIA Academy GitHub link are documented.
- [ ] `python scripts/prepublish_check.py --skip-runtime` passes using committed evidence, or `python scripts/prepublish_check.py` passes after a fresh full run.

No GitHub Actions workflow is required for the submission. All rubric proof is available directly from source and committed runtime evidence.
