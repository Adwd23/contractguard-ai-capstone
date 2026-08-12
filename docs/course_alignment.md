# Course Material Alignment

The supplied course files were treated as design inputs rather than copied as isolated
lab scripts.

## Day 1 — Advanced engineering patterns

Applied concepts:

- ReAct tool traces (`Thought -> Action -> Observation`)
- Plan-and-Execute before action
- Reflexion/self-critique
- Hierarchical delegation
- short-term shared state and tool interfaces

The capstone combines all four named patterns instead of stopping at one sequential lab.

## Day 2 — Advanced frameworks and state graphs

Applied concepts:

- real framework-managed nodes and edges;
- conditional routing;
- cycles and bounded termination conditions;
- shared state written by nodes;
- retry/fallback behavior;
- checkpointing and human interruption.

The supplied autonomous-research lab used a useful research/evaluation loop. ContractGuard
generalizes that idea into three explicit loops and adds durable restart recovery.

## Day 3 — Multi-agent systems

Applied concepts:

- specialized Planner/Coordinator, Researcher, Analyst, Reviewer, Security, Writer, and
  Tool/Storage responsibilities;
- centralized coordination;
- structured messages and shared memory;
- direct specialist reporting rather than a single prompt role-playing several personas.

The report-agent lab inspired the role decomposition, but the capstone replaces the
linear sequence with a conditional state graph and production controls.

## Day 4 — Security and observability

Applied concepts:

- direct and indirect prompt-injection detection;
- demonstrated blocked attack;
- PII masking and strict output validation;
- tool permission boundaries;
- JSON logs, Prometheus metrics, latency/failure/retry events;
- penetration-style non-happy-path evidence.

## Day 5 — Production deployment

Applied concepts:

- prototype-to-production modularity;
- retry budgets and circuit breakers;
- durable SQLite checkpointing;
- human-in-the-loop approval;
- FastAPI;
- Docker and Docker Compose;
- MinIO/S3 simulated cloud storage;
- Prometheus monitoring;
- professional repository and documentation structure.
