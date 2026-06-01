PYTHON ?= python3
SCENARIO ?= s3_access_denied
RUNTIME ?= emr_ec2

.PHONY: help test deploy destroy run-scenario validate smoke clean

help:
	@printf "Harrier EMR Demo Lab commands\n\n"
	@printf "  make test          Run static/unit tests\n"
	@printf "  make deploy        Deploy disposable AWS demo infrastructure\n"
	@printf "  make destroy       Destroy disposable AWS demo infrastructure\n"
	@printf "  make run-scenario  Run SCENARIO=s3_access_denied RUNTIME=emr_ec2\n"
	@printf "  make validate      Validate SCENARIO through Harrier MCP\n"
	@printf "  make smoke         Run lightweight repository smoke check\n"
	@printf "  make clean         Remove local generated demo output\n"

test:
	$(PYTHON) -m pytest -q

deploy:
	./scripts/deploy.sh

destroy:
	./scripts/destroy.sh

run-scenario:
	RUNTIME=$(RUNTIME) ./scripts/run_scenario.sh $(SCENARIO)

validate:
	RUNTIME=$(RUNTIME) ./scripts/validate_scenario.sh $(SCENARIO)

smoke:
	find . -maxdepth 3 -type f | sort > /tmp/harrier-demo-lab-files.txt
	@printf "Repository smoke check wrote /tmp/harrier-demo-lab-files.txt\n"

clean:
	rm -rf .harrier-demo .harrier-local .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

