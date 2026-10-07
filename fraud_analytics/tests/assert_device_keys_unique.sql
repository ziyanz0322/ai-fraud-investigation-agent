select
    account_id,
    device_id,
    count(*) as row_count
from {{ ref('stg_devices') }}
group by account_id, device_id
having count(*) > 1
