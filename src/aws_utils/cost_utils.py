import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta


AWS_REGION= 'us-east-1'

def get_accounts(ParentId):
    output =[]
    try:
        client = boto3.client('organizations', region_name=AWS_REGION)
        paginator = client.get_paginator('list_accounts_for_parent')
        for page in paginator.paginate(ParentId=ParentId):
            output.extend(page['Accounts'])
    except ClientError as e:
        print(e)
    except Exception as e:
        print(e)
    return output

def get_cur_params(start_date,
                   end_date,
                   account_id=None,
                   by_service=False):
    #https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_GetDimensionValues.html
    group_by = [
            {'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'}
        ]
    if by_service:
        group_by.append({'Type': 'DIMENSION', 'Key': 'SERVICE'})
    params = {
        'TimePeriod': {
            'Start': start_date,
            'End': end_date
        },
        'Granularity': 'MONTHLY',
        'Metrics': ['UnblendedCost'],
        'GroupBy': group_by
    }
    if account_id:
        params['Filter'] = {
            'Dimensions': {
                'Key': 'LINKED_ACCOUNT',
                'Values': [account_id]
            }
        }

    return params

def get_costs(client,
              start_date,
              end_date,
              account_id=None,
              by_service=False):

    params = get_cur_params(start_date=start_date,
                                            end_date=end_date,
                                            account_id=account_id,
                                            by_service=by_service)

    cost_data = []
    next_token = None
    while True:
        if next_token:
            params['NextPageToken'] = next_token
        response = client.get_cost_and_usage(**params)
        cost_data.extend(response['ResultsByTime'])
        next_token = response.get('NextPageToken')
        if not next_token:
            break
    return cost_data

def get_total(totals_list):
    output = 0.0
    for e in totals_list:
        try:
            groups = e.get('Groups')
            for group in groups:
                raw_total = float(group.get('Metrics').get('UnblendedCost').get('Amount'))
                output += raw_total
        except KeyError:
            print('key not found')
    return output

def fmt_total_cost_output(accounts_list,by_service=False):
    delete_output =dict()
    review_output = dict()
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        client = boto3.client('ce', region_name=AWS_REGION)

        for account in accounts_list:
            response =    get_costs(client, start_date, end_date, account_id=account, by_service=by_service)
            # print(response)
            total_cost = get_total(response)
            if total_cost < 1:
                delete_output['Account']= account
                delete_output['TotalCosts']= total_cost
                delete_output['RawOutput']= response
            else:
                review_output['Account']= account
                review_output['TotalCosts']= total_cost
                review_output['RawOutput']= response
    except ClientError as e:
        print(e)
    except Exception as e:
        print(e)
    return delete_output, review_output


# def main():
#     accounts = get_accounts(PARENT_ID)
#     x, y = fmt_total_cost_output(accounts)

#     print(json.dumps(x, indent=4))
# if __name__=="__main__":
#     main()