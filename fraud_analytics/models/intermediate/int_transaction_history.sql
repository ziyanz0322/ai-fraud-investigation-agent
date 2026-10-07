{{ config(materialized='view') }}

with previous_transactions as (
    select
        t.transaction_id,
        max(h.transaction_time) as previous_transaction_time

    from {{ ref('stg_transactions') }} t

    left join {{ ref('stg_transactions') }} h
        on t.account_id = h.account_id
        and h.transaction_time < t.transaction_time

    group by t.transaction_id
),

prior_chargebacks as (
    select
        t.transaction_id,
        count(c.chargeback_id) as chargeback_count_last_180d

    from {{ ref('stg_transactions') }} t

    left join {{ ref('stg_chargebacks') }} c
        on t.account_id = c.account_id
        and c.chargeback_date >= dateadd(
            'day', -180, t.transaction_time
        )
        and c.chargeback_date < t.transaction_time

    group by t.transaction_id
)

select
    t.transaction_id,
    p.previous_transaction_time,

    floor(
        datediff(
            'second',
            p.previous_transaction_time,
            t.transaction_time
        ) / 86400.0
    ) as days_since_previous_transaction,

    c.chargeback_count_last_180d

from {{ ref('stg_transactions') }} t

left join previous_transactions p
    on t.transaction_id = p.transaction_id

left join prior_chargebacks c
    on t.transaction_id = c.transaction_id
