# Submission Checklist

## Repository

- [x] Clear project description on the landing page
- [x] Professional README and English quick-start
- [x] Architecture and GitHub-renderable Mermaid graph using nodes, edges, state, agents, and tools
- [x] Setup, prerequisites, environment variables, execution, and expected outputs
- [x] `.gitignore` excludes secrets, keys, caches, and mutable checkpoint databases
- [x] Meaningful incremental Git history rather than one bulk upload
- [x] Training program and June 2026 session attribution
- [x] SDAIA Academy GitHub link
- [x] GitHub Actions for tests/evidence plus Docker-to-MinIO smoke validation
- [x] Automated pre-publication checker
- [ ] Replace the placeholder local Git author/email with the trainee's chosen public identity
- [ ] Create the trainee-owned empty GitHub repository and push `main`

## Rubric execution evidence

- [x] Real schema-validated function calls with ReAct records
- [x] Offline MCP-style schema router plus optional provider-native function calling adapters
- [x] Plan-and-Execute and short-term shared state
- [x] Real state-machine framework with nodes, edges, conditions, and bounded cycles
- [x] Ten distinct agents, typed messages, and explicit centralized coordination
- [x] Runtime per-agent tool permissions
- [x] Prompt-injection attack blocked with zero tools
- [x] Strict function schemas, path boundary, safe thread IDs, and API-key option
- [x] Pre-model context minimization and PII masking
- [x] Output secret/schema guardrail and PII masking
- [x] JSONL logs and Prometheus metrics
- [x] Tool failure/retry and Reflexion/re-search loops executed
- [x] Persistent SQLite checkpoint survives restart
- [x] Human approval interrupt pauses and resumes
- [x] FastAPI, hardened Docker/Compose, MinIO, and Prometheus artifacts
- [x] Executed notebook, tests, reports, logs, metrics, and JSON snapshots

## Final pre-push commands

```bash
python scripts/prepublish_check.py
git status
git log --oneline --decorate
git remote add origin <YOUR_EMPTY_GITHUB_REPOSITORY>
git push -u origin main
```

After the push, confirm that:

1. `README.md` renders on the repository landing page.
2. `notebooks/ContractGuard_Capstone_Executed.ipynb` displays saved outputs.
3. Both GitHub Actions jobs pass.
4. The Actions artifacts include the evidence bundle and MinIO smoke result.
5. No `.env`, API key, mutable SQLite database, or real contract data is tracked.
