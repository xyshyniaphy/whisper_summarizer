---
name: git_push
description: Commit all changes with detailed message and push to remote repository. Analyzes git diff to generate meaningful commit messages following conventional commit format.
---

# git_push - Git Commit and Push Skill

## Purpose

Automates the git commit and push workflow with intelligent commit message generation:
- Analyzes all staged and unstaged changes
- Generates detailed commit messages following conventional commit format
- Automatically adds all changes to staging
- Commits with proper formatting
- Pushes to the remote repository

## When to Use

Use this skill when you need to:

```bash
# Commit and push all changes after completing work
/git_push

# After fixing bugs or adding features
/git_push

# After documentation updates
/git_push

# Quick commit before leaving/switching context
/git_push
```

## Input Parameters

### Optional
- `--no-push`: Commit changes but skip pushing to remote
- `-- amend`: Amend the last commit instead of creating new one
- `--message <msg>`: Use custom message instead of auto-generated
- `--type <type>`: Force commit type (feat, fix, docs, refactor, etc.)

## Commit Message Format

Follows conventional commit specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or modifications
- `chore`: Maintenance tasks
- `perf`: Performance improvements

### Example Generated Messages

```
feat(shared-api): add public DOCX download endpoint

- Add /api/shared/{share_token}/download-docx endpoint
- Generate DOCX from AI summary using python-docx
- Support Chinese fonts (Microsoft YaHei)
- Include RFC 2231 encoding for Japanese filenames

Fixes: 401 Unauthorized error when downloading DOCX from shared pages
```

```
docs(claude): update production debugging documentation

- Replace curl examples with Python urllib.request
- Server container uses python:3.12-slim (no curl installed)
- Add proper patterns for HTTP testing in production
```

## Output

### Console Output

```
========================================
Git Commit and Push
========================================

📊 Analyzing changes...

Modified files:
  • server/app/api/shared.py (+258 lines)
  • frontend/src/pages/SharedTranscription.tsx (+8 lines)
  • CLAUDE.md (+23 lines)

📝 Generated commit message:

feat(shared-api): add public download endpoints

[... full message ...]

✅ Changes staged
✅ Committed: abc1234
✅ Pushed to origin/main
```

## Error Handling

The skill handles common issues:

### Uncommitted Merge Conflicts
```
❌ ERROR: Uncommitted merge conflicts detected
Please resolve conflicts before running git_push
```

### No Remote Configured
```
❌ ERROR: No remote repository configured
Run: git remote add origin <repository-url>
```

### Push Rejected
```
❌ ERROR: Push rejected - remote has new commits
Run: git pull --rebase first
```

## Examples

### Basic Usage
```bash
/git_push
```

### Commit Without Pushing
```bash
/git_push --no-push
```

### Custom Message
```bash
/git_push --message "Fix shared page authentication"
```

### Force Specific Type
```bash
/git_push --type fix
```

## Implementation Notes

The skill intelligently:
- Detects file types and modifies commit scope
- Counts added/removed lines for summary
- Lists affected files in commit body
- Uses branch name to infer context
- Co-authors with Claude for attribution

## See Also

- [Conventional Commits](https://www.conventionalcommits.org/)
- [SCM:git - /sc:git](../../CLAUDE.md#git-operations)
