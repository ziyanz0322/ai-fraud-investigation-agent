{{ config(materialized='view') }}

select
    transaction_id,
    account_id,
    transaction_time,
    amount,
    lower(trim(transaction_type)) as transaction_type,
    merchant_id,
    device_id,
    lower(trim(status)) as status,
    upper(trim(state)) as state,
    lower(trim(channel)) as channel
from {{ source('fraud_raw', 'transactions') }}
