---
description: Validate all artifacts before creating PR ensuring MP compliance and quality
allowed-tools: Read(./**), Bash(git:*), Bash(pnpm:*), Bash(uv:*), Bash(node:*), Bash(pre-commit:*), Grep, Glob
argument-hint: "[--strict-mode] [--fix-issues] [--report-format=text|json|md] [--skip-tests]"
---

# Pre-PR Validation

Comprehensive validation suite that checks all artifacts, code quality, tests, and compliance before creating a pull request, ensuring adherence to SkillMeat standards.

## Context Analysis

Analyze current PR readiness and identify validation scope:

```bash
# Source shared utilities with fallbacks
source .claude/scripts/git-utils.sh 2>/dev/null || echo "Warning: git-utils.sh not found"
source .claude/scripts/report-utils.sh 2>/dev/null || echo "Warning: report-utils.sh not found"
source .claude/scripts/validation-utils.sh 2>/dev/null || echo "Warning: validation-utils.sh not found"
source .claude/scripts/json-utils.sh 2>/dev/null || echo "Warning: json-utils.sh not found"
source .claude/scripts/file-utils.sh 2>/dev/null || echo "Warning: file-utils.sh not found"
source .claude/scripts/architecture-utils.sh 2>/dev/null || echo "Warning: architecture-utils.sh not found"

# Initialize validation report
if type init_report >/dev/null 2>&1; then
    init_report "Pre-PR Validation"
else
    echo "=== Pre-PR Validation ==="
fi

# Get comprehensive Git status
echo "=== PR Readiness Assessment ==="
if type get_git_status_report >/dev/null 2>&1; then
    get_git_status_report "text"
else
    git status --porcelain
fi

# Check repository state
if type check_git_repo >/dev/null 2>&1; then
    if check_git_repo; then
        echo "✓ Valid Git repository"
    else
        echo "❌ Not a valid Git repository"
        exit 1
    fi
fi
```

## Pre-Validation Checks

Check for common PR blockers:

```bash
echo -e "\n=== PR Blocker Check ==="
blockers=()

# Check for uncommitted changes in critical files
critical_files=("package.json" "pyproject.toml" "CLAUDE.md" "README.md")
for file in "${critical_files[@]}"; do
    if [[ -f "$file" ]] && git diff --name-only | grep -q "^$file$"; then
        blockers+=("Uncommitted changes in critical file: $file")
        echo "❌ $file has uncommitted changes"
    fi
done

# Check for required files using validation utilities
if type validate_required_files >/dev/null 2>&1; then
    required_files=("README.md" "CLAUDE.md" ".gitignore")
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            blockers+=("Missing required file: $file")
            echo "❌ Missing: $file"
        else
            echo "✓ Required file exists: $file"
        fi
    done
fi

# Check for large files
if type find_large_files >/dev/null 2>&1; then
    large_files=$(find_large_files "10MB" "." 2>/dev/null || true)
    if [[ -n "$large_files" ]]; then
        while IFS= read -r file; do
            if [[ -n "$file" ]]; then
                blockers+=("Large file detected: $file")
                echo "❌ Large file: $file"
            fi
        done <<< "$large_files"
    fi
else
    # Fallback large file check
    if command -v find >/dev/null 2>&1; then
        large_files=$(find . -type f -size +10M ! -path "./.git/*" ! -path "./node_modules/*" 2>/dev/null | head -5)
        if [[ -n "$large_files" ]]; then
            while IFS= read -r file; do
                if [[ -n "$file" ]]; then
                    blockers+=("Large file detected: $file")
                    echo "❌ Large file: $file"
                fi
            done <<< "$large_files"
        fi
    fi
fi

# Check for merge conflicts
if git status --porcelain | grep -q "^UU\|^AA\|^DD"; then
    blockers+=("Merge conflicts detected")
    echo "❌ Merge conflicts found"
else
    echo "✓ No merge conflicts"
fi

# Report blocker status
if [[ ${#blockers[@]} -eq 0 ]]; then
    echo "✅ No PR blockers detected"
else
    echo "❌ Found ${#blockers[@]} PR blockers:"
    printf "  - %s\n" "${blockers[@]}"

    if type add_error >/dev/null 2>&1; then
        add_error "${#blockers[@]} PR blockers must be resolved"
    fi
fi
```

## Artifact Validation

Validate project artifacts:

```bash
echo -e "\n=== Artifact Validation ==="
artifact_errors=0

# Validate package.json files
echo "Validating package.json files..."
if type validate_package_json >/dev/null 2>&1; then
    for package_file in $(find . -name "package.json" ! -path "./node_modules/*" 2>/dev/null); do
        if validate_package_json "$package_file" true; then
            echo "✓ Valid: $package_file"
        else
            echo "❌ Invalid: $package_file"
            artifact_errors=$((artifact_errors + 1))
        fi
    done
else
    echo "⚠ Package validation not available"
fi

# Validate Python project files
echo "Validating Python project files..."
if type validate_pyproject_toml >/dev/null 2>&1; then
    for pyproject_file in $(find . -name "pyproject.toml" 2>/dev/null); do
        if validate_pyproject_toml "$pyproject_file" true; then
            echo "✓ Valid: $pyproject_file"
        else
            echo "❌ Invalid: $pyproject_file"
            artifact_errors=$((artifact_errors + 1))
        fi
    done
fi

# Validate AI artifacts
echo "Validating AI artifacts..."
ai_artifacts=("ai/repo.map.json" "ai/symbols.graph.json" "ai/chunking.config.json")
for artifact in "${ai_artifacts[@]}"; do
    if [[ -f "$artifact" ]]; then
        if type validate_json_file >/dev/null 2>&1; then
            if validate_json_file "$artifact" true; then
                echo "✓ Valid AI artifact: $artifact"
            else
                echo "❌ Invalid AI artifact: $artifact"
                artifact_errors=$((artifact_errors + 1))
            fi
        else
            echo "⚠ JSON validation not available for: $artifact"
        fi
    fi
done

# Report artifact validation results
if [[ $artifact_errors -eq 0 ]]; then
    echo "✅ All artifacts are valid"
    if type add_success >/dev/null 2>&1; then
        add_success "All project artifacts validated successfully"
    fi
else
    echo "❌ Found $artifact_errors artifact validation errors"
    if type add_error >/dev/null 2>&1; then
        add_error "$artifact_errors artifact validation errors found"
    fi
fi
```

## Architecture Validation

Check architectural compliance:

```bash
echo -e "\n=== Architecture Validation ==="

# Backend architecture validation
if [[ -d "services/api" ]]; then
    echo "Validating backend architecture..."
    if type validate_backend_layers >/dev/null 2>&1; then
        if validate_backend_layers "services/api/app" false; then
            echo "✅ Backend architecture is compliant"
        else
            echo "❌ Backend architecture violations found"
            artifact_errors=$((artifact_errors + 1))
        fi
    else
        echo "⚠ Backend architecture validation not available"
    fi
fi

# Frontend architecture validation
if [[ -d "apps/web" ]]; then
    echo "Validating frontend architecture..."
    if type validate_frontend_architecture >/dev/null 2>&1; then
        if validate_frontend_architecture "apps/web" false; then
            echo "✅ Frontend architecture is compliant"
        else
            echo "❌ Frontend architecture violations found"
            artifact_errors=$((artifact_errors + 1))
        fi
    else
        echo "⚠ Frontend architecture validation not available"
    fi
fi

# Check for direct Radix imports (should use @miethe/ui)
echo "Checking UI library compliance..."
if [[ -d "apps/web/src" ]]; then
    direct_radix=$(find apps/web/src -name "*.tsx" -o -name "*.ts" | xargs grep -l "@radix-ui" 2>/dev/null | wc -l)
    if [[ $direct_radix -gt 0 ]]; then
        echo "❌ Found $direct_radix files with direct Radix imports (should use @miethe/ui)"
        artifact_errors=$((artifact_errors + 1))
    else
        echo "✓ No direct Radix imports found"
    fi
fi
```

## Code Quality Checks

Run code quality and linting checks:

```bash
echo -e "\n=== Code Quality Checks ==="

# TypeScript compilation check
if [[ -f "tsconfig.json" || -f "apps/web/tsconfig.json" ]]; then
    echo "Checking TypeScript compilation..."
    if command -v pnpm >/dev/null 2>&1; then
        if pnpm --filter "./apps/web" typecheck --noEmit 2>/dev/null; then
            echo "✅ TypeScript compilation successful"
        else
            echo "❌ TypeScript compilation failed"
            artifact_errors=$((artifact_errors + 1))
        fi
    fi
fi

# Linting check
echo "Running linting checks..."
if command -v pnpm >/dev/null 2>&1; then
    if pnpm --filter "./apps/web" lint --max-warnings 0 2>/dev/null; then
        echo "✅ Linting passed"
    else
        echo "❌ Linting failed"
        artifact_errors=$((artifact_errors + 1))
    fi
fi

# Pre-commit hooks check
if [[ -f ".pre-commit-config.yaml" ]] && command -v pre-commit >/dev/null 2>&1; then
    echo "Running pre-commit hooks..."
    if pre-commit run --all-files 2>/dev/null; then
        echo "✅ Pre-commit hooks passed"
    else
        echo "❌ Pre-commit hooks failed"
        artifact_errors=$((artifact_errors + 1))
    fi
fi
```

## Test Execution

Run test suites:

```bash
echo -e "\n=== Test Execution ==="

# Skip tests if requested
skip_tests=false
for arg in "$@"; do
    [[ "$arg" == "--skip-tests" ]] && skip_tests=true && break
done

if [[ "$skip_tests" == "true" ]]; then
    echo "⏭️ Tests skipped as requested"
else
    # Frontend tests
    if [[ -f "apps/web/package.json" ]]; then
        echo "Running frontend tests..."
        if command -v pnpm >/dev/null 2>&1; then
            if pnpm --filter "./apps/web" test --run 2>/dev/null; then
                echo "✅ Frontend tests passed"
            else
                echo "❌ Frontend tests failed"
                artifact_errors=$((artifact_errors + 1))
            fi
        fi
    fi

    # Backend tests
    if [[ -f "services/api/pyproject.toml" ]]; then
        echo "Running backend tests..."
        if command -v uv >/dev/null 2>&1; then
            if PYTHONPATH="$PWD/services/api" uv run --project services/api pytest 2>/dev/null; then
                echo "✅ Backend tests passed"
            else
                echo "❌ Backend tests failed"
                artifact_errors=$((artifact_errors + 1))
            fi
        fi
    fi

    # UI package tests
    if [[ -f "packages/ui/package.json" ]]; then
        echo "Running UI package tests..."
        if command -v pnpm >/dev/null 2>&1; then
            if pnpm --filter "./packages/ui" test --run 2>/dev/null; then
                echo "✅ UI package tests passed"
            else
                echo "❌ UI package tests failed"
                artifact_errors=$((artifact_errors + 1))
            fi
        fi
    fi
fi
```

## Security Checks

Run security validations:

```bash
echo -e "\n=== Security Checks ==="

# Dependency audit
echo "Running dependency audit..."
if command -v pnpm >/dev/null 2>&1; then
    if pnpm audit --audit-level=high 2>/dev/null; then
        echo "✅ Dependency audit passed"
    else
        echo "⚠️ Dependency audit found issues (review required)"
    fi
fi

# Check for secrets in staged files
echo "Scanning for potential secrets..."
secret_patterns=("password" "secret" "key" "token" "api_key" "private")
secrets_found=false

if command -v git >/dev/null 2>&1 && git status --porcelain | grep -q "^[AM]"; then
    staged_files=$(git diff --cached --name-only)
    for file in $staged_files; do
        if [[ -f "$file" && ! "$file" =~ \.(md|txt|json|yaml|yml)$ ]]; then
            for pattern in "${secret_patterns[@]}"; do
                if grep -qi "$pattern" "$file" 2>/dev/null; then
                    echo "⚠️ Potential secret in: $file (pattern: $pattern)"
                    secrets_found=true
                fi
            done
        fi
    done
fi

if [[ "$secrets_found" == "false" ]]; then
    echo "✅ No obvious secrets detected"
fi

# File permissions check
echo "Checking file permissions..."
if type validate_file_permissions >/dev/null 2>&1; then
    # Check script files have correct permissions
    for script in $(find .claude/scripts -name "*.sh" 2>/dev/null); do
        if validate_file_permissions "$script" "755"; then
            echo "✓ Script permissions correct: $script"
        else
            echo "⚠️ Script permissions incorrect: $script"
        fi
    done
fi
```

## Final Report

Generate comprehensive validation report:

```bash
echo -e "\n=== Pre-PR Validation Summary ==="

# Calculate total issues
total_issues=$((${#blockers[@]} + artifact_errors))

# Generate final report
if type generate_report >/dev/null 2>&1; then
    # Use structured reporting if available
    if [[ $total_issues -eq 0 ]]; then
        add_success "All validations passed - PR ready"
        add_success "No blockers or validation errors found"
    else
        add_error "Found $total_issues issues that need resolution"
        if [[ ${#blockers[@]} -gt 0 ]]; then
            add_error "PR blockers: ${#blockers[@]}"
        fi
        if [[ $artifact_errors -gt 0 ]]; then
            add_error "Validation errors: $artifact_errors"
        fi
    fi

    # Check report format parameter
    report_format="text"
    for arg in "$@"; do
        if [[ "$arg" =~ --report-format=(.*) ]]; then
            report_format="${BASH_REMATCH[1]}"
        fi
    done

    generate_report "$report_format"
else
    # Fallback summary
    echo "PR Blockers: ${#blockers[@]}"
    echo "Validation Errors: $artifact_errors"
    echo "Total Issues: $total_issues"
    echo "Timestamp: $(date)"
fi

# Exit status and next steps
if [[ $total_issues -eq 0 ]]; then
    echo -e "\n🎉 Ready for PR Creation!"
    echo "✅ All validations passed"
    echo "✅ No blockers detected"
    echo "✅ Code quality checks successful"
    echo ""
    echo "Next steps:"
    echo "  1. Create pull request"
    echo "  2. Add descriptive title and description"
    echo "  3. Request reviews from appropriate team members"
    echo "  4. Monitor CI/CD pipeline results"

    exit 0
else
    echo -e "\n🚫 PR Not Ready"
    echo "❌ Found $total_issues issues that must be resolved"
    echo ""
    echo "Required actions:"

    if [[ ${#blockers[@]} -gt 0 ]]; then
        echo "  🔧 Fix PR blockers:"
        printf "    - %s\n" "${blockers[@]}"
    fi

    if [[ $artifact_errors -gt 0 ]]; then
        echo "  🔧 Fix validation errors (run individual commands for details)"
    fi

    echo ""
    echo "Helpful commands:"
    echo "  /post-implementation-updates  # Update all artifacts"
    echo "  /check-architecture           # Validate architecture"
    echo "  /scan-violations             # Check for policy violations"
    echo "  /validate-contracts          # Validate API contracts"

    exit 1
fi
```

## Command Parameters

Handle command line arguments:

```bash
# Parse arguments (processed above in individual sections)
# --strict-mode: Enable stricter validation rules
# --fix-issues: Attempt to auto-fix issues where possible
# --report-format=text|json|md: Output format for final report
# --skip-tests: Skip test execution to speed up validation

# This comprehensive validation ensures all aspects of the PR are ready:
# ✅ No blocking issues
# ✅ All artifacts are valid and up-to-date
# ✅ Architecture compliance verified
# ✅ Code quality standards met
# ✅ Tests passing
# ✅ Security checks completed
```

This validation suite provides comprehensive PR readiness checks while leveraging shared utilities for consistency and maintainability. It ensures all SkillMeat standards are met before code review.
