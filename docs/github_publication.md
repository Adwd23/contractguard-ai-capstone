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

The **Full Repo v1.3.1** archive already has this target configured as `origin`. After extracting it, verify and push:

```bash
git remote -v
git push -u origin main
```

If you extracted a copy without the remote configuration, set it explicitly:

```bash
git remote add origin https://github.com/Adwd23/contractguard-ai-capstone.git
git push -u origin main
```

In GitHub Desktop, use **File → Add Local Repository**, choose the extracted `contractguard-ai` folder, verify the History tab, and then use **Push origin / Publish branch** while signed in as **Adwd23**.

## After the first push

1. Open **Actions**.
2. Wait for `test-and-evidence` and `docker-minio-smoke` to pass.
3. Confirm the evidence-refresh commit appears on `main` if generated artifacts changed.
4. Confirm `notebooks/ContractGuard_Capstone_Executed.ipynb` has execution counts and captured output.
5. Open `evidence/prepublish_report.json` and confirm `ready_to_publish` is `true`.
6. Submit the repository URL only after the checks are green.

If GitHub CLI is installed and authenticated as `Adwd23`, the About description can also be set after the repository exists remotely:

```bash
gh repo edit Adwd23/contractguard-ai-capstone \
  --description "Secure LangGraph multi-agent system for vendor contract auditing, compliance analysis, guardrails, human approval, and production monitoring."
```

This metadata is not controlled by `README.md`; verify it directly on the GitHub repository landing page.
