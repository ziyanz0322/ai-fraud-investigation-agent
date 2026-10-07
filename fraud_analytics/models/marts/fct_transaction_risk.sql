{{ config(materialized='view') }}

with features as (
    select
        c.*,
        a.transaction_count_last_30m,
        a.same_merchant_transaction_count_last_24h,
        a.failed_transaction_count_last_30m,
        h.previous_transaction_time,
        h.days_since_previous_transaction,
        h.chargeback_count_last_180d

    from {{ ref('int_transaction_context') }} c

    left join {{ ref('int_transaction_activity') }} a
        on c.transaction_id = a.transaction_id

    left join {{ ref('int_transaction_history') }} h
        on c.transaction_id = h.transaction_id
),

signals as (
    select
        *,

        case
            when account_age_days < 0 then false
            else account_age_days < 30
        end as s01_new_account,

        amount > 3000
            as s02_high_value_transaction,

        transaction_count_last_30m >= 5
            as s03_high_transaction_velocity,

        device_age_hours < 24
            as s04_new_device,

        coalesce(days_since_previous_transaction > 180, false)
            as s05_dormant_account_reactivation,

        same_merchant_transaction_count_last_24h >= 4
            as s06_repeated_counterparty,

        failed_transaction_count_last_30m >= 3
            as s07_repeated_failed_payments,

        chargeback_count_last_180d >= 2
            as s08_prior_chargebacks

    from features
)

select
    *,

    cast(s01_new_account as integer)
    + cast(s02_high_value_transaction as integer)
    + cast(s03_high_transaction_velocity as integer)
    + cast(s04_new_device as integer)
    + cast(s05_dormant_account_reactivation as integer)
    + cast(s06_repeated_counterparty as integer)
    + cast(s07_repeated_failed_payments as integer)
    + cast(s08_prior_chargebacks as integer)
        as triggered_signal_count

from signals
