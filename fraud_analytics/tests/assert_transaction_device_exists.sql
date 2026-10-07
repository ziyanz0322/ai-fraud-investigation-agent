select t.*
from {{ ref('stg_transactions') }} t
where not exists (
    select 1
    from {{ ref('stg_devices') }} d
    where d.account_id = t.account_id
      and d.device_id = t.device_id
)
