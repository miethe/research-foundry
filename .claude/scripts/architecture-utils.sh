#!/bin/bash

# Architecture utilities for Claude commands
# Architecture validation functions used across artifact commands

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Source dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/file-utils.sh" 2>/dev/null || true
source "$SCRIPT_DIR/validation-utils.sh" 2>/dev/null || true
source "$SCRIPT_DIR/report-utils.sh" 2>/dev/null || true

# Architecture validation functions

# Validate backend layer separation
validate_backend_layers() {
    local api_dir="${1:-services/api/app}"
    local strict_mode="${2:-false}"

    echo -e "${BLUE}=== Backend Layer Validation ===${NC}"

    if [[ ! -d "$api_dir" ]]; then
        echo -e "${RED}❌ Backend API directory not found: $api_dir${NC}"
        return 1
    fi

    local violations=0

    # Check Router layer compliance
    echo -e "\n🔍 Router Layer Compliance:"
    violations=$((violations + $(check_router_layer_compliance "$api_dir" "$strict_mode")))

    # Check Service layer compliance
    echo -e "\n🔍 Service Layer Compliance:"
    violations=$((violations + $(check_service_layer_compliance "$api_dir" "$strict_mode")))

    # Check Repository layer compliance
    echo -e "\n🔍 Repository Layer Compliance:"
    violations=$((violations + $(check_repository_layer_compliance "$api_dir" "$strict_mode")))

    # Check Model layer compliance
    echo -e "\n🔍 Model Layer Compliance:"
    violations=$((violations + $(check_model_layer_compliance "$api_dir" "$strict_mode")))

    if [[ $violations -eq 0 ]]; then
        echo -e "${GREEN}✓ All backend layers are compliant${NC}"
        return 0
    else
        echo -e "${RED}❌ Found $violations architecture violations${NC}"
        return 1
    fi
}

# Check router layer follows MP patterns
check_router_layer_compliance() {
    local api_dir="$1"
    local strict_mode="${2:-false}"
    local router_dir="$api_dir/api"

    if [[ ! -d "$router_dir" ]]; then
        echo -e "${RED}❌ Router directory not found: $router_dir${NC}"
        return 1
    fi

    echo "Checking router layer dependencies..."

    local violations=0
    local router_files

    # Find router files (limit to prevent overwhelming output)
    mapfile -t router_files < <(find "$router_dir" -name "*.py" | head -20)

    for file in "${router_files[@]}"; do
        if [[ -f "$file" ]]; then
            echo "  Checking: $(basename "$file")"

            # Violation: Direct repository imports in routers
            if grep -q "from.*repositories" "$file" || grep -q "import.*repositories" "$file"; then
                echo -e "    ${RED}❌ Direct repository import (should use services)${NC}"
                violations=$((violations + 1))
            fi

            # Violation: Direct model operations in routers
            if grep -q "\.create\|\.update\|\.delete" "$file" && ! grep -q "service\." "$file"; then
                echo -e "    ${RED}❌ Direct model operations (should delegate to services)${NC}"
                violations=$((violations + 1))
            fi

            # Violation: Missing error response envelope
            if [[ "$strict_mode" == "true" ]]; then
                if ! grep -q "ErrorResponse\|error_response\|HTTPException" "$file"; then
                    echo -e "    ${YELLOW}⚠ Missing error response envelope${NC}"
                    violations=$((violations + 1))
                fi
            fi

            # Good: Service layer usage
            if grep -q "from.*services" "$file" || grep -q "import.*services" "$file"; then
                echo -e "    ${GREEN}✓ Uses service layer${NC}"
            fi

            # Good: Error response envelope
            if grep -q "ErrorResponse\|error_response" "$file"; then
                echo -e "    ${GREEN}✓ Uses error response envelope${NC}"
            fi

            # Good: Route handler patterns
            if grep -q "@router\.\(get\|post\|put\|delete\)" "$file"; then
                echo -e "    ${GREEN}✓ Proper route handler patterns${NC}"
            fi
        fi
    done

    echo "$violations"
}

# Check service layer follows MP patterns
check_service_layer_compliance() {
    local api_dir="$1"
    local strict_mode="${2:-false}"
    local service_dir="$api_dir/services"

    if [[ ! -d "$service_dir" ]]; then
        echo -e "${RED}❌ Service directory not found: $service_dir${NC}"
        return 1
    fi

    echo "Checking service layer dependencies..."

    local violations=0
    local service_files

    mapfile -t service_files < <(find "$service_dir" -name "*.py" | head -20)

    for file in "${service_files[@]}"; do
        if [[ -f "$file" ]]; then
            echo "  Checking: $(basename "$file")"

            # Good: Repository layer usage
            if grep -q "from.*repositories" "$file" || grep -q "import.*repositories" "$file"; then
                echo -e "    ${GREEN}✓ Uses repository layer${NC}"
            fi

            # Violation: Direct database imports (should use repositories)
            if grep -q "from sqlalchemy" "$file" && ! grep -q "from.*repositories" "$file"; then
                echo -e "    ${RED}❌ Direct database imports (should use repositories)${NC}"
                violations=$((violations + 1))
            fi

            # Violation: Direct HTTP handling (should be in routers)
            if grep -q "Request\|Response\|@app\|@router" "$file"; then
                echo -e "    ${RED}❌ Direct HTTP handling (should be in routers)${NC}"
                violations=$((violations + 1))
            fi

            # Good: DTO usage for data transformation
            if grep -q "Dto\|Schema" "$file"; then
                echo -e "    ${GREEN}✓ Uses DTOs for data transformation${NC}"
            fi

            # Check for business logic patterns
            if grep -E "(def|async def)\s+\w+.*:" "$file" | grep -q -v "__init__"; then
                echo -e "    ${GREEN}✓ Contains business logic methods${NC}"
            fi
        fi
    done

    echo "$violations"
}

# Check repository layer follows MP patterns
check_repository_layer_compliance() {
    local api_dir="$1"
    local strict_mode="${2:-false}"
    local repo_dir="$api_dir/repositories"

    if [[ ! -d "$repo_dir" ]]; then
        echo -e "${RED}❌ Repository directory not found: $repo_dir${NC}"
        return 1
    fi

    echo "Checking repository layer dependencies..."

    local violations=0
    local repo_files

    mapfile -t repo_files < <(find "$repo_dir" -name "*.py" | head -20)

    for file in "${repo_files[@]}"; do
        if [[ -f "$file" ]]; then
            echo "  Checking: $(basename "$file")"

            # Good: Database/ORM usage
            if grep -q "from sqlalchemy" "$file" || grep -q "from.*models" "$file"; then
                echo -e "    ${GREEN}✓ Uses ORM/models appropriately${NC}"
            fi

            # Violation: Business logic in repositories
            if grep -q "validate\|calculate\|process" "$file"; then
                echo -e "    ${YELLOW}⚠ Possible business logic in repository${NC}"
                violations=$((violations + 1))
            fi

            # Violation: HTTP handling in repositories
            if grep -q "Request\|Response\|@app\|@router" "$file"; then
                echo -e "    ${RED}❌ HTTP handling in repository (should be in routers)${NC}"
                violations=$((violations + 1))
            fi

            # Good: CRUD operations
            if grep -q "create\|read\|update\|delete\|get\|find" "$file"; then
                echo -e "    ${GREEN}✓ Implements CRUD operations${NC}"
            fi

            # Check for RLS (Row Level Security) patterns
            if grep -q "user_id\|current_user" "$file"; then
                echo -e "    ${GREEN}✓ Implements Row Level Security patterns${NC}"
            fi
        fi
    done

    echo "$violations"
}

# Check model layer follows MP patterns
check_model_layer_compliance() {
    local api_dir="$1"
    local strict_mode="${2:-false}"
    local model_dir="$api_dir/models"

    if [[ ! -d "$model_dir" ]]; then
        echo -e "${RED}❌ Model directory not found: $model_dir${NC}"
        return 1
    fi

    echo "Checking model layer dependencies..."

    local violations=0
    local model_files

    mapfile -t model_files < <(find "$model_dir" -name "*.py" | head -20)

    for file in "${model_files[@]}"; do
        if [[ -f "$file" ]]; then
            echo "  Checking: $(basename "$file")"

            # Good: SQLAlchemy model definitions
            if grep -q "Base\|Table\|Column\|relationship" "$file"; then
                echo -e "    ${GREEN}✓ Contains proper model definitions${NC}"
            fi

            # Violation: Business logic in models
            if grep -E "(def|async def)\s+\w+.*:" "$file" | grep -v "__" | grep -q -v "to_dict\|from_dict"; then
                echo -e "    ${YELLOW}⚠ Possible business logic in model${NC}"
                violations=$((violations + 1))
            fi

            # Violation: HTTP handling in models
            if grep -q "Request\|Response\|@app\|@router" "$file"; then
                echo -e "    ${RED}❌ HTTP handling in model${NC}"
                violations=$((violations + 1))
            fi

            # Good: Validation patterns
            if grep -q "validator\|validates" "$file"; then
                echo -e "    ${GREEN}✓ Contains validation logic${NC}"
            fi
        fi
    done

    echo "$violations"
}

# Validate frontend architecture
validate_frontend_architecture() {
    local app_dir="${1:-apps/web}"
    local strict_mode="${2:-false}"

    echo -e "${BLUE}=== Frontend Architecture Validation ===${NC}"

    if [[ ! -d "$app_dir" ]]; then
        echo -e "${RED}❌ Frontend app directory not found: $app_dir${NC}"
        return 1
    fi

    local violations=0

    # Check Next.js App Router structure
    echo -e "\n🔍 Next.js App Router Structure:"
    violations=$((violations + $(check_nextjs_structure "$app_dir" "$strict_mode")))

    # Check component architecture
    echo -e "\n🔍 Component Architecture:"
    violations=$((violations + $(check_component_architecture "$app_dir" "$strict_mode")))

    # Check state management
    echo -e "\n🔍 State Management:"
    violations=$((violations + $(check_state_management "$app_dir" "$strict_mode")))

    # Check UI library usage
    echo -e "\n🔍 UI Library Usage:"
    violations=$((violations + $(check_ui_library_usage "$app_dir" "$strict_mode")))

    if [[ $violations -eq 0 ]]; then
        echo -e "${GREEN}✓ Frontend architecture is compliant${NC}"
        return 0
    else
        echo -e "${RED}❌ Found $violations frontend architecture violations${NC}"
        return 1
    fi
}

# Check Next.js App Router structure
check_nextjs_structure() {
    local app_dir="$1"
    local strict_mode="${2:-false}"

    local violations=0

    # Check for App Router structure
    if [[ -d "$app_dir/src/app" ]]; then
        echo -e "  ${GREEN}✓ Uses Next.js App Router structure${NC}"
    else
        echo -e "  ${RED}❌ Missing App Router structure (src/app)${NC}"
        violations=$((violations + 1))
    fi

    # Check for proper page files
    local page_files
    mapfile -t page_files < <(find "$app_dir/src/app" -name "page.tsx" 2>/dev/null || true)

    if [[ ${#page_files[@]} -gt 0 ]]; then
        echo -e "  ${GREEN}✓ Contains App Router pages (${#page_files[@]} found)${NC}"
    else
        echo -e "  ${YELLOW}⚠ No page.tsx files found${NC}"
        violations=$((violations + 1))
    fi

    # Check for layout files
    if [[ -f "$app_dir/src/app/layout.tsx" ]]; then
        echo -e "  ${GREEN}✓ Has root layout file${NC}"
    else
        echo -e "  ${RED}❌ Missing root layout.tsx${NC}"
        violations=$((violations + 1))
    fi

    echo "$violations"
}

# Check component architecture
check_component_architecture() {
    local app_dir="$1"
    local strict_mode="${2:-false}"

    local violations=0

    # Check components directory structure
    if [[ -d "$app_dir/src/components" ]]; then
        echo -e "  ${GREEN}✓ Has components directory${NC}"
    else
        echo -e "  ${RED}❌ Missing src/components directory${NC}"
        violations=$((violations + 1))
    fi

    # Check for proper component organization
    local component_dirs=("marketing" "ui" "forms" "layout")
    for dir in "${component_dirs[@]}"; do
        if [[ -d "$app_dir/src/components/$dir" ]]; then
            echo -e "  ${GREEN}✓ Has $dir components directory${NC}"
        fi
    done

    # Check for direct Radix imports (should use @meaty/ui)
    local direct_radix_imports=0
    if [[ -d "$app_dir/src" ]]; then
        direct_radix_imports=$(find "$app_dir/src" -name "*.tsx" -o -name "*.ts" | \
            xargs grep -l "@radix-ui" 2>/dev/null | wc -l)
    fi

    if [[ $direct_radix_imports -gt 0 ]]; then
        echo -e "  ${RED}❌ Found $direct_radix_imports files with direct Radix imports (should use @meaty/ui)${NC}"
        violations=$((violations + direct_radix_imports))
    else
        echo -e "  ${GREEN}✓ No direct Radix imports found${NC}"
    fi

    echo "$violations"
}

# Check state management patterns
check_state_management() {
    local app_dir="$1"
    local strict_mode="${2:-false}"

    local violations=0

    # Check for React Query usage
    if [[ -f "$app_dir/package.json" ]]; then
        if grep -q "@tanstack/react-query\|react-query" "$app_dir/package.json"; then
            echo -e "  ${GREEN}✓ Uses React Query for server state${NC}"
        else
            echo -e "  ${YELLOW}⚠ React Query not found in dependencies${NC}"
        fi
    fi

    # Check for proper hooks directory
    if [[ -d "$app_dir/src/hooks" ]]; then
        echo -e "  ${GREEN}✓ Has hooks directory${NC}"

        # Check for custom hooks
        local hook_files
        mapfile -t hook_files < <(find "$app_dir/src/hooks" -name "use*.ts" -o -name "use*.tsx" 2>/dev/null)

        if [[ ${#hook_files[@]} -gt 0 ]]; then
            echo -e "  ${GREEN}✓ Contains custom hooks (${#hook_files[@]} found)${NC}"
        fi
    fi

    # Check for state patterns in components
    if [[ -d "$app_dir/src" ]]; then
        local useState_usage
        useState_usage=$(find "$app_dir/src" -name "*.tsx" | \
            xargs grep -l "useState" 2>/dev/null | wc -l)

        if [[ $useState_usage -gt 0 ]]; then
            echo -e "  ${GREEN}✓ Uses React state management${NC}"
        fi
    fi

    echo "$violations"
}

# Check UI library usage
check_ui_library_usage() {
    local app_dir="$1"
    local strict_mode="${2:-false}"

    local violations=0

    # Check for @meaty/ui imports
    if [[ -d "$app_dir/src" ]]; then
        local meaty_ui_imports
        meaty_ui_imports=$(find "$app_dir/src" -name "*.tsx" -o -name "*.ts" | \
            xargs grep -l "@meaty/ui" 2>/dev/null | wc -l)

        if [[ $meaty_ui_imports -gt 0 ]]; then
            echo -e "  ${GREEN}✓ Uses @meaty/ui components ($meaty_ui_imports files)${NC}"
        else
            echo -e "  ${YELLOW}⚠ No @meaty/ui imports found${NC}"
        fi
    fi

    # Check package.json for UI dependencies
    if [[ -f "$app_dir/package.json" ]]; then
        if grep -q "@meaty/ui" "$app_dir/package.json"; then
            echo -e "  ${GREEN}✓ @meaty/ui dependency present${NC}"
        else
            echo -e "  ${RED}❌ @meaty/ui dependency missing${NC}"
            violations=$((violations + 1))
        fi
    fi

    echo "$violations"
}

# Generate architecture compliance report
generate_architecture_report() {
    local component="${1:-all}"
    local output_format="${2:-text}"
    local strict_mode="${3:-false}"

    echo -e "${BLUE}=== Architecture Compliance Report ===${NC}"

    local total_violations=0
    local backend_violations=0
    local frontend_violations=0

    case "$component" in
        "backend")
            backend_violations=$(validate_backend_layers "services/api/app" "$strict_mode")
            total_violations=$backend_violations
            ;;
        "frontend")
            frontend_violations=$(validate_frontend_architecture "apps/web" "$strict_mode")
            total_violations=$frontend_violations
            ;;
        "all"|*)
            backend_violations=$(validate_backend_layers "services/api/app" "$strict_mode" 2>/dev/null || echo "0")
            frontend_violations=$(validate_frontend_architecture "apps/web" "$strict_mode" 2>/dev/null || echo "0")
            total_violations=$((backend_violations + frontend_violations))
            ;;
    esac

    # Generate summary
    echo -e "\n${BLUE}=== Architecture Compliance Summary ===${NC}"

    if [[ "$component" == "all" || "$component" == "backend" ]]; then
        if [[ $backend_violations -eq 0 ]]; then
            echo -e "Backend: ${GREEN}✓ Compliant${NC}"
        else
            echo -e "Backend: ${RED}❌ $backend_violations violations${NC}"
        fi
    fi

    if [[ "$component" == "all" || "$component" == "frontend" ]]; then
        if [[ $frontend_violations -eq 0 ]]; then
            echo -e "Frontend: ${GREEN}✓ Compliant${NC}"
        else
            echo -e "Frontend: ${RED}❌ $frontend_violations violations${NC}"
        fi
    fi

    echo -e "Total violations: $total_violations"

    # Return status based on violations
    return $total_violations
}

# Main function for testing
main() {
    local command="${1:-help}"

    case "$command" in
        "backend")
            validate_backend_layers "${2:-services/api/app}" "${3:-false}"
            ;;
        "frontend")
            validate_frontend_architecture "${2:-apps/web}" "${3:-false}"
            ;;
        "report")
            generate_architecture_report "${2:-all}" "${3:-text}" "${4:-false}"
            ;;
        "help"|*)
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  backend [api_dir] [strict_mode]"
            echo "  frontend [app_dir] [strict_mode]"
            echo "  report [component] [format] [strict_mode]"
            echo ""
            echo "Examples:"
            echo "  $0 backend services/api/app true"
            echo "  $0 frontend apps/web false"
            echo "  $0 report all text true"
            ;;
    esac
}

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
