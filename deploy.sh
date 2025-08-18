#!/bin/bash

# Define colors as variables
GREEN="\033[1;32m"
CYAN="\033[1;36m"
RED="\033[1;31m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
MAGENTA="\033[1;35m"
BOLD="\033[1m"
UNDERLINE="\033[4m"
# Define no color
NC="\033[0m" # No Color

fetch_latest_changes(){
    echo -e "${CYAN}${BOLD}Configuring git user...${NC}"
    git config user.email "deploy@deploy.com"
    git config user.name "deploy"

    # fetch latest changes on current working branch
    branch=$(git rev-parse --abbrev-ref HEAD)
    echo -e "${GREEN}${BOLD}Fetching & pulling latest code on branch ${UNDERLINE}$1${NC}"
    git pull origin $1
}

deploy_ci(){
    project_name=$(basename $(git rev-parse --show-toplevel) | tr '[:upper:]' '[:lower:]')
    echo -e "${YELLOW}${BOLD}Stop existing services on compose project ${UNDERLINE}$project_name"_"$1${NC}"
    docker compose --project-name $project_name"_"$1 -f docker-compose-$1.yml down

    echo -e "${BLUE}${BOLD}Cleaning cache build for older than 10 days for ${UNDERLINE}$1${NC}"
    docker builder prune -f --filter until=240h
    docker buildx prune -f --filter until=240h
    docker image prune -a -f

    echo -e "${MAGENTA}${BOLD}Rebuilding services for ${UNDERLINE}$project_name"_"$1${NC} ${MAGENTA}${BOLD} using branch ${UNDERLINE}$1${NC}"
    docker compose --project-name $project_name"_"$1 -f docker-compose-$1.yml up --build -d
    
    echo -e "${GREEN}${BOLD}✓ Deployment complete!${NC}"
}

"$@"
