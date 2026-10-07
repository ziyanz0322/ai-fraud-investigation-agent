{{ config(materialized='view') }}

select
    t.transaction_id,

    sum(
        case
            when h.transaction_time >= dateadd(
                'minute', -30, t.transaction_time
            )
            then 1 else 0
        end
    ) as transaction_count_last_30m,

    sum(
        case
            when h.merchant_id = t.merchant_id
            then 1 else 0
        end
    ) as same_merchant_transaction_count_last_24h,

    sum(
        case
            when h.transaction_time >= dateadd(
                'minute', -30, t.transaction_time
            )
            and h.status in ('failed', 'declined')
            then 1 else 0
        end
    ) as failed_transaction_count_last_30m

from {{ ref('stg_transactions') }} t

left join {{ ref('stg_transactions') }} h
    on t.account_id = h.account_id
    and h.transaction_time >= dateadd(
        'hour', -24, t.transaction_time
    )
    and h.transaction_time <= t.transaction_time

group by t.transaction_id
