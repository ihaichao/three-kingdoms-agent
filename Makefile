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

create-long-term-memory:
	docker run --rm --network=three-kingdoms-network --env-file api/.env \
	 -v ./api/src/three_kingdoms:/app/three_kingdoms \
	 -v ./api/tools:/app/tools \
	 -v ./api/data:/app/data three-kingdoms-agent-api \
	 /app/.venv/bin/python -m tools.create_long_term_memory

generate-evaluation-dataset:
	docker run --rm --network=three-kingdoms-network --env-file api/.env \
	 -v ./api/src/three_kingdoms:/app/three_kingdoms \
	 -v ./api/tools:/app/tools \
	 -v ./api/data:/app/data three-kingdoms-agent-api \
	 /app/.venv/bin/python -m tools.generate_evaluation_dataset

upload-evaluation-dataset:
	docker run --rm --network=three-kingdoms-network --env-file api/.env \
	 -v ./api/src/three_kingdoms:/app/three_kingdoms \
	 -v ./api/tools:/app/tools \
	 -v ./api/data:/app/data three-kingdoms-agent-api \
	 /app/.venv/bin/python -m tools.upload_evaluation_dataset

# 小批量试跑：make evaluate-agent ARGS="--nb-samples 5"
evaluate-agent:
	docker run --rm --network=three-kingdoms-network --env-file api/.env \
	 -v ./api/src/three_kingdoms:/app/three_kingdoms \
	 -v ./api/tools:/app/tools \
	 -v ./api/data:/app/data three-kingdoms-agent-api \
	 /app/.venv/bin/python -m tools.evaluate_agent $(ARGS)

# 一次性诊断：对照两个判官模型。make compare-judges ARGS="-n 10"
compare-judges:
	docker run --rm --network=three-kingdoms-network --env-file api/.env \
	 -v ./api/src/three_kingdoms:/app/three_kingdoms \
	 -v ./api/tools:/app/tools \
	 -v ./api/data:/app/data three-kingdoms-agent-api \
	 /app/.venv/bin/python -m tools.compare_judges $(ARGS)

# 分层看某次实验。make analyze-experiment ARGS="--name three-kingdoms-xxxx"
analyze-experiment:
	docker run --rm --network=three-kingdoms-network --env-file api/.env \
	 -v ./api/src/three_kingdoms:/app/three_kingdoms \
	 -v ./api/tools:/app/tools \
	 -v ./api/data:/app/data three-kingdoms-agent-api \
	 /app/.venv/bin/python -m tools.analyze_experiment $(ARGS)

# 导出最差的样本供人肉归因。make dump-worst ARGS="--top 20"
dump-worst:
	docker run --rm --network=three-kingdoms-network --env-file api/.env \
	 -v ./api/src/three_kingdoms:/app/three_kingdoms \
	 -v ./api/tools:/app/tools \
	 -v ./api/data:/app/data three-kingdoms-agent-api \
	 /app/.venv/bin/python -m tools.dump_worst $(ARGS)

# 量指标本底：正对照+负对照，不跑 agent。make metric-floor ARGS="-n 40"
metric-floor:
	docker run --rm --network=three-kingdoms-network --env-file api/.env \
	 -v ./api/src/three_kingdoms:/app/three_kingdoms \
	 -v ./api/tools:/app/tools \
	 -v ./api/data:/app/data three-kingdoms-agent-api \
	 /app/.venv/bin/python -m tools.metric_floor $(ARGS)
