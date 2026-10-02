# AI Fraud Investigation Agent

A portfolio project that combines deterministic fraud analytics with an LLM-based investigation agent.

The core design principle is:

> SQL/Python calculates facts and risk signals.
> The LLM retrieves evidence, compares supporting and mitigating context, and produces a grounded investigation summary.
> Final decisions remain human-in-the-loop.

---

## V1 Architecture

```text
Synthetic Data
    ↓
SQLite
    ↓
Python Risk Engine
    ↓
Deterministic Risk Signals
    ↓
Agent Tools
    ↓
LLM Investigation Agent
    ↓
Evidence-Based Investigation Summary
    ↓
Human Review
```

### Core Tables

- `users`
- `transactions`
- `devices`
- `chargebacks`

### Agent Tools

- `get_account_profile(account_id)`
- `get_transaction_history(account_id)`
- `calculate_risk_signals(transaction_id)`
- `get_chargeback_history(account_id)`

---

## Risk Signals

| Signal | V1 Threshold |
|---|---|
| New account | Account age < 30 days |
| High-value transaction | Amount > $3,000 |
| High transaction velocity | ≥ 5 transactions in the 30-minute window ending at the transaction |
| New device | Device age < 24 hours |
| Dormant-account reactivation | > 180 days since the previous transaction |
| Repeated counterparty | ≥ 4 transactions with the same merchant in the 24-hour window ending at the transaction |
| Repeated failed payments | ≥ 3 failed/declined transactions in the 30-minute window ending at the transaction |
| Prior chargebacks | ≥ 2 chargebacks in the prior 180 days |

These V1 thresholds are intentionally simple and interpretable. They are used as investigation signals rather than fraud conclusions.

Later versions will introduce customer-level behavioral baselines and segment-specific thresholds.

---

## Agent Investigation Flow

```text
Transaction ID
    ↓
Calculate risk signals
    ↓
Retrieve account profile
    ↓
Retrieve transaction history
    ↓
Retrieve chargeback history when relevant
    ↓
Compare supporting and mitigating context
    ↓
Generate grounded investigation summary
    ↓
Human review recommendation
```

The agent does not independently determine whether a transaction is fraudulent.

---

## Demo Case 1 — TXN_010

A newly created account made six approved purchases with the same merchant and device within approximately 14 minutes, ending with a $4,800 transaction.

### Triggered Signals

- New account
- High-value transaction
- High transaction velocity
- New device
- Repeated counterparty

### Key Evidence

- Account age: 14 days
- Transaction amount: $4,800
- 6 transactions in the 30-minute window ending at the transaction
- Device age: approximately 0.33 hours
- 6 transactions with the same merchant in the 24-hour window ending at the transaction
- Transaction amounts increased from $200 to $4,800

### Mitigating Context

- All six transactions were approved
- No repeated failed-payment signal
- No prior chargeback signal
- Transaction state matched the account state

The agent recommends human review based on the combination of multiple concurrent risk indicators, while explicitly avoiding a fraud conclusion.

---

## Demo Case 2 — TXN_004

A premium customer made a $5,800 transaction.

Only one risk signal triggered:

- High-value transaction

### Mitigating Context

- Established account
- Established device
- No elevated transaction velocity
- No repeated failed payments
- No recent chargebacks
- Previous transaction was also high-value at $4,200
- Both transactions used the same device, channel, and state

This case demonstrates a key design principle:

> High value ≠ fraud.

The current V1 uses a simple global high-value threshold. A later version will introduce customer-level behavioral baselines to better distinguish unusual activity from normal high-value customer behavior.

---

## Current Status

### V1 Completed

- SQLite data model
- Synthetic behavioral test cases
- 8 deterministic risk signals
- Python risk engine
- 4 investigation tools
- Multi-step LLM tool-calling loop
- Grounded investigation summaries
- Human-review recommendations

### Next Steps

```text
Snowflake
→ dbt transformations and data quality
→ fraud feature tables
→ AWS S3 ingestion
→ orchestration
→ agent/rule evaluation
→ human-in-the-loop workflow
```

---

## Design Principles

- Deterministic analytics calculate facts and risk signals.
- The LLM does not calculate fraud features from raw data.
- Risk signals are not treated as proof of fraud.
- The agent retrieves evidence through controlled tools.
- Supporting and mitigating evidence are both considered.
- Missing evidence and uncertainty are explicitly documented.
- Final high-impact decisions remain human-in-the-loop.
