.PHONY: backend-install backend-test frontend-install frontend-check frontend-typecheck verify docker-smoke proof backend-proof frontend-build bootstrap-backend bootstrap-frontend bootstrap truth-check full-proof clean-clone-proof release-proof-local nox test check-generated

backend-install:
	cd backend && python -m pip install -e ".[test]"

backend-test:
	cd backend && python -m compileall -q app
	cd backend && python -m pytest -q

frontend-install:
	cd frontend && npm ci

frontend-check:
	cd frontend && npm run lint
	cd frontend && npm run typecheck
	cd frontend && npm run build

frontend-build:
	cd frontend && npm run build

frontend-typecheck:
	cd frontend && npm run typecheck

bootstrap-backend:
	bash scripts/bootstrap_backend.sh

bootstrap-frontend:
	bash scripts/bootstrap_frontend.sh

bootstrap:
	bash scripts/bootstrap_all.sh

truth-check:
	python3 scripts/check_truth_claims.py --root .
	python3 scripts/validate_workflows.py
	python3 scripts/check_source_keys.py
	python3 scripts/check_statuses.py

check-generated:
	python3 scripts/check_no_generated_files.py --root .

nox:
	nox

full-proof:
	bash scripts/proof_full_stack.sh

release-proof-local:
	@if [ -x backend/.venv/bin/python ]; then \
		backend/.venv/bin/python scripts/release_gate.py; \
	else \
		python3 scripts/release_gate.py; \
	fi

clean-clone-proof:
	bash scripts/proof_clean_clone.sh

backend-proof:
	cd backend && python scripts/proof_backend_import.py

# test is an alias for backend-test
test: backend-test

# verify runs the full quality gate (no Docker)
verify: check-generated truth-check backend-install backend-test frontend-install frontend-check

docker-smoke:
	docker compose up -d --build
	curl -f http://localhost:8000/docs >/dev/null
	curl -f http://localhost:3000 >/dev/null
	docker compose down -v

proof:
	@mkdir -p artifacts/proof
	@TIMESTAMP=$$(date +%Y%m%d-%H%M%S); \
	echo "=== Backend tests $(TIMESTAMP) ===" | tee artifacts/proof/backend-$${TIMESTAMP}.log; \
	cd backend && python -m compileall -q app 2>&1 | tee -a ../artifacts/proof/backend-$${TIMESTAMP}.log; \
	python scripts/proof_backend_import.py 2>&1 | tee -a ../artifacts/proof/backend-$${TIMESTAMP}.log; \
	python -m pytest -q 2>&1 | tee -a ../artifacts/proof/backend-$${TIMESTAMP}.log; \
	echo "=== Frontend checks $(TIMESTAMP) ===" | tee ../artifacts/proof/frontend-$${TIMESTAMP}.log; \
	cd ../frontend && npm run lint 2>&1 | tee -a ../artifacts/proof/frontend-$${TIMESTAMP}.log; \
	npm run typecheck 2>&1 | tee -a ../artifacts/proof/frontend-$${TIMESTAMP}.log; \
	npm run build 2>&1 | tee -a ../artifacts/proof/frontend-$${TIMESTAMP}.log; \
	echo "Proof logs saved to artifacts/proof/backend-$${TIMESTAMP}.log and artifacts/proof/frontend-$${TIMESTAMP}.log"
