import json
from openai import OpenAI

from database import create_connection
from tools import (
    get_account_profile,
    get_transaction_history,
    calculate_risk_signals,
    get_chargeback_history,
)

client = OpenAI()

tools = [
    {
        "type": "function",
        "name": "get_account_profile",
        "description": "Get the profile of an account by account_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "The account ID, for example ACC_003.",
                }
            },
            "required": ["account_id"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_transaction_history",
        "description": "Get the transaction history of an account by account_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "The account ID, for example ACC_003.",
                }
            },
            "required": ["account_id"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "calculate_risk_signals",
        "description": "Calculate deterministic risk signals for a transaction.",
        "parameters": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "The transaction ID, for example TXN_013.",
                }
            },
            "required": ["transaction_id"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_chargeback_history",
        "description": "Get the chargeback history of an account by account_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "The account ID, for example ACC_009.",
                }
            },
            "required": ["account_id"],
            "additionalProperties": False,
        },
    },
]


# agent loop, maximum step = 5
def run_investigation(transaction_id, max_steps=5):
    conn = create_connection("data/fraud.db")

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=f"""
        Investigate transaction {transaction_id}.

        Investigation procedure:
        1. Calculate risk signals first.
        2. Retrieve account profile and transaction history for context.
        3. Retrieve chargeback history only when relevant.
        4. Compare triggered signals with historical behavior and mitigating context.
        5. Do not infer fraud, customer intent, device ownership, or authorization without evidence.

        Return exactly these sections:

        1. Transaction
        2. Account Context
        3. Triggered Risk Signals
        4. Evidence Assessment
        - Supporting Evidence
        - Mitigating Context
        5. Transaction Pattern
        6. Uncertainties and Missing Information
        7. Human Review Recommendation

        Use only facts supported by tool outputs.
        Risk signals are indicators for review, not proof of fraud.
        """,
        tools=tools,
    )

    step = 0

    while step < max_steps:
        function_calls = [
            item for item in response.output if item.type == "function_call"
        ]

        if not function_calls:
            break

        tool_outputs = []

        for item in function_calls:
            arguments = json.loads(item.arguments)

            if item.name == "calculate_risk_signals":
                result = calculate_risk_signals(conn, arguments["transaction_id"])

            elif item.name == "get_account_profile":
                result = get_account_profile(conn, arguments["account_id"])

            elif item.name == "get_transaction_history":
                result = get_transaction_history(conn, arguments["account_id"])

            elif item.name == "get_chargeback_history":
                result = get_chargeback_history(conn, arguments["account_id"])

            else:
                result = {"error": f"Unknown tool: {item.name}"}

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result),
                }
            )

        response = client.responses.create(
            model="gpt-5.6-luna",
            previous_response_id=response.id,
            input=tool_outputs,
            tools=tools,
        )

        step += 1

    conn.close()

    return response.output_text


# test
if __name__ == "__main__":
    test_transactions = [
        # "TXN_001",
        "TXN_010",
        "TXN_004",
        # "TXN_017",
    ]

    for transaction_id in test_transactions:
        print("=" * 80)
        print(transaction_id)
        print(run_investigation(transaction_id))
