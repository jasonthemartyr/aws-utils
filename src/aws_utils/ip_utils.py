import asyncio
import json
import aiodns
import boto3
import os
from functools import partial


def config_query(aggregator_name, queries):
    """
    Function for querying AWS Config.

    Args:
        aggregator_name: Name of config aggregator. Is set in load_config()
        queries: SQL like query for AWS Config. Is set in load_config()

    Returns:
        List of AWS Config query results
    """
    output = list()
    client = boto3.client('config', region_name='us-east-1')
    for q in queries.values():
        response = client.select_aggregate_resource_config(
            Expression=q,
            ConfigurationAggregatorName=aggregator_name
        )
        results = response["Results"]
        json_output = [json.loads(line) for line in results]
        output.extend(json_output)
    return output

async def async_config_query(aggregator_name, queries):
    """
    Async wrapper for config_query(). Required when using asyncio.

    Args:
        aggregator_name: Name of config aggregator is set in load_config()
        queries: SQL like query for AWS Config. Is set in load_config()

    Returns:
        List of formatted AWS resources and their public IP's
    """
    loop = asyncio.get_running_loop()
    func = partial(config_query, aggregator_name, queries) 
    results = await loop.run_in_executor(None, func)
    formatted_results = [json.dumps(item) for item in results]
    output = await fmt_output_async(formatted_results)
    return output

def search_for_ip(data, search_ip):
    """
    Function for finding an AWS resource with a specific public IP. 
    Should use output from async_config_query().

    Args:
        data: JSON output from async_config_query()
        search_ip: string of IP to search output of async_config_query()

    Returns:
        JSON object of matching resource
    """
    output = []
    for d in data:
        public_ip = d.get('publicIp')
        if public_ip and search_ip == public_ip:
            output.append(d)
        resolved_ips = d.get('resolvedIps',[])
        if resolved_ips and search_ip in resolved_ips:
            output.append(d)
    return output

# some examples: https://snyk.io/advisor/python/aiodns/example
# docs: https://github.com/aio-libs/aiodns
async def resolve_dns_async(hostname: str):
    """
    Async func to resolve FQDN's to IPv4

    Args:
        hostname: FQDN string

    Returns:
        List of resolved public IP addresses
    """
    try:
        resolver = aiodns.DNSResolver()
        results = await asyncio.gather(
            resolver.query(hostname, 'A'), #Just A records for now
            return_exceptions=True
        )
        ip_addresses = set()
        for result in results:
            if isinstance(result, Exception):
                continue
            ip_addresses.update(r.host for r in result) # type: ignore
        return list(ip_addresses)
    except Exception as e:
        return list(f"failed to resolve: {e}")


async def fmt_output_async(result_contents):
    """
    Formats output from AWS Config search and resolves FQDN's

    Args:
        result_contents: A list of JSON object output from AWS Config query

    Returns:
        List of JSON objects with public IP's
    """
    output = []
    dns_tasks = []
    templates = []

    for entry in result_contents:
        parse_entry = json.loads(entry)
        config = parse_entry.get('configuration')
        account_id = parse_entry.get('accountId')
        resource_id = parse_entry.get('resourceId')
        resource_name = parse_entry.get('resourceName')
        region = parse_entry.get('awsRegion')
        resource_type = parse_entry.get('resourceType')

        template_base = {
            'accountId': account_id,
            'resourceId': resource_id,
            'resourceName': resource_name,
            'region': region,
            'resourceType': resource_type
        }

        if 'AWS::EC2::NetworkInterface' in resource_type:
            template = template_base | {
                'publicIp': config.get('association', {}).get('publicIp') #returns empty dict if nested one doesnt exist (https://www.w3schools.com/python/ref_dictionary_get.asp)
            }
            output.append(template)
        elif 'AWS::EC2::EIP' in resource_type:
            template = template_base | {
                'publicIp': config.get('publicIp'),
                'networkInterfaceId': config.get('networkInterfaceId')
            }
            output.append(template)
        elif 'AWS::RDS::DBInstance' in resource_type:
            hostname = config.get('endpoint', {}).get('address')
            if hostname:
                dns_tasks.append(resolve_dns_async(hostname)) #add all fqdns that need to be resolved to a list
                templates.append((template_base, hostname, len(dns_tasks) - 1)) # set an index for "dns_tasks"
        elif 'AWS::ElasticLoadBalancingV2::LoadBalancer' in resource_type:
            hostname = config.get('dNSName')
            if hostname:
                dns_tasks.append(resolve_dns_async(hostname))
                templates.append((template_base, hostname, len(dns_tasks) - 1))
        elif "AWS::EKS::Cluster" in resource_type:
            endpoint = config.get('Endpoint')
            if endpoint:
                hostname = endpoint.replace("https://", "") #remove https:// from endpoint
                dns_tasks.append(resolve_dns_async(hostname))
                eks_config = {
                    'eksEndpointPrivateAccess': config.get('resourcesVpcConfig', {}).get('endpointPrivateAccess'),
                    'eksEndpointPublicAccess': config.get('resourcesVpcConfig', {}).get('endpointPublicAccess'),
                    'eksPublicAccessCidrs': config.get('resourcesVpcConfig', {}).get('publicAccessCidrs')
                }
                template_base.update(eks_config)
                templates.append((template_base, hostname, len(dns_tasks) - 1))
    if dns_tasks:
        dns_results = await asyncio.gather(*dns_tasks)
        for template_base, hostname, index in templates: #im referencing the index we set via "len((dns_tasks) - 1)"
            resolved_ips = dns_results[index]
            template = template_base | {
                'resolvedIps': resolved_ips,
                'fqdn': hostname
            }
            output.append(template)

    return output

def default_queries():
    """
    Default query values for EKS, EC2, EIP, ELB, and RDS for use with AWS Config.

    Returns:
        JSON objects with default IP queries
    """

    return {
    "EC2": """
        SELECT accountId, resourceId, resourceName, resourceType, 
               configuration.association.publicIp, groups.groupId, 
               groups.groupName, availabilityZone, awsRegion 
        WHERE resourceType = 'AWS::EC2::NetworkInterface' 
        AND configuration.association.publicIp > '0.0.0.0'
    """,

    "EIP": """
        SELECT accountId, resourceId, resourceName, resourceType,
               configuration.publicIp, configuration.networkInterfaceId,
               availabilityZone, awsRegion 
        WHERE resourceType = 'AWS::EC2::EIP'
    """,
    
    "ELB": """
        SELECT accountId, resourceId, resourceName, resourceType,
               configuration.dNSName, configuration.securityGroups,
               availabilityZone, awsRegion 
        WHERE resourceType = 'AWS::ElasticLoadBalancingV2::LoadBalancer'
        AND configuration.scheme = 'internet-facing'
    """,
    
    "DB": """
        SELECT accountId, resourceId, resourceName, resourceType,
               configuration.endpoint.address,
               configuration.vpcSecurityGroups.vpcSecurityGroupId,
               availabilityZone, awsRegion 
        WHERE resourceType = 'AWS::RDS::DBInstance'
        AND configuration.publiclyAccessible = true
    """,
    
    "EKS": """
        SELECT accountId, resourceId, resourceName, resourceType,
               awsRegion, configuration.ResourcesVpcConfig.EndpointPublicAccess,
               configuration.ResourcesVpcConfig.EndpointPrivateAccess,
               configuration.ResourcesVpcConfig.PublicAccessCidrs,
               configuration.Endpoint 
        WHERE resourceType = 'AWS::EKS::Cluster'
        AND configurationItemStatus != 'ResourceDeleted'
    """
    }

def load_config():
    """
    Loads default ENV VARs for specific actions and values.

    Returns:
        JSON objects with default values
    """

    agg_name = os.environ.get('AGGREGATOR_NAME')
    if agg_name is None:
        print("Please set AGGREGATOR_NAME environment variable")
        os._exit(1)

    config = {
        "PRINT":os.environ.get('PRINT', False),
        "SAVE_FILE":os.environ.get('SAVE_FILE', False),
        "SAVE_FILE_NAME": os.environ.get('SAVE_FILE_NAME', 'all_public_ips_FORMATTED.json'),
        "SEARCH_IP": os.environ.get('SEARCH_IP'),
        "AGGREGATOR_NAME": agg_name,
        "CONFIG_QUERIES": os.environ.get('CONFIG_QUERIES', default_queries()),
    }
    return config
