select c.*
from {{ ref('stg_chargebacks') }} c
where not exists (
    select 1
    from {{ ref('stg_transactions') }} t
    where t.transaction_id = c.transaction_id
      and t.account_id = c.account_id
)
