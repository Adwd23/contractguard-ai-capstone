#!/usr/bin/env python3
"""Create and execute the capstone evidence notebook."""
from __future__ import annotations

from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "ContractGuard_Capstone_Executed.ipynb"
OUT.parent.mkdir(parents=True, exist_ok=True)

nb = nbf.v4.new_notebook()
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
}

cells = []
cells.append(
    nbf.v4.new_markdown_cell(
        """# ContractGuard AI — Executed Capstone Evidence

**Program:** SDAIA Academy — Advanced Agentic AI Systems Engineering  
**Cohort/session:** June 2026  
**Project:** Secure Multi-Agent Vendor Contract Audit Platform

This notebook executes and preserves evidence for all six rubric deliverables: real tool
use and named reasoning patterns, framework-managed graph orchestration, role-specialized
agents, security and observability, durable checkpoint/HITL/cloud artifacts, and
professional documentation.
"""
    )
)

cells.append(
    nbf.v4.new_code_cell(
        """from pathlib import Path
import json, os, subprocess, sys
import pandas as pd
from IPython.display import display, Markdown

PROJECT_ROOT = Path.cwd().resolve()
if PROJECT_ROOT.name == 'notebooks':
    PROJECT_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))
print('Project root:', PROJECT_ROOT)
print('Python:', sys.version.split()[0])
"""
    )
)

cells.append(
    nbf.v4.new_markdown_cell(
        """## 1. Execute the complete security, retry, HITL, restart, and output-validation demonstration

The runner contains hard assertions. Any missing rubric behavior causes the cell to fail.
It executes a real prompt-injection attack, a safe contract, a high-risk contract with a
simulated tool timeout, a Reflexion re-search loop, a durable human interrupt, a fresh
service restart, human approval, an output-schema revision loop, PII masking, and artifact
storage.
"""
    )
)

cells.append(
    nbf.v4.new_code_cell(
        """result = subprocess.run(
    [sys.executable, str(PROJECT_ROOT / 'scripts' / 'run_capstone_demo.py')],
    cwd=PROJECT_ROOT,
    text=True,
    capture_output=True,
    check=True,
)
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr)
"""
    )
)

cells.append(nbf.v4.new_markdown_cell("## 2. Rubric assertion summary"))
cells.append(
    nbf.v4.new_code_cell(
        """summary = json.loads((PROJECT_ROOT / 'evidence' / 'run_summary.json').read_text())
proof = pd.DataFrame(
    [{'requirement': key.replace('_', ' '), 'passed': value} for key, value in summary['proof'].items()]
)
display(proof)
assert proof['passed'].all()
print('All proof assertions:', bool(proof['passed'].all()))
"""
    )
)

cells.append(
    nbf.v4.new_markdown_cell(
        """## 3. Deliverable 1 — Agentic reasoning and real function tools

The Coordinator implements **Plan-and-Execute**. Every registered function call records a
concise **ReAct** triple: rationale/Thought, Action, and Observation. The Quality Reviewer
implements **Reflexion/self-critique**. The coordinator-to-specialist topology is
**Hierarchical Delegation**.
"""
    )
)
cells.append(
    nbf.v4.new_code_cell(
        """low = json.loads((PROJECT_ROOT / 'evidence' / '02_low_risk_completed.json').read_text())
tool_rows = []
observations = {o['call_id']: o for o in low['tool_observations']}
for call in low['tool_calls']:
    obs = observations[call['call_id']]
    tool_rows.append({
        'agent': call['agent'],
        'tool': call['tool_name'],
        'rationale': call['rationale'],
        'status': obs['status'],
        'latency_ms': round(obs['latency_ms'], 3),
        'observation': obs['summary'],
    })
display(pd.DataFrame(tool_rows))
print('Named reasoning patterns:', summary['reasoning_patterns'])
print('Shared state keys carried across steps:', len(low.keys()))
assert len(low['tool_calls']) >= 6
assert 'ReAct' in {d.get('pattern') for d in low['decision_trace']}
"""
    )
)

cells.append(
    nbf.v4.new_markdown_cell(
        """## 4. Deliverable 2 — Genuine graph orchestration with conditions and loops

The graph is built by the `transitions.Machine` framework. Conditions decide branches;
shared state is read and updated by node callbacks; three bounded cycles support tool
retry, Reflexion/re-search, and report revision.
"""
    )
)
cells.append(
    nbf.v4.new_code_cell(
        """graph = json.loads((PROJECT_ROOT / 'evidence' / 'graph_spec.json').read_text())
print('Framework:', graph['framework'])
print('Node count:', len(graph['nodes']))
print('Loops:')
for loop in graph['loops']:
    print(' -', loop)
edge_frame = pd.DataFrame(graph['edges'])[['trigger', 'source', 'dest', 'conditions', 'before']].fillna('')
display(edge_frame)
assert len(graph['nodes']) >= 10
assert any(edge['source'] == edge['dest'] for edge in graph['edges'])
assert any(edge.get('conditions') for edge in graph['edges'])
"""
    )
)

cells.append(
    nbf.v4.new_markdown_cell(
        """## 5. Failure paths — actual tool retry and Reflexion re-search

The first policy search deliberately raises a simulated timeout. The failed
`ToolObservation` is retained, the conditional self-loop fires, and the next attempt
succeeds. A separate quality critique routes back to research.
"""
    )
)
cells.append(
    nbf.v4.new_code_cell(
        """paused = json.loads((PROJECT_ROOT / 'evidence' / '03_high_risk_paused_for_human.json').read_text())
failed_tools = [o for o in paused['tool_observations'] if o['status'] == 'error']
print('Failed tool observations:', json.dumps(failed_tools, indent=2))
print('Policy retry count:', paused['policy_retry_count'])
print('Quality re-plan count:', paused['quality_retry_count'])
print('Research node visits:', paused['node_history'].count('researching'))
print('Node path:', ' -> '.join(paused['node_history']))
assert failed_tools
assert paused['policy_retry_count'] >= 1
assert paused['quality_retry_count'] >= 1
assert paused['node_history'].count('researching') >= 3
"""
    )
)

cells.append(
    nbf.v4.new_markdown_cell(
        """## 6. Deliverable 3 — Multi-agent role specialization and structured communication

These are separate agent objects/classes, not personas concatenated into one prompt.
Messages contain sender, recipient, message type, content, payload, and timestamp.
"""
    )
)
cells.append(
    nbf.v4.new_code_cell(
        """messages = pd.DataFrame(paused['agent_messages'])
agent_summary = messages.groupby('sender').agg(
    messages=('sender', 'size'),
    recipients=('recipient', lambda values: ', '.join(sorted(set(values))))
).reset_index()
display(agent_summary)
display(messages[['sender', 'recipient', 'message_type', 'content']].tail(12))
print('Coordination strategy:', summary['coordination_strategy'])
assert messages['sender'].nunique() >= 7
assert {'sender', 'recipient', 'message_type', 'payload'}.issubset(messages.columns)
"""
    )
)

cells.append(
    nbf.v4.new_markdown_cell(
        """## 7. Deliverable 4 — Security guardrails and structured observability

The malicious uploaded contract is inspected before the tool registry is reachable. The
output guardrail masks PII and validates a strict Pydantic schema. Monitoring is JSONL +
Prometheus, not print statements.
"""
    )
)
cells.append(
    nbf.v4.new_code_cell(
        """blocked = json.loads((PROJECT_ROOT / 'evidence' / '01_prompt_injection_blocked.json').read_text())
print('Attack terminal status:', blocked['status'])
print('Detected reason:', blocked['blocked_reason'])
print('Tool calls after block:', len(blocked['tool_calls']))
print('Blocked path:', ' -> '.join(blocked['node_history']))
assert blocked['status'] == 'blocked'
assert len(blocked['tool_calls']) == 0
"""
    )
)
cells.append(
    nbf.v4.new_code_cell(
        """log_path = PROJECT_ROOT / 'evidence' / 'execution_log.jsonl'
logs = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
log_frame = pd.DataFrame(logs)
print('Structured log events:', len(log_frame))
print('Event types:', sorted(log_frame['event'].dropna().unique()))
display(log_frame[['timestamp', 'event', 'thread_id', 'node', 'tool', 'latency_ms']].tail(15).fillna(''))

metrics_text = (PROJECT_ROOT / 'evidence' / 'metrics_before_restart.prom').read_text()
metric_names = sorted({line.split('{', 1)[0].split(' ', 1)[0] for line in metrics_text.splitlines() if line and not line.startswith('#')})
print('Prometheus metric series (sample):', metric_names[:20])
assert 'tool_call_failed' in set(log_frame['event'])
assert 'guardrail_blocked' in set(log_frame['event'])
assert 'human_interrupt' in set(log_frame['event'])
assert 'contractguard_tool_calls_total' in metrics_text
"""
    )
)

cells.append(
    nbf.v4.new_markdown_cell(
        """## 8. Deliverable 5 — Persistent checkpoint, real HITL pause/resume, and cloud artifact

A high-risk contract stops at `awaiting_approval`. The first service object is closed.
A fresh service object opens the same SQLite database, reloads the thread, applies a human
decision, and continues from the paused node.
"""
    )
)
cells.append(
    nbf.v4.new_code_cell(
        """loaded = json.loads((PROJECT_ROOT / 'evidence' / '04_checkpoint_loaded_after_restart.json').read_text())
final = json.loads((PROJECT_ROOT / 'evidence' / '05_high_risk_resumed_and_completed.json').read_text())
print('Node loaded after restart:', loaded['node'])
print('Interrupt payload:', json.dumps(loaded['state']['interrupt_payload'], indent=2))
print('Final status:', final['status'])
print('Human decision:', final['approval_status'], '-', final['approver'])
print('Output revision count:', final['report_revision_count'])
print('PII redactions:', final['pii_redactions'])
print('Artifact URI:', final['artifact_uri'])
assert loaded['node'] == 'awaiting_approval'
assert final['status'] == 'completed'
assert final['approval_status'] == 'approved'
assert final['report_revision_count'] >= 1
assert final['pii_redactions'] >= 3
"""
    )
)

cells.append(
    nbf.v4.new_code_cell(
        """cloud_files = ['Dockerfile', 'docker-compose.yml', 'deploy/prometheus.yml', 'src/contractguard/api.py']
cloud_evidence = []
for relative in cloud_files:
    path = PROJECT_ROOT / relative
    cloud_evidence.append({'artifact': relative, 'exists': path.exists(), 'bytes': path.stat().st_size if path.exists() else 0})
display(pd.DataFrame(cloud_evidence))
assert all(item['exists'] for item in cloud_evidence)
"""
    )
)

cells.append(nbf.v4.new_markdown_cell("## 9. Final masked compliance report"))
cells.append(
    nbf.v4.new_code_cell(
        """report_path = Path(final['artifact_uri'].removeprefix('file://'))
report_text = report_path.read_text()
print(report_text[:6000])
assert '[REDACTED_EMAIL]' in report_text
assert '[REDACTED_PHONE]' in report_text
assert '[REDACTED_NATIONAL_ID]' in report_text
assert 'nora.alqahtani@example.com' not in report_text
"""
    )
)

cells.append(
    nbf.v4.new_markdown_cell(
        """## 10. Automated tests

The test suite covers direct/indirect injection, PII masking, real tool search, low-risk
completion, graph retry, restart persistence, HITL resume, output revision, artifact
storage, and FastAPI endpoints.
"""
    )
)
cells.append(
    nbf.v4.new_code_cell(
        """tests = subprocess.run(
    [sys.executable, '-m', 'pytest', '-q'],
    cwd=PROJECT_ROOT,
    text=True,
    capture_output=True,
    check=True,
    env={**os.environ, 'PYTHONPATH': str(PROJECT_ROOT / 'src')},
)
print(tests.stdout)
(PROJECT_ROOT / 'evidence' / 'pytest_results.txt').write_text(tests.stdout + tests.stderr)
"""
    )
)

cells.append(
    nbf.v4.new_markdown_cell(
        """## 11. Documentation and submission completeness

- Professional README with setup, API keys, expected outputs, deployment, evidence index,
  training attribution, and SDAIA Academy link.
- Technical architecture using nodes, edges, state, agents, tools, conditions, loops, and
  checkpointers.
- Rubric traceability, security model, API reference, tests, `.gitignore`, Docker/Compose,
  CI workflow, and retained third-party license.
- Executed notebook and captured JSON/log/metric/report evidence.

The only external submission step is pushing this prepared Git repository to the
trainee's chosen GitHub repository.
"""
    )
)
cells.append(
    nbf.v4.new_code_cell(
        """required = [
    'README.md', '.gitignore', 'docs/architecture.md', 'docs/rubric_traceability.md',
    'docs/security.md', 'docs/api.md', 'Dockerfile', 'docker-compose.yml',
    '.github/workflows/ci.yml', 'THIRD_PARTY_NOTICES.md',
]
rows = [{'file': item, 'exists': (PROJECT_ROOT / item).exists()} for item in required]
display(pd.DataFrame(rows))
assert all(row['exists'] for row in rows)
print('Executed capstone notebook completed successfully.')
"""
    )
)

nb["cells"] = cells
raw_path = ROOT / "notebooks" / "ContractGuard_Capstone.ipynb"
nbf.write(nb, raw_path)

client = NotebookClient(nb, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}})
executed = client.execute()
nbf.write(executed, OUT)
print(OUT)
