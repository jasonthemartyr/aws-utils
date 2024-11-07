#!/usr/bin/make -f
makefileDir := $(dir $(lastword $(MAKEFILE_LIST)))
CWD = $(shell cd $(makefileDir) && pwd)
SCRIPT_DIR := ./scripts

help: ## help using this makefile
	@ grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

pre-reqs:
	pip install -e .

run-pre-commit-all:
	pre-commit install-hooks
	pre-commit run --all-files

grafana-creds: ## retrieve grafana admin creds from AZ
	az keyvault secret show --name grafana-pass --vault-name grafana-pass --query value -o tsv

terraform-auto-apply: ## auto-apply terraform
	terraform init
	terraform refresh
	terraform apply -auto-approve

terraform-destroy: ## terraform destroy
	terraform destroy

.PHONY: docker-build-utils

docker-build-utils: ## Build utils container
	@cd $(SCRIPT_DIR) && ./build.sh

.PHONY: help pre-reqs grafana-creds terraform-auto-apply terraform-destroy