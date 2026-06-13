#!/bin/bash

# CI/CD utilities for Claude commands
# Common CI/CD workflow generation and management functions

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Source dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/json-utils.sh" 2>/dev/null || true
source "$SCRIPT_DIR/file-utils.sh" 2>/dev/null || true

# Generate GitHub Actions workflow
generate_github_workflow() {
    local workflow_name="$1"
    local workflow_file="$2"
    local triggers=("${@:3}")

    local workflow_dir=".github/workflows"
    mkdir -p "$workflow_dir"

    local full_path="$workflow_dir/$workflow_file"

    cat > "$full_path" <<EOF
name: $workflow_name

on:
EOF

    # Add triggers
    for trigger in "${triggers[@]}"; do
        case "$trigger" in
            "push")
                cat >> "$full_path" <<EOF
  push:
    branches: [ main, develop ]
EOF
                ;;
            "pull_request")
                cat >> "$full_path" <<EOF
  pull_request:
    branches: [ main ]
EOF
                ;;
            "schedule")
                cat >> "$full_path" <<EOF
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
EOF
                ;;
            "workflow_dispatch")
                cat >> "$full_path" <<EOF
  workflow_dispatch:
EOF
                ;;
        esac
    done

    cat >> "$full_path" <<EOF

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

EOF

    echo "$full_path"
}

# Add Node.js setup to workflow
add_nodejs_setup() {
    local workflow_file="$1"
    local node_version="${2:-18}"
    local package_manager="${3:-pnpm}"

    cat >> "$workflow_file" <<EOF
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '$node_version'
        cache: '$package_manager'

    - name: Install dependencies
      run: $package_manager install

EOF
}

# Add Python setup to workflow
add_python_setup() {
    local workflow_file="$1"
    local python_version="${2:-3.11}"
    local use_uv="${3:-true}"

    cat >> "$workflow_file" <<EOF
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '$python_version'

EOF

    if [[ "$use_uv" == "true" ]]; then
        cat >> "$workflow_file" <<EOF
    - name: Install uv
      uses: astral-sh/setup-uv@v2

    - name: Install dependencies
      run: uv sync

EOF
    else
        cat >> "$workflow_file" <<EOF
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

EOF
    fi
}

# Add testing steps to workflow
add_test_steps() {
    local workflow_file="$1"
    local test_type="$2" # nodejs, python, mixed
    local test_commands=("${@:3}")

    case "$test_type" in
        "nodejs")
            cat >> "$workflow_file" <<EOF
    - name: Run lint
      run: pnpm lint

    - name: Run type check
      run: pnpm typecheck

    - name: Run tests
      run: pnpm test

    - name: Build
      run: pnpm build

EOF
            ;;
        "python")
            cat >> "$workflow_file" <<EOF
    - name: Run lint
      run: uv run ruff check .

    - name: Run format check
      run: uv run ruff format --check .

    - name: Run type check
      run: uv run mypy .

    - name: Run tests
      run: uv run pytest

EOF
            ;;
        "mixed")
            cat >> "$workflow_file" <<EOF
    - name: Run frontend lint
      run: pnpm lint

    - name: Run frontend type check
      run: pnpm typecheck

    - name: Run frontend tests
      run: pnpm test

    - name: Run backend lint
      run: uv run ruff check .

    - name: Run backend tests
      run: uv run pytest

    - name: Build frontend
      run: pnpm build

EOF
            ;;
        "custom")
            for command in "${test_commands[@]}"; do
                local step_name
                step_name=$(echo "$command" | sed 's/^[^ ]* //' | sed 's/^/Run /')
                cat >> "$workflow_file" <<EOF
    - name: $step_name
      run: $command

EOF
            done
            ;;
    esac
}

# Add security scanning steps
add_security_scanning() {
    local workflow_file="$1"
    local scan_types=("${@:2}")

    for scan_type in "${scan_types[@]}"; do
        case "$scan_type" in
            "codeql")
                cat >> "$workflow_file" <<EOF
    - name: Initialize CodeQL
      uses: github/codeql-action/init@v2
      with:
        languages: javascript, python

    - name: Perform CodeQL Analysis
      uses: github/codeql-action/analyze@v2

EOF
                ;;
            "snyk")
                cat >> "$workflow_file" <<EOF
    - name: Run Snyk Security Scan
      uses: snyk/actions/node@master
      env:
        SNYK_TOKEN: \${{ secrets.SNYK_TOKEN }}
      with:
        args: --severity-threshold=high

EOF
                ;;
            "dependency-check")
                cat >> "$workflow_file" <<EOF
    - name: Dependency Check
      uses: dependency-check/Dependency-Check_Action@main
      with:
        project: 'SkillMeat'
        path: '.'
        format: 'HTML'

EOF
                ;;
        esac
    done
}

# Add deployment steps
add_deployment_steps() {
    local workflow_file="$1"
    local deployment_type="$2" # vercel, netlify, docker, custom
    local deployment_config="$3"

    case "$deployment_type" in
        "vercel")
            cat >> "$workflow_file" <<EOF
    - name: Deploy to Vercel
      uses: amondnet/vercel-action@v25
      with:
        vercel-token: \${{ secrets.VERCEL_TOKEN }}
        vercel-org-id: \${{ secrets.VERCEL_ORG_ID }}
        vercel-project-id: \${{ secrets.VERCEL_PROJECT_ID }}
        vercel-args: '--prod'

EOF
            ;;
        "netlify")
            cat >> "$workflow_file" <<EOF
    - name: Deploy to Netlify
      uses: nwtgck/actions-netlify@v2.0
      with:
        publish-dir: './dist'
        production-branch: main
        github-token: \${{ secrets.GITHUB_TOKEN }}
        deploy-message: 'Deploy from GitHub Actions'
      env:
        NETLIFY_AUTH_TOKEN: \${{ secrets.NETLIFY_AUTH_TOKEN }}
        NETLIFY_SITE_ID: \${{ secrets.NETLIFY_SITE_ID }}

EOF
            ;;
        "docker")
            cat >> "$workflow_file" <<EOF
    - name: Build Docker Image
      run: docker build -t \${{ github.repository }}:\${{ github.sha }} .

    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: \${{ secrets.DOCKER_USERNAME }}
        password: \${{ secrets.DOCKER_PASSWORD }}

    - name: Push Docker Image
      run: |
        docker push \${{ github.repository }}:\${{ github.sha }}
        docker tag \${{ github.repository }}:\${{ github.sha }} \${{ github.repository }}:latest
        docker push \${{ github.repository }}:latest

EOF
            ;;
    esac
}

# Generate complete CI workflow
generate_complete_workflow() {
    local project_type="$1" # nodejs, python, mixed
    local workflow_name="${2:-CI/CD Pipeline}"
    local include_security="${3:-false}"
    local deployment_type="${4:-none}"

    local workflow_file="ci-cd.yml"
    local triggers=("push" "pull_request" "workflow_dispatch")

    echo -e "${BLUE}Generating complete CI/CD workflow for $project_type project${NC}"

    # Generate base workflow
    local workflow_path
    workflow_path=$(generate_github_workflow "$workflow_name" "$workflow_file" "${triggers[@]}")

    # Add project-specific setup
    case "$project_type" in
        "nodejs")
            add_nodejs_setup "$workflow_path" "18" "pnpm"
            add_test_steps "$workflow_path" "nodejs"
            ;;
        "python")
            add_python_setup "$workflow_path" "3.11" "true"
            add_test_steps "$workflow_path" "python"
            ;;
        "mixed")
            add_nodejs_setup "$workflow_path" "18" "pnpm"
            add_python_setup "$workflow_path" "3.11" "true"
            add_test_steps "$workflow_path" "mixed"
            ;;
    esac

    # Add security scanning if requested
    if [[ "$include_security" == "true" ]]; then
        add_security_scanning "$workflow_path" "codeql" "dependency-check"
    fi

    # Add deployment if specified
    if [[ "$deployment_type" != "none" ]]; then
        add_deployment_steps "$workflow_path" "$deployment_type" ""
    fi

    echo -e "${GREEN}✓ Generated workflow: $workflow_path${NC}"
    echo "$workflow_path"
}

# Generate pre-commit hooks
generate_pre_commit_config() {
    local project_type="$1" # nodejs, python, mixed
    local config_file=".pre-commit-config.yaml"

    echo -e "${BLUE}Generating pre-commit configuration for $project_type project${NC}"

    cat > "$config_file" <<EOF
# Pre-commit hooks configuration
repos:
EOF

    case "$project_type" in
        "nodejs"|"mixed")
            cat >> "$config_file" <<EOF
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.44.0
    hooks:
      - id: eslint
        files: \.(js|jsx|ts|tsx)$
        additional_dependencies:
          - eslint
          - '@typescript-eslint/eslint-plugin'
          - '@typescript-eslint/parser'

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.0.0
    hooks:
      - id: prettier
        files: \.(js|jsx|ts|tsx|json|css|scss|md)$

EOF
            ;;
    esac

    case "$project_type" in
        "python"|"mixed")
            cat >> "$config_file" <<EOF
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

EOF
            ;;
    esac

    echo -e "${GREEN}✓ Generated pre-commit config: $config_file${NC}"
    echo "$config_file"
}

# Generate Dockerfile
generate_dockerfile() {
    local project_type="$1" # nodejs, python, mixed
    local dockerfile="Dockerfile"

    echo -e "${BLUE}Generating Dockerfile for $project_type project${NC}"

    case "$project_type" in
        "nodejs")
            cat > "$dockerfile" <<EOF
# Node.js Dockerfile
FROM node:18-alpine

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build application
RUN pnpm build

# Expose port
EXPOSE 3000

# Start application
CMD ["pnpm", "start"]
EOF
            ;;
        "python")
            cat > "$dockerfile" <<EOF
# Python Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev

# Copy source code
COPY . .

# Expose port
EXPOSE 8000

# Start application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
            ;;
        "mixed")
            cat > "$dockerfile" <<EOF
# Multi-stage Dockerfile for mixed project
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend

# Install pnpm
RUN npm install -g pnpm

# Copy frontend package files
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./

# Install frontend dependencies
RUN pnpm install --frozen-lockfile

# Copy frontend source
COPY apps/web/ ./

# Build frontend
RUN pnpm build

# Python backend stage
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy backend dependency files
COPY services/api/pyproject.toml services/api/uv.lock ./

# Install backend dependencies
RUN uv sync --no-dev

# Copy backend source
COPY services/api/ ./

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./static

# Expose port
EXPOSE 8000

# Start application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
            ;;
    esac

    echo -e "${GREEN}✓ Generated Dockerfile: $dockerfile${NC}"
    echo "$dockerfile"
}

# Generate docker-compose.yml
generate_docker_compose() {
    local project_type="$1"
    local include_db="${2:-true}"
    local include_redis="${3:-false}"
    local compose_file="docker-compose.yml"

    echo -e "${BLUE}Generating docker-compose.yml for $project_type project${NC}"

    cat > "$compose_file" <<EOF
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://postgres:password@db:5432/skillmeat
EOF

    if [[ "$include_redis" == "true" ]]; then
        cat >> "$compose_file" <<EOF
      - REDIS_URL=redis://redis:6379
EOF
    fi

    cat >> "$compose_file" <<EOF
    depends_on:
EOF

    if [[ "$include_db" == "true" ]]; then
        cat >> "$compose_file" <<EOF
      - db
EOF
    fi

    if [[ "$include_redis" == "true" ]]; then
        cat >> "$compose_file" <<EOF
      - redis
EOF
    fi

    if [[ "$include_db" == "true" ]]; then
        cat >> "$compose_file" <<EOF

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=skillmeat
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
EOF
    fi

    if [[ "$include_redis" == "true" ]]; then
        cat >> "$compose_file" <<EOF

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
EOF
    fi

    cat >> "$compose_file" <<EOF

volumes:
EOF

    if [[ "$include_db" == "true" ]]; then
        cat >> "$compose_file" <<EOF
  postgres_data:
EOF
    fi

    echo -e "${GREEN}✓ Generated docker-compose.yml: $compose_file${NC}"
    echo "$compose_file"
}

# Setup CI/CD for project
setup_project_ci_cd() {
    local project_type="${1:-auto}"
    local include_security="${2:-false}"
    local deployment_type="${3:-none}"
    local include_containers="${4:-false}"

    echo -e "${BLUE}Setting up CI/CD for project${NC}"

    # Auto-detect project type
    if [[ "$project_type" == "auto" ]]; then
        if [[ -f "package.json" && -f "pyproject.toml" ]]; then
            project_type="mixed"
        elif [[ -f "package.json" ]]; then
            project_type="nodejs"
        elif [[ -f "pyproject.toml" ]]; then
            project_type="python"
        else
            echo -e "${YELLOW}Could not detect project type. Defaulting to nodejs${NC}"
            project_type="nodejs"
        fi
    fi

    echo -e "${BLUE}Detected project type: $project_type${NC}"

    # Generate workflow
    generate_complete_workflow "$project_type" "CI/CD Pipeline" "$include_security" "$deployment_type"

    # Generate pre-commit config
    generate_pre_commit_config "$project_type"

    # Generate container files if requested
    if [[ "$include_containers" == "true" ]]; then
        generate_dockerfile "$project_type"
        generate_docker_compose "$project_type"
    fi

    echo ""
    echo -e "${GREEN}✓ CI/CD setup completed${NC}"
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Review generated workflow files"
    echo "  2. Install pre-commit: pip install pre-commit"
    echo "  3. Setup pre-commit hooks: pre-commit install"
    echo "  4. Configure any required secrets in GitHub"

    if [[ "$include_containers" == "true" ]]; then
        echo "  5. Test Docker build: docker build -t test ."
        echo "  6. Test docker-compose: docker-compose up"
    fi
}

# Validate existing CI configuration
validate_ci_config() {
    local project_dir="${1:-.}"

    echo -e "${BLUE}Validating CI/CD configuration in: $project_dir${NC}"

    local issues=0

    # Check for GitHub workflows
    if [[ -d "$project_dir/.github/workflows" ]]; then
        local workflow_count
        workflow_count=$(find "$project_dir/.github/workflows" -name "*.yml" -o -name "*.yaml" | wc -l | xargs)
        echo -e "${GREEN}✓ Found $workflow_count GitHub workflow(s)${NC}"

        # Validate YAML syntax
        find "$project_dir/.github/workflows" -name "*.yml" -o -name "*.yaml" | while read -r workflow; do
            if command -v yq > /dev/null 2>&1; then
                if yq eval . "$workflow" > /dev/null 2>&1; then
                    echo -e "${GREEN}✓ Valid YAML: $(basename "$workflow")${NC}"
                else
                    echo -e "${RED}✗ Invalid YAML: $(basename "$workflow")${NC}"
                    ((issues++))
                fi
            fi
        done
    else
        echo -e "${YELLOW}⚠ No GitHub workflows found${NC}"
        ((issues++))
    fi

    # Check for pre-commit config
    if [[ -f "$project_dir/.pre-commit-config.yaml" ]] || [[ -f "$project_dir/.pre-commit-config.yml" ]]; then
        echo -e "${GREEN}✓ Pre-commit configuration found${NC}"
    else
        echo -e "${YELLOW}⚠ No pre-commit configuration found${NC}"
        ((issues++))
    fi

    # Check for Dockerfile
    if [[ -f "$project_dir/Dockerfile" ]]; then
        echo -e "${GREEN}✓ Dockerfile found${NC}"
    else
        echo -e "${YELLOW}⚠ No Dockerfile found${NC}"
    fi

    # Check for docker-compose
    if [[ -f "$project_dir/docker-compose.yml" ]] || [[ -f "$project_dir/docker-compose.yaml" ]]; then
        echo -e "${GREEN}✓ Docker Compose configuration found${NC}"
    else
        echo -e "${YELLOW}⚠ No Docker Compose configuration found${NC}"
    fi

    echo ""
    if [[ $issues -eq 0 ]]; then
        echo -e "${GREEN}✓ CI/CD configuration validation passed${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ CI/CD configuration has $issues issue(s)${NC}"
        return 1
    fi
}

# Export functions for sourcing
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being run directly, not sourced
    echo "CI/CD utilities loaded. Available functions:"
    echo "  generate_github_workflow, add_nodejs_setup, add_python_setup, add_test_steps"
    echo "  add_security_scanning, add_deployment_steps, generate_complete_workflow"
    echo "  generate_pre_commit_config, generate_dockerfile, generate_docker_compose"
    echo "  setup_project_ci_cd, validate_ci_config"
fi
