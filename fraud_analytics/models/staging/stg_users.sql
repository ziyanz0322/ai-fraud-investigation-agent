{{ config(materialized='view') }}

select
    account_id,
    created_at,
    upper(trim(state)) as state,
    lower(trim(customer_segment)) as customer_segment,
    lower(trim(status)) as status
from {{ source('fraud_raw', 'users') }}
