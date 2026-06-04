PYTHON ?= python3
SCENARIO ?= s3_access_denied
RUNTIME ?= emr_ec2

.PHONY: help test hygiene deploy destroy run-scenario validate compare-oom smoke clean

help:
	@printf "Harrier EMR Demo Lab commands\n\n"
	@printf "  make test          Run static/unit tests\n"
	@printf "  make hygiene       Check for tracked local/generated files\n"
	@printf "  make deploy        Deploy disposable AWS demo infrastructure\n"
	@printf "  make destroy       Destroy disposable AWS demo infrastructure\n"
	@printf "  make run-scenario  Run SCENARIO=s3_access_denied RUNTIME=emr_ec2\n"
	@printf "  make validate      Validate SCENARIO through Harrier MCP\n"
	@printf "  make compare-oom   Generate DevOps Agent native-vs-Harrier OOM prompts\n"
	@printf "  make smoke         Run lightweight repository smoke check\n"
	@printf "  make clean         Remove local generated demo output\n"

test:
	$(PYTHON) -m pytest -q

hygiene:
	./scripts/check-repo-hygiene.sh

deploy:
	./scripts/deploy.sh

destroy:
	./scripts/destroy.sh

run-scenario:
	RUNTIME=$(RUNTIME) ./scripts/run_scenario.sh $(SCENARIO)

validate:
	RUNTIME=$(RUNTIME) ./scripts/validate_scenario.sh $(SCENARIO)

compare-oom:
	./scripts/run_devops_agent_oom_comparison.sh

smoke:
	find . -maxdepth 3 -type f | sort > /tmp/harrier-demo-lab-files.txt
	@printf "Repository smoke check wrote /tmp/harrier-demo-lab-files.txt\n"

clean:
	rm -rf .harrier-demo .harrier-local .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
