# aws-utils - WIP

A repo to store common utils used in AWS.

## Contents

```bash
src
└── aws_utils
    ├── __init__.py
    ├── __pycache__
    ├── cost_utils.py <-- cost utilities to ID costs by service in a specific OU
    ├── eks_utils.py <-- A class used to programmatically access the K8s control plane (think for daemonset/pod enforcement, etc)
    └── ip_utils.py <-- AWS config query to ID public IP's for various resources (EC2, EKS, RDS, etc)
```
