# Enhanced Claude Code Workflow

This document outlines the improved workflow for automatically checking and fixing GitHub Actions CI failures.

## 🔄 New Automated Workflow

### 1. After Creating PR - Automatic CI Check
```bash
# Immediately after creating PR, check CI status
gh pr checks <PR_NUMBER>
gh pr view <PR_NUMBER> --json statusCheckRollup
```

### 2. If CI Fails - Automatic Error Retrieval
```bash
# Get the failed job logs
gh run view <RUN_ID> --log-failed

# Or get specific job logs
gh api repos/OWNER/REPO/actions/runs/RUN_ID/jobs
```

### 3. Auto-Fix Common Issues
- **Linting Issues**: Run `uv run ruff check . --fix` and commit
- **Type Issues**: Run `uv run mypy .` and fix reported issues
- **Test Failures**: Analyze test output and fix issues
- **Build Issues**: Check dependencies and configuration

### 4. Commit and Push Fixes
```bash
git add .
git commit -m "fix: resolve CI failures"
git push origin <branch_name>
```

### 5. Re-check CI Status
```bash
# Wait for new CI run and check again
gh pr checks <PR_NUMBER>
```

## 🛠️ Implementation Example

When I create a PR, I will now:

1. **Create PR** as usual
2. **Immediately check CI status** using `gh pr checks`
3. **If failures detected**:
   - Fetch error logs automatically
   - Analyze and fix issues
   - Commit fixes and push
   - Re-check CI status
4. **Repeat until all checks pass**

## 📋 Workflow Commands

### Check PR CI Status
```bash
gh pr checks <PR_NUMBER>
```

### Get Failed Job Details
```bash
gh run view <RUN_ID> --log-failed
```

### Get Specific Job Logs
```bash
gh api repos/nyasuto/chirpy/actions/runs/<RUN_ID>/jobs
```

### Auto-fix Code Quality Issues
```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy .
```

## 🎯 Benefits

- **Proactive**: Catches and fixes CI failures immediately
- **Autonomous**: Reduces manual intervention required
- **Efficient**: Faster feedback loop for development
- **Reliable**: Ensures all PRs pass CI before review

## 📝 Future Enhancements

- Monitor CI status in real-time
- Intelligent error analysis and fixing
- Automated retry mechanisms
- Better error reporting and logging

This workflow addresses issue #15 by making CI failure handling automatic and proactive.