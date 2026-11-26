# One entry point for every check CI runs. See CONTRIBUTING.md.
.PHONY: install sync-spec check-spec generate check-drift lint test conformance build breaking e2e e2e-live e2e-published all

install:
	pnpm install --frozen-lockfile
	cd python && uv sync --frozen
	cd go && go mod download

# The public contract is owned by tembuilder-be (the backend mounts and tests
# exactly these operations); openapi/tembuilder.yaml is a byte-for-byte copy.
# BE_SPEC points at the backend's file: the sibling checkout by default, or
# the path CI checked tembuilder-be out to.
BE_SPEC ?= ../tembuilder-be/svr/service-svr/internal/publicapi/openapi.yaml

# Copies the backend contract and regenerates every SDK from it.
sync-spec:
	@test -f "$(BE_SPEC)" || (echo "Backend contract not found at $(BE_SPEC): set BE_SPEC." && exit 1)
	cp "$(BE_SPEC)" openapi/tembuilder.yaml
	$(MAKE) generate

# Fails when openapi/tembuilder.yaml was edited here or is behind the backend.
check-spec:
	@test -f "$(BE_SPEC)" || (echo "Backend contract not found at $(BE_SPEC): set BE_SPEC." && exit 1)
	@cmp -s "$(BE_SPEC)" openapi/tembuilder.yaml \
	  || (echo "openapi/tembuilder.yaml differs from $(BE_SPEC): run 'make sync-spec' (never edit the copy)." && exit 1)
	@echo "openapi/tembuilder.yaml matches the backend contract."

generate:
	./scripts/generate.sh

# Fails when generated code does not match the spec (hand edits or a spec
# change without regeneration).
check-drift: generate
	git diff --exit-code -- node/src/generated python/src/tembuilder/_generated go/internal/api \
	  || (echo "Generated code is out of date: run 'make generate' and commit the result." && exit 1)
	@test -z "$$(git status --porcelain -- node/src/generated python/src/tembuilder/_generated go/internal/api)" \
	  || (echo "Untracked generated files: run 'make generate' and commit the result." && exit 1)

lint:
	pnpm spec:lint
	cd node && pnpm typecheck
	cd python && uv run --frozen ruff check src tests examples ../e2e/python && uv run --frozen ruff format --check src tests examples ../e2e/python && uv run --frozen mypy --strict ../e2e/python/app.py && uv run --frozen mypy
	cd go && test -z "$$(gofmt -l .)" && go vet ./... && test -z "$$(gofmt -l ../e2e/go)"
	cd scripts/contractcheck && test -z "$$(gofmt -l .)" && go vet ./...

test:
	cd node && pnpm test
	cd python && uv run --frozen pytest --cov
	cd go && go test -race -coverprofile=coverage.out ./ && ../scripts/require-go-coverage.sh coverage.out

# contract/cases.json must agree with the spec (every operation covered, each
# request and response documented), then the Node SDK runs against a Prism mock.
conformance:
	cd scripts/contractcheck && go test ./... && go run . ../../openapi/tembuilder.yaml ../../contract/cases.json
	cd node && pnpm test:conformance

build:
	cd node && pnpm build && pnpm check:pack
	cd python && uv build
	cd go && go build ./...

# Compares the spec with the one on BASE (default origin/main).
breaking:
	./scripts/check-breaking.sh $(BASE)

# Installs each SDK into a brand-new app (packed tarball, built wheel, local
# module) and runs it like a user would. Offline checks always run; with
# TEMBUILDER_API_KEY, TEMBUILDER_BASE_URL and TEMBUILDER_SMOKE_TEMPLATE it also
# renders a real PDF. See e2e/run.sh.
e2e:
	./e2e/run.sh all local

# e2e against a running stack: loads the git-ignored .env.smoke and fails
# instead of skipping when the live flow cannot run.
e2e-live:
	@test -f .env.smoke || (echo ".env.smoke is missing: see CONTRIBUTING.md" && exit 1)
	set -a && . ./.env.smoke && set +a && REQUIRE_LIVE=1 ./e2e/run.sh all local

# Same apps against what npm, PyPI and the Go proxy serve. Versions are
# independent per SDK: NODE_VERSION, PYTHON_VERSION, GO_VERSION (default latest).
e2e-published:
	./e2e/run.sh node $(or $(NODE_VERSION),latest)
	./e2e/run.sh python $(or $(PYTHON_VERSION),latest)
	./e2e/run.sh go $(or $(GO_VERSION),latest)

all: check-spec lint check-drift test conformance build e2e
