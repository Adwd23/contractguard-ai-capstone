# GitHub Publication Instructions

Target repository:

```text
https://github.com/Adwd23/contractguard-ai-capstone
```

## Required About description

Open the repository page, choose the gear icon in the **About** panel, and set:

```text
Secure LangGraph multi-agent system for vendor contract auditing, compliance analysis, guardrails, human approval, and production monitoring.
```

Set the repository to Public if direct trainer access is required.

## Push the prepared Git history

```bash
git remote add origin https://github.com/Adwd23/contractguard-ai-capstone.git
git push -u origin main
```

If `origin` already exists:

```bash
git remote set-url origin https://github.com/Adwd23/contractguard-ai-capstone.git
git push -u origin main
```

## After the first push

1. Open **Actions**.
2. Wait for `test-and-evidence` and `docker-minio-smoke` to pass.
3. Confirm the evidence-refresh commit appears on `main` if generated artifacts changed.
4. Confirm `notebooks/ContractGuard_Capstone_Executed.ipynb` has execution counts and captured output.
5. Open `evidence/prepublish_report.json` and confirm `ready_to_publish` is `true`.
6. Submit the repository URL only after the checks are green.
