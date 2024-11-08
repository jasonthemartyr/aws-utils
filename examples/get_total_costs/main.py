import json
from aws_utils.ip_utils import get_accounts, fmt_total_cost_output

PARENT_ID=''

def main():
    accounts = get_accounts(PARENT_ID)
    x, y = fmt_total_cost_output(accounts)

    print(json.dumps(x, indent=4))
if __name__=="__main__":
    main()