# Course Material Alignment

The supplied course files were used as architectural inputs rather than copied as isolated
lab scripts.

## Day 1 — Advanced engineering patterns

Applied concepts:

- ReAct records (`Thought -> Action -> Observation`);
- Plan-and-Execute before action;
- Reflexion/self-critique;
- Hierarchical delegation;
- short-term shared state;
- MCP-style tool descriptions and optional model-native function calling.

The capstone combines all four named patterns instead of stopping at one sequential lab.

## Day 2 — Advanced frameworks and state graphs

Applied concepts:

- a real LangGraph `StateGraph`;
- executable nodes and `add_edge` / `add_conditional_edges` routing;
- conditional routing;
- cycles with bounded termination conditions;
- shared state read and updated by nodes;
- retry/fallback behavior;
- durable `SqliteSaver` checkpointing plus `interrupt()` / `Command(resume=...)`.

The autonomous-research lab's research/evaluation cycle is generalized into three loops
and durable restart recovery.

## Day 3 — Multi-agent systems

Applied concepts:

- specialized Coordinator, Researcher, Analyst, Reviewer, Security, Writer, Guardian, and
  Storage responsibilities;
- centralized/hierarchical coordination;
- typed messages and shared memory;
- direct specialist reporting rather than one prompt role-playing many personas;
- runtime least-privilege tool permissions.

The report-agent lab inspired role decomposition, while ContractGuard replaces the linear
sequence with a conditional state graph and production controls.

## Day 4 — Security and observability

Applied concepts:

- direct and indirect prompt-injection detection;
- a demonstrated blocked attack;
- strict function schemas and tool permission boundaries;
- contract-path and identifier validation;
- PII masking before optional external model use and before final output;
- strict output validation and secret filtering;
- JSON logs, Prometheus metrics, latency/failure/retry/model events;
- penetration-style negative tests.

## Day 5 — Production deployment

Applied concepts:

- prototype-to-production modularity;
- retry budgets and circuit breakers;
- durable SQLite checkpointing;
- human-in-the-loop approval;
- FastAPI and optional API-key authentication;
- non-root Docker and hardened Docker Compose;
- MinIO/S3 simulated cloud storage;
- Prometheus monitoring;
- automated CI, MinIO smoke testing, and pre-publication verification;
- professional repository and documentation structure.
