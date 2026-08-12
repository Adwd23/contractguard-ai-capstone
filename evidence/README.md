# Runtime Evidence

This directory is regenerated from the current v1.3 source by:

```bash
python scripts/run_capstone_demo.py
python scripts/build_executed_notebook.py
python scripts/prepublish_check.py --skip-runtime
```

The first GitHub Actions run performs those commands with the actual LangGraph dependency installed, validates every JSON artifact, and refreshes the committed evidence on `main` when required.

Do not hand-edit scored evidence. A valid submission should contain the generated `run_summary.json`, `graph_spec.json`, attack/retry/HITL scenario files, structured logs, Prometheus metrics, test results, pre-publication report, and executed notebook from the same commit.

`grader_manifest.json` is a strict JSON source-evidence index intended for automated graders.
