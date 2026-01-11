#!/bin/bash
# git_push - Git Commit and Push Script
#
# Commits all changes with detailed message and pushes to remote.
# Analyzes changes to generate meaningful commit messages.
#
# Usage: git_push.sh [--no-push] [--amend] [--message <msg>] [--type <type>]

set -e

# ========================================
# Configuration
# ========================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Resolve project root by finding .git directory
if [ -d "./.git" ]; then
    PROJECT_ROOT="$(pwd)"
elif [ -d "../.git" ]; then
    PROJECT_ROOT="$(cd "$(pwd)/.." && pwd)"
elif [ -d "../../.git" ]; then
    PROJECT_ROOT="$(cd "$(pwd)/../.." && pwd)"
else
    # Fallback: find .git by going up
    CURRENT_DIR="$(pwd)"
    while [ "$CURRENT_DIR" != "/" ]; do
        if [ -d "$CURRENT_DIR/.git" ]; then
            PROJECT_ROOT="$CURRENT_DIR"
            break
        fi
        CURRENT_DIR="$(dirname "$CURRENT_DIR")"
    done
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Flags
NO_PUSH=false
AMEND=false
CUSTOM_MESSAGE=""
FORCE_TYPE=""

# ========================================
# Parse Arguments
# ========================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-push)
            NO_PUSH=true
            shift
            ;;
        --amend)
            AMEND=true
            shift
            ;;
        --message)
            CUSTOM_MESSAGE="$2"
            shift 2
            ;;
        --type)
            FORCE_TYPE="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--no-push] [--amend] [--message <msg>] [--type <type>]"
            exit 1
            ;;
    esac
done

# ========================================
# Functions
# ========================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_header() {
    echo
    echo "========================================"
    echo "$1"
    echo "========================================"
    echo
}

# Check for merge conflicts
check_conflicts() {
    if git diff --name-only --diff-filter=U | grep -q .; then
        log_error "Uncommitted merge conflicts detected"
        echo
        echo "Please resolve conflicts before running git_push"
        echo "Conflicting files:"
        git diff --name-only --diff-filter=U | sed 's/^/  /'
        exit 1
    fi
}

# Get current branch
get_branch() {
    git rev-parse --abbrev-ref HEAD
}

# Detect commit type from changes
detect_type() {
    local files="$1"
    local type="$FORCE_TYPE"

    if [ -n "$type" ]; then
        echo "$type"
        return
    fi

    # Analyze file patterns
    if echo "$files" | grep -qE "(server/app/api|runner/app/services|frontend/src/pages).*\.py"; then
        if git diff --cached --name-only | grep -q "test_"; then
            type="test"
        elif git diff --cached --stat | grep -qE "^\s+.* deletions"; then
            type="fix"
        else
            type="feat"
        fi
    elif echo "$files" | grep -qE "(\.md|\.txt|docs/|SKILL\.md)"; then
        type="docs"
    elif echo "$files" | grep -qE "(\.css|\.tsx?|tailwind|components/ui)"; then
        if git diff --cached --stat | grep -q "style\|format\|lint"; then
            type="style"
        else
            type="feat"
        fi
    elif echo "$files" | grep -qE "(docker-compose|Dockerfile|\.sh|scripts/)"; then
        type="chore"
    elif echo "$files" | grep -qE "test_.*\.py|tests/"; then
        type="test"
    elif echo "$files" | grep -qE "(config\.py|\.env|settings)"; then
        type="chore"
    else
        type="chore"
    fi

    echo "$type"
}

# Detect scope from changes
detect_scope() {
    local files="$1"

    if echo "$files" | grep -qE "server/app/api/shared"; then
        echo "shared-api"
    elif echo "$files" | grep -qE "server/app/api|runner/app"; then
        echo "backend"
    elif echo "$files" | grep -qE "frontend/src"; then
        echo "frontend"
    elif echo "$files" | grep -qE "docker|nginx"; then
        echo "deployment"
    elif echo "$files" | grep -qE "CLAUDE|README|\.md"; then
        echo "docs"
    elif echo "$files" | grep -qE "\.sh|scripts/"; then
        echo "scripts"
    else
        echo ""
    fi
}

# Generate commit message
generate_message() {
    local type="$1"
    local scope="$2"
    local changes="$3"

    if [ -n "$CUSTOM_MESSAGE" ]; then
        echo "$CUSTOM_MESSAGE"
        return
    fi

    # Get branch name for context
    local branch=$(get_branch)

    # Count files and lines
    local file_count=$(echo "$changes" | wc -l)
    local additions=$(git diff --cached --numstat | awk '{sum+=$1} END {print sum}')
    local deletions=$(git diff --cached --numstat | awk '{sum+=$2} END {print sum}')
    additions=${additions:-0}
    deletions=${deletions:-0}

    # Build header
    if [ -n "$scope" ]; then
        header="${type}(${scope}):"
    else
        header="${type}:"
    fi

    # Generate description based on changes
    description=""
    case "$type" in
        feat)
            if [ "$file_count" -eq 1 ]; then
                description="Add $(echo "$changes" | head -1 | xargs basename | sed 's/\.[^.]*$//') functionality"
            else
                description="Add new features and improvements"
            fi
            ;;
        fix)
            description="Fix issues and bugs"
            ;;
        docs)
            description="Update documentation"
            ;;
        refactor)
            description="Refactor code structure"
            ;;
        style)
            description="Improve code formatting and style"
            ;;
        test)
            description="Add or update tests"
            ;;
        chore)
            description="Perform maintenance tasks"
            ;;
        perf)
            description="Optimize performance"
            ;;
        *)
            description="Update codebase"
            ;;
    esac

    # Build full message
    local msg=""
    msg="${header} ${description}"

    # Add body with file list
    if [ "$file_count" -gt 0 ]; then
        msg+=$'\n'
        msg+="Changes:"
        # Build file list using process substitution
        while IFS= read -r file; do
            if [ -n "$file" ]; then
                local filename=$(basename "$file")
                msg+=$'\n'
                msg+="  • ${filename}"
            fi
        done <<< "$changes"
    fi

    # Add co-author attribution
    msg+=$'\n'
    msg+=$'\n'
    msg+="Co-Authored-By: Claude <noreply@anthropic.com>"

    echo "$msg"
}

# ========================================
# Main Execution
# ========================================
cd "$PROJECT_ROOT"

print_header "🚀 Git Commit and Push"

# Check for conflicts
check_conflicts

# Check if we have changes
if [ "$AMEND" = false ]; then
    if [ -z "$(git status --porcelain)" ]; then
        log_warning "No changes to commit"
        exit 0
    fi

    # Stage all changes
    log_info "Staging all changes..."
    git add -A
fi

# Get changed files
changed_files=$(git diff --cached --name-only | grep -v "^$" || true)

if [ -z "$changed_files" ] && [ "$AMEND" = false ]; then
    log_warning "No changes staged after git add"
    exit 0
fi

# Detect type and scope
commit_type=$(detect_type "$changed_files")
commit_scope=$(detect_scope "$changed_files")

log_info "Commit type: ${commit_type}"
if [ -n "$commit_scope" ]; then
    log_info "Scope: ${commit_scope}"
fi

# Generate or use custom message
if [ "$AMEND" = true ]; then
    if [ -n "$CUSTOM_MESSAGE" ]; then
        commit_message="$CUSTOM_MESSAGE"
    else
        # Reuse last commit message but update co-author
        last_message=$(git log -1 --format=%B)
        commit_message="${last_message}"
        if ! echo "$commit_message" | grep -q "Co-Authored-By: Claude"; then
            commit_message+=""
            commit_message+="Co-Authored-By: Claude <noreply@anthropic.com>"
        fi
    fi

    log_info "Amending last commit..."
else
    commit_message=$(generate_message "$commit_type" "$commit_scope" "$changed_files")
fi

# Display commit message
echo
echo -e "${CYAN}📝 Commit message:${NC}"
echo "----------------------------------------"
echo "$commit_message"
echo "----------------------------------------"
echo

# Confirm (optional - could add --confirm flag)
# read -p "Continue? [Y/n] " -n 1 -r
# echo
# if [[ $REPLY =~ ^[Nn]$ ]]; then
#     log_warning "Aborted by user"
#     exit 1
# fi

# Commit
if [ "$AMEND" = true ]; then
    git commit --amend -m "$commit_message"
else
    git commit -m "$commit_message"
fi

log_success "Changes committed"

# Get commit hash
commit_hash=$(git rev-parse --short HEAD)
log_info "Commit: ${commit_hash}"

# Push
if [ "$NO_PUSH" = false ]; then
    # Check if remote exists
    if ! git remote | grep -q origin; then
        log_error "No remote repository configured"
        echo "Run: git remote add origin <repository-url>"
        exit 1
    fi

    # Get remote branch
    remote_branch=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "origin/$(get_branch)")

    log_info "Pushing to ${remote_branch}..."

    if git push; then
        log_success "Pushed to ${remote_branch}"
    else
        log_error "Push failed"
        echo
        echo "Possible issues:"
        echo "  • Remote has new commits (run: git pull --rebase)"
        echo "  • Authentication required"
        echo "  • Network connectivity"
        exit 1
    fi
else
    log_info "Skipping push (--no-push flag)"
fi

echo
print_header "✨ Done!"

# Show status
echo "Current branch: $(get_branch)"
echo "Latest commit: ${commit_hash}"
if [ "$NO_PUSH" = false ]; then
    echo "Remote: $(git config --get remote.origin.url)"
fi
echo
