ifeq (,$(wildcard api/.env))
$(error .env file is missing at api/.env. Please create one based on api/.env.example)
endif

include api/.env

# --- Infrastructure ---

infrastructure-build:
	docker compose build

infrastructure-up:
	docker compose up --build -d

infrastructure-stop:
	docker compose stop

infrastructure-logs:
	docker compose logs -f

# --- Offline pipelines (等后面模块写好 tools/ 再启用) ---

# create-long-term-memory:
# 	docker run --rm --network=three-kingdoms-network --env-file api/.env -v ./api/data:/app/data three-kingdoms-agent-api uv run python -m tools.create_long_term_memory
