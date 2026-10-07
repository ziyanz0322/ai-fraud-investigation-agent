# AI Fraud Investigation Agent

An AI-assisted transaction investigation project that combines deterministic risk signals with contextual analysis.

The current V2 implementation uses Snowflake for storage and SQL execution, dbt for data models and risk calculations, and a Python agent to retrieve evidence and generate investigation reports.

The agent recommends monitoring or human review. It does not authorize payments or establish fraud.

## Architecture

```text
Synthetic CSV files
        ↓
Snowflake: FRAUD_DB.RAW
        ↓
dbt staging models
        ↓
dbt intermediate feature models
        ↓
FCT_TRANSACTION_RISK
        ↓
Python tools
        ↓
OpenAI-powered investigation agent
        ↓
Investigation report
```

Risk signals are calculated by SQL rules. The language model interprets retrieved evidence and explains the findings.

The original SQLite implementation remains available for regression testing and comparison.

## Dataset

| Table | Rows |
|---|---:|
| users | 500 |
| transactions | 9,000 |
| devices | 700 |
| chargebacks | 100 |

The synthetic dataset uses course card-transaction data as its primary behavioral reference for amounts, merchant repetition, and merchant-state distribution. Application data contributes only aggregate fraud-prevalence context.

Source names, SSNs, phone numbers, addresses, and card numbers are not included in the output schema.

Transaction activity spans January–June 2026. Transaction state represents merchant location, not customer location.

See `data/synthetic/README.md` for generation assumptions and distribution comparisons, if retained with the dataset.

## Risk Signals

| ID | Signal | Trigger condition |
|---|---|---|
| S01 | New account | Account age < 30 days |
| S02 | High-value transaction | Amount > $3,000 |
| S03 | High transaction velocity | ≥ 5 attempts in 30 minutes |
| S04 | New device | Device age < 24 hours |
| S05 | Dormant account reactivation | > 180 complete days since the previous transaction |
| S06 | Repeated counterparty | ≥ 4 attempts at the same merchant in 24 hours |
| S07 | Repeated failed payments | ≥ 3 failed or declined attempts in 30 minutes |
| S08 | Prior chargebacks | ≥ 2 chargebacks reported in the preceding 180 days |

Time-window rules:

- S03 and S06 include the target transaction and count all transaction statuses.
- S07 includes only failed or declined attempts through the target timestamp.
- S05 uses the most recent strictly earlier transaction, regardless of status. No earlier transaction means no dormant-account trigger.
- S08 includes the 180-day lower boundary and excludes reports at or after the target timestamp.
- Account and device ages are measured at transaction time, not at the current date.
- Historical tool queries exclude the target transaction and later records.

## Project Structure

```text
ai-fraud-investigation-agent/
├── data/
│   ├── fraud.db
│   ├── fraud_synthetic.db
│   └── synthetic/
│       ├── users.csv
│       ├── transactions.csv
│       ├── devices.csv
│       ├── chargebacks.csv
│       └── snowflake_risk_results.csv
├── src/
│   ├── agent.py
│   ├── snowflake_database.py
│   ├── snowflake_tools.py
│   ├── database.py
│   ├── tools.py
│   ├── risk_engine.py
│   ├── generate_data.py
│   ├── load_synthetic_data.py
│   └── compare_risk_results.py
├── tests/
│   └── test_synthetic_signals.py
├── fraud_analytics/
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── sources.yml
│   │   ├── staging/
│   │   │   ├── staging.yml
│   │   │   ├── stg_users.sql
│   │   │   ├── stg_transactions.sql
│   │   │   ├── stg_devices.sql
│   │   │   └── stg_chargebacks.sql
│   │   ├── intermediate/
│   │   │   ├── int_transaction_context.sql
│   │   │   ├── int_transaction_activity.sql
│   │   │   └── int_transaction_history.sql
│   │   └── marts/
│   │       └── fct_transaction_risk.sql
│   └── tests/
│       ├── assert_device_keys_unique.sql
│       ├── assert_transaction_device_exists.sql
│       └── assert_chargeback_account_matches.sql
└── README.md
```

The top-level `tests/` directory contains Python tests. The dbt project's `tests/` directory contains SQL data tests.

## Environment Setup

Validated environment:

- Python 3.12.2
- dbt Core 1.12.5
- dbt Snowflake adapter 1.12.1
- Snowflake Python Connector
- OpenAI Python SDK

For an existing installation, activate the working environment:

```bash
source ~/.venvs/fraud-dbt/bin/activate
```

For a new installation:

```bash
python -m venv ~/.venvs/fraud-dbt
source ~/.venvs/fraud-dbt/bin/activate

python -m pip install --upgrade pip
python -m pip install \
  "dbt-core==1.12.5" \
  "dbt-snowflake==1.12.1" \
  snowflake-connector-python \
  openai
```

Connector and OpenAI SDK versions are not yet pinned.

## Snowflake Configuration

The current development setup uses:

| Object | Name |
|---|---|
| Warehouse | FRAUD_WH |
| Database | FRAUD_DB |
| Source schema | RAW |
| dbt output schema | DBT_DEV |
| Development role | SYSADMIN |

`FRAUD_WH` uses X-Small compute, automatic resume, and a 60-second auto-suspend setting.

Before building models, create the four source tables and load their CSV files into `FRAUD_DB.RAW`. Building dbt models does not upload the CSVs.

The project uses encrypted key-pair authentication:

1. Generate an encrypted PKCS#8 RSA private key and its public key.
2. Register the public key on the Snowflake user.
3. Keep the private key outside the repository.
4. Configure dbt and the Python connector to use that key.

### dbt Connection Profile

Create `~/.dbt/profiles.yml`:

```yaml
fraud_analytics:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: YOUR_ORGANIZATION-YOUR_ACCOUNT
      user: YOUR_SNOWFLAKE_USER
      role: SYSADMIN
      database: FRAUD_DB
      warehouse: FRAUD_WH
      schema: DBT_DEV
      threads: 1
      private_key_path: /absolute/path/to/fraud_snowflake_v2.p8
      private_key_passphrase: "{{ env_var('DBT_ENV_SECRET_SNOWFLAKE_KEY_PASSPHRASE') }}"
```

Replace the account, user, and key path with your own values.

The `profile` setting in `fraud_analytics/dbt_project.yml` must be:

```yaml
profile: fraud_analytics
```

The Python connection module currently configures its connection separately. Update `src/snowflake_database.py` with the same account, user, role, warehouse, database, schema, and key path.

### Session Credentials

In a macOS zsh terminal, enter the private-key passphrase:

```bash
read -s "DBT_ENV_SECRET_SNOWFLAKE_KEY_PASSPHRASE?Private key passphrase: "
export DBT_ENV_SECRET_SNOWFLAKE_KEY_PASSPHRASE
```

For agent runs, also enter an OpenAI API key:

```bash
read -s "OPENAI_API_KEY?OpenAI API key: "
export OPENAI_API_KEY
```

These variables apply to the current terminal session and its child processes. Re-enter them in a new terminal.

Do not commit credentials or private keys.

## Build the Data Models

From the repository root:

```bash
cd fraud_analytics
dbt debug
dbt build --select +fct_transaction_risk
cd ..
```

The selection builds the risk model and its upstream dependencies, and runs associated data tests. It excludes unrelated scaffold example models.

The models are materialized as views. Source-data changes are reflected when the views are queried; SQL logic changes require another dbt build.

## Run an Investigation

From the repository root:

```bash
python -m src.agent
```

The current entry point uses the `test_transactions` list at the bottom of `src/agent.py`. Edit that list to choose transactions:

```python
test_transactions = ["TXN_010"]
```

The report contains:

1. Key Findings
2. Transaction Overview
3. Triggered Signals
4. Recommendation

An investigation queries Snowflake and calls the OpenAI API. It requires access to the model configured in `src/agent.py`.

## Controlled Demonstration Cases

| Transaction | Intended scenario | Expected signals |
|---|---|---|
| TXN_001 | Normal established customer | None |
| TXN_010 | New account and device, rapid attempts, preceding declines | S01, S02, S03, S04, S06, S07 |
| TXN_004 | High-value purchase consistent with prior premium-customer activity | S02 |
| TXN_017 | Repeated prior disputes with otherwise familiar purchasing behavior | S08 |

These are controlled synthetic scenarios, not independently verified fraud labels. Repeated disputes do not establish friendly fraud.

## Validation

### Python Regression Tests

From the repository root:

```bash
python -m unittest discover \
  -s tests \
  -p "test_synthetic_signals.py" \
  -v
```

Five tests cover:

- Expected signal combinations.
- Suspicious-sequence counts.
- Historical record cutoffs.
- Isolation from injected future transactions and chargebacks.
- The S03 threshold boundary at four versus five attempts.

These tests use SQLite and do not call OpenAI. Tests that inject or remove records operate on in-memory copies.

### dbt Data Tests

From the dbt project directory:

```bash
dbt test --select \
  stg_users \
  stg_transactions \
  stg_devices \
  stg_chargebacks
```

Nineteen configured tests check primary-key uniqueness, required identifiers, and account, transaction, and device relationships.

### V1–V2 Comparison

Export the following Snowflake query as a complete CSV to `data/synthetic/snowflake_risk_results.csv`:

```sql
SELECT
    TRANSACTION_ID AS "transaction_id",
    S01_NEW_ACCOUNT AS "S01",
    S02_HIGH_VALUE_TRANSACTION AS "S02",
    S03_HIGH_TRANSACTION_VELOCITY AS "S03",
    S04_NEW_DEVICE AS "S04",
    S05_DORMANT_ACCOUNT_REACTIVATION AS "S05",
    S06_REPEATED_COUNTERPARTY AS "S06",
    S07_REPEATED_FAILED_PAYMENTS AS "S07",
    S08_PRIOR_CHARGEBACKS AS "S08",
    TRIGGERED_SIGNAL_COUNT AS "triggered_signal_count"
FROM FRAUD_DB.DBT_DEV.FCT_TRANSACTION_RISK
ORDER BY TRANSACTION_ID;
```

Then run from the repository root:

```bash
python -m src.compare_risk_results
```

The completed comparison found matching results for all eight signal flags and the triggered-signal count across all 9,000 transactions.

This comparison validates agreement on the current dataset. It does not establish real-world fraud detection accuracy or complete boundary-condition coverage.

## V1 and V2 Responsibilities

- `agent.py` uses the Snowflake connection and tools.
- `snowflake_tools.py` retrieves evidence and formats SQL-derived signals for the agent.
- dbt calculates features and signal flags.
- `risk_engine.py`, `database.py`, and `tools.py` retain the SQLite implementation for comparison.
- `load_synthetic_data.py` supports the local test database.

The current agent path does not use the SQLite risk engine.

## Current Limitations

- The dataset is synthetic and contains deliberately constructed scenarios.
- The generated transaction period does not provide a positive example of more than 180 days of inactivity.
- Signal labels, operators, and thresholds are described in Python as well as implemented in dbt SQL. Changes must be synchronized.
- Account status and segment are snapshot attributes; historical changes are not recorded.
- Chargeback resolution history is unavailable, so historical tools omit resolution status.
- Device first-seen timestamps are assumed stable. Later corrections could change reconstructed historical features.
- Model-generated reports can misstate timing, comparison operators, or relationships. Report-level evaluation remains incomplete.
- The agent is a development prototype with limited retry, failure-recovery, and audit controls.
- SYSADMIN is used for development. A dedicated role with appropriate scoped permissions is needed before deployment.
- Authentication details and model selection are not yet managed through one unified configuration.
- Source-table creation and initial loading were performed manually; a fresh deployment still requires those setup steps.

## Next Improvements

- Add full feature-value comparisons and more boundary tests.
- Evaluate report accuracy independently from signal correctness.
- Centralize rule metadata and connection configuration.
- Add reliable connection cleanup, explicit step-limit handling, and error reporting.
- Introduce scoped Snowflake roles and reproducible setup scripts.
- Pin remaining dependencies and add automated validation.
