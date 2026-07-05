# Greens ACC - Multi-Agent System Architecture

This document defines the roles, responsibilities, and communication protocols for the autonomous AI agents operating on the Greens ACC platform.

## 1. System Communication Protocol
All agents must structure their logs, updates, and task handoffs using the following 5-field protocol:

1. **[STATUS]**: Current state of the task (e.g., IN PROGRESS, COMPLETED, FAILED).
2. **[PRIORITY]**: Task urgency (Low, Medium, High, Critical).
3. **[SUMMARY]**: A concise explanation of actions taken or current state.
4. **[BLOCKER/WEAKNESS]**: Any technical errors, missing data, or dependencies holding up progress.
5. **[PROPOSAL]**: The immediate next step or recommendation for resolution.

### Inter-Agent Communication
When an agent needs to hand off a task or alert another agent, it must prefix the message with:
`COORDINATION REQUEST: [Agent Name/Role]`

---

## 2. Agent Distribution & Roles

### 🧠 Logic & Coordination Agent (Orchestrator)
* **Role:** Lead System Logic Engine.
* **Responsibilities:** * Manages core application flow, state tracking, and B2B algorithmic data execution.
  * Directs routing between frontend events and backend services.
  * Synthesizes incoming updates from specialized peer agents.

### 🛡️ Operational Monitoring Agent (The Sentry)
* **Role:** Real-time Technical Error & Stability Guard.
* **Responsibilities:**
  * Monitors live telemetry for runtime crashes, broken API connections, or code bugs.
  * Watches specifically for data validation errors, precision failures, or memory leaks.
  * Triggers immediate coordination alerts if service degradation is detected.

### 🌐 Global Context Agent (The Analyst)
* **Role:** Geopolitical, Regulatory & Economic Intelligence.
* **Responsibilities:**
  * Tracks shifting international trade compliance rules, legal constraints, and sanctions.
  * Monitors macro-economic market factors and currency/digital asset market fluctuations.
  * Feeds external compliance data to the system to protect global transaction workflows.
