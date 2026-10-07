{{ config(materialized='view') }}

select
    chargeback_id,
    transaction_id,
    account_id,
    chargeback_date,
    lower(trim(reason_code)) as reason_code,
    amount,
    lower(trim(status)) as status
from {{ source('fraud_raw', 'chargebacks') }}
