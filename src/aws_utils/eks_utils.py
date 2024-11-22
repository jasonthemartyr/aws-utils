from urllib import response
import boto3
import kubernetes
import yaml
import tempfile
import os



class EKSClusterManager:
    def __init__(self, cluster_name: str, region: str, role_to_assume: str):
        self.cluster_name = cluster_name
        self.region = region
        self.role_to_assume = role_to_assume
        self.boto_session = self.create_boto_session()
        self.eks_client = self.boto_session.client('eks')
        self.cluster_desc = self.describe_cluster_config()

    def assume_eks_role(self):
        sts_client = boto3.client('sts', self.region)
        assumed_role = sts_client.assume_role(
            RoleArn=self.role_to_assume,
            RoleSessionName=f"EksAssumeRole-{self.cluster_name}"
        )
        return assumed_role['Credentials']

    def create_boto_session(self):
        credentials = self.assume_eks_role()
        return boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=self.region
        )

    def describe_cluster_config(self):
        cluster_desc = self.eks_client.describe_cluster(name=self.cluster_name)['cluster']
        return cluster_desc

    def match_access_entries(self):
        entries = self.eks_client.list_access_entries(clusterName=self.cluster_name)['accessEntries']
        #simple match for now. TODO: add validation via describe_access_entry() method for 'kubernetesGroups', 'scope', etc
        return any(entry in self.role_to_assume for entry in entries)

    def update_access_entry(self):
        if not self.match_access_entries():
            # you have to create, update, then associate the access policy with EKS cluster
            self.eks_client.create_access_entry(clusterName=self.cluster_name, principalArn=self.role_to_assume,kubernetesGroups=['masters'])
            # response = client.list_access_policies() #may need to list and get admin policy before applying
            # print(response)
            # policy = client.associate_access_policy(
            #                                             clusterName=cluster_name,
            #                                             principalArn='arn:aws:iam::XXX:role/XXX',
            #                                             policyArn='arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy',
            #                                             accessScope={
            #                                                 'type': 'cluster'
            #                                             }
            #                                             )
            # print(policy)
            self.eks_client.update_access_entry(clusterName=self.cluster_name,principalArn=self.role_to_assume)
            policy = self.eks_client.associate_access_policy(clusterName=self.cluster_name,
                                                             principalArn=self.role_to_assume,
                                                             policyArn='arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy',
                                                            accessScope={'type': 'cluster'})

            return policy['ResponseMetadata']['HTTPStatusCode'] #returns 200 if successful
        return 304 #not modified http response code

    def get_kube_config(self):
        credentials = self.assume_eks_role()
        resp = self.update_access_entry()
        if resp in [200, 304]:
            kubeconfig = {
                'apiVersion': 'v1',
                'kind': 'Config',
                'clusters': [{
                    'cluster': {
                        'server': self.cluster_desc['endpoint'],
                        'certificate-authority-data': self.cluster_desc['certificateAuthority']['data']
                    },
                    'name': self.cluster_name
                }],
                'contexts': [{
                    'context': {
                        'cluster': self.cluster_name,
                        'user': 'aws',
                    },
                    'name': self.cluster_name
                }],
                'current-context': self.cluster_name,
                'preferences': {},
                'users': [{
                    'name': 'aws',
                    'user': {
                        'exec': {
                            'apiVersion': 'client.authentication.k8s.io/v1beta1',
                            'command': 'aws',
                            'args': [
                                '--region',
                                self.region,
                                'eks',
                                'get-token',
                                '--cluster-name',
                                self.cluster_name
                            ],
                            'env': [
                                {
                                    'name': 'AWS_ACCESS_KEY_ID',
                                    'value': credentials['AccessKeyId']
                                },
                                {
                                    'name': 'AWS_SECRET_ACCESS_KEY',
                                    'value': credentials['SecretAccessKey']
                                },
                                {
                                    'name': 'AWS_SESSION_TOKEN',
                                    'value': credentials['SessionToken']
                                }
                            ]
                        }
                    }
                }]
            }
            config_file = tempfile.NamedTemporaryFile(delete=False, mode='wb')
            yaml.dump(kubeconfig, config_file, encoding='utf-8')
            config_file.close()
            return config_file.name

def main():
    AWS_REGION= 'us-east-1'
    eks = EKSClusterManager('YOUR_CLUSTER_NAME',region = AWS_REGION, role_to_assume='arn:aws:iam::AWS_ACCOUNT_NUMBER:role/ROLE_NAME' )
    kubeconfig = eks.get_kube_config()
    kubernetes.config.load_kube_config(kubeconfig)

    api = kubernetes.client.CoreV1Api()
    pods = api.list_namespaced_pod(namespace='default')
    print(pods)
    print(f'Found {len(pods.items)} pods')
    os.remove(kubeconfig)
if __name__=="__main__":
    main()
