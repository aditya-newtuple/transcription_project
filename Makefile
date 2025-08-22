GIT_ROOT := $(shell git rev-parse --show-toplevel)
DEV_GIT_BRANCH := main
PROD_GIT_BRANCH := prod
PROJECT_NAME := $(shell basename $(GIT_ROOT) | tr '[:upper:]' '[:lower:]')

.PHONY: help \
	docs deploy-docs \
	pre-commit \
	init-alembic add-alembic-revision upgrade-alembic-revision downgrade-alembic-revision show-alembic-history show-alembic-current stamp-alembic-revision \
	create-network stop-services start-services stop-dev-application start-dev-application stop-prod-application start-prod-application clean-docker-cache \
	sync-uv-dependencies install-dependencies \
	tests \
	run-application-backend run-application-frontend

# ANSI color codes
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RESET  := \033[0m

help:
	@echo "${YELLOW}Available commands:${RESET}"
	@echo "  ${GREEN}docs                      ${RESET}: Generate local documentation in the /docs folder using MkDocs."
	@echo "  ${GREEN}deploy-docs               ${RESET}: Deploy the generated documentation to GitHub Pages."
	@echo "  ${GREEN}pre-commit                ${RESET}: Install and run pre-commit hooks for code quality checks."
	@echo "  ${GREEN}init-alembic              ${RESET}: Initialize Alembic for database migrations."
	@echo "  ${GREEN}add-alembic-revision      ${RESET}: Auto-generate an Alembic revision for database migrations."
	@echo "  ${GREEN}upgrade-alembic-revision  ${RESET}: Upgrade the database schema to the latest Alembic revision."
	@echo "  ${GREEN}downgrade-alembic-revision${RESET}: Downgrade the database schema by one revision."
	@echo "  ${GREEN}show-alembic-history      ${RESET}: Show the Alembic migration history."
	@echo "  ${GREEN}show-alembic-current      ${RESET}: Show the current Alembic revision."
	@echo "  ${GREEN}stamp-alembic-revision    ${RESET}: Stamp the database with the latest Alembic revision."
	@echo "  ${GREEN}create-network            ${RESET}: Create the required Docker networks."
	@echo "  ${GREEN}create-volume             ${RESET}: Create the required Docker volumes."
	@echo "  ${GREEN}stop-services             ${RESET}: Stop all running Docker services as defined in docker-compose-services.yml."
	@echo "  ${GREEN}start-services            ${RESET}: Stop then start all services with rebuild in detached mode."
	@echo "  ${GREEN}stop-dev-application      ${RESET}: Shut down the development instance of the application."
	@echo "  ${GREEN}start-dev-application     ${RESET}: Start the development instance of the application with rebuild."
	@echo "  ${GREEN}stop-prod-application     ${RESET}: Stop the production instance of the application."
	@echo "  ${GREEN}start-prod-application    ${RESET}: Start the production instance of the application with rebuild."
	@echo "  ${GREEN}clean-docker-cache        ${RESET}: Prune Docker build cache and builder cache."
	@echo "  ${GREEN}sync-uv-dependencies      ${RESET}: Synchronize the uv package dependencies by updating requirements."
	@echo "  ${GREEN}install-dependencies      ${RESET}: Install Python dependencies from requirements.txt for local run."
	@echo "  ${GREEN}tests                     ${RESET}: Run tests using pytest."
	@echo "  ${GREEN}run-application-backend   ${RESET}: Run the application backend locally."
	@echo "  ${GREEN}run-application-frontend  ${RESET}: Run the application frontend locally."

# --- Alembic Database Migrations ---
init-alembic:
	@echo "Initializing Alembic for database migrations..."
	cd ${GIT_ROOT}/bot_service/src/backend && alembic init alembic

add-alembic-revision:
	@echo "Auto-generating an Alembic revision for database migrations..."
	@echo "Enter alembic commit message: "; \
	read ALEMBIC_COMMIT_MSG; \
	echo "Your alembic commit message is: $$ALEMBIC_COMMIT_MSG"; \
	cd ${GIT_ROOT}/bot_service/src/backend && alembic revision --autogenerate -m "$$ALEMBIC_COMMIT_MSG"

upgrade-alembic-revision:
	@echo "Upgrading the database schema to the latest Alembic revision..."
	cd ${GIT_ROOT}/bot_service/src/backend && alembic upgrade head

downgrade-alembic-revision:
	@echo "Downgrading the database schema by one revision..."
	cd ${GIT_ROOT}/bot_service/src/backend && alembic downgrade -1

show-alembic-history:
	@echo "Showing the Alembic migration history..."
	cd ${GIT_ROOT}/bot_service/src/backend && alembic history --verbose

show-alembic-current:
	@echo "Showing the current Alembic revision..."
	cd ${GIT_ROOT}/bot_service/src/backend && alembic current

stamp-alembic-revision:
	@echo "Stamping the database with the latest Alembic revision..."
	cd ${GIT_ROOT}/bot_service/src/backend && alembic stamp head

# --- Docker Management ---
clean-docker-cache:
	@echo "Pruning Docker build cache and builder cache..."
	docker buildx prune -a -f
	docker builder prune -a -f

create-volume:
	@echo "Creating Docker volumes..."
	docker volume create postgres_data || true
	docker volume create pgadmin_data || true
	docker volume create redis_data || true

create-network:
	@echo "Creating Docker networks..."
	docker network create -d bridge shared_network || true
	docker network create -d bridge llm-network || true

stop-services:
	@echo "Stopping Docker services..."
	docker compose -f docker-compose-services.yml down

start-services: stop-services
	@echo "Starting Docker services..."
	if [ "$$(docker volume ls -q)" ]; then \
		docker compose -f docker-compose-services.yml up -d --build; \
	else \
		$(MAKE) create-volume; \
		docker compose -f docker-compose-services.yml up -d --build; \
	fi

stop-dev-application:
	@echo "Shutting down the development instance of the application..."
	docker compose --project-name ${PROJECT_NAME}_${DEV_GIT_BRANCH} -f docker-compose-main.yml down

start-dev-application: stop-dev-application
	@echo "Starting the development instance of the application..."
	docker compose --project-name ${PROJECT_NAME}_${DEV_GIT_BRANCH} -f docker-compose-main.yml up -d --build

stop-prod-application:
	@echo "Stopping the production instance of the application..."
	docker compose --project-name ${PROJECT_NAME}_${PROD_GIT_BRANCH} -f docker-compose-prod.yml down

start-prod-application: stop-prod-application
	@echo "Starting the production instance of the application..."
	docker compose --project-name ${PROJECT_NAME}_${PROD_GIT_BRANCH} -f docker-compose-prod.yml up -d --build

# --- Documentation ---
docs:
	@echo "Generating local documentation..."
	pip3 install mkdocs-material --quiet
	python3 -m mkdocs serve -a localhost:8001

deploy-docs:
	@echo "Deploying documentation to GitHub Pages..."
	pip3 install mkdocs-material --quiet
	python3 -m mkdocs gh-deploy --force

# --- Code Quality & Dependencies ---
pre-commit:
	@echo "Running pre-commit hooks..."
	cd ${GIT_ROOT} && pre-commit run --all-files

sync-uv-dependencies:
	@echo "Synchronizing uv package dependencies..."
	pip3 install uv --quiet
	cd ${GIT_ROOT}/bot_service/src/backend && uv pip compile requirements.txt -o requirements.in

install-dependencies:
	@echo "Installing Python dependencies from requirements.txt..."
	pip3 install -r ${GIT_ROOT}/bot_service/src/backend/requirements.txt -U
	@echo "Installing Node.js dependencies for the frontend..."
	cd ${GIT_ROOT}/bot_service/src/frontend && npm install --legacy-peer-deps

# --- Local Development & Testing ---
run-application-backend:
	@echo "Running the application backend locally..."
	cd ${GIT_ROOT}/bot_service/src/backend && python3 main.py -e ./etc/.env

run-application-frontend:
	@echo "Running the application frontend locally..."
	cd ${GIT_ROOT}/bot_service/src/frontend && npm run dev

tests:
	@echo "Running tests..."
	pytest ${GIT_ROOT}/bot_service/src/backend/tests -v