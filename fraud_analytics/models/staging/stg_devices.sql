{{ config(materialized='view') }}

select
    account_id,
    device_id,
    first_seen_at,
    last_seen_at,
    lower(trim(device_type)) as device_type,
    trusted
from {{ source('fraud_raw', 'devices') }}
