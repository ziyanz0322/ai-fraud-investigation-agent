{{ config(materialized='view') }}

select
    t.transaction_id,
    t.account_id,
    t.transaction_time,
    t.amount,
    t.transaction_type,
    t.merchant_id,
    t.device_id,
    t.status,
    t.state as merchant_state,
    t.channel,

    u.created_at as account_created_at,
    u.state as account_state,
    u.customer_segment,

    d.first_seen_at as device_first_seen_at,
    d.device_type,

    floor(
        datediff('second', u.created_at, t.transaction_time)
        / 86400.0
    ) as account_age_days,

    datediff('second', d.first_seen_at, t.transaction_time)
        / 3600.0 as device_age_hours

from {{ ref('stg_transactions') }} t

left join {{ ref('stg_users') }} u
    on t.account_id = u.account_id

left join {{ ref('stg_devices') }} d
    on t.account_id = d.account_id
    and t.device_id = d.device_id
