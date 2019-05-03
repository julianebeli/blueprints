import __init__
from api.requestor2 import API
import json
from pluck import pluck
      

cache_time = 60*60*24*30
api = API('prod', cache=cache_time)

account = 438
params = dict(methodname='get_sub_accounts_of_account',
              account_id=account,
              recursive=True)
api.add_method(**params)
api.do()
subaccounts = api.results

plucked = pluck(subaccounts, 'id', 'name', 'parent_account_id')
plucker = {}

for line in plucked:
    plucker[line[0]] = dict(name=line[1], parent=line[2])

with open('subaccount_data.py', 'w') as f:
    f.write(f'root_sub_account={account}\n')
    f.write(f'info={json.dumps(plucker, indent=4)}')

exit()
