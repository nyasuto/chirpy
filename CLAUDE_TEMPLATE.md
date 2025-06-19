# CLAUDE.md Template

This template provides universal best practices for Claude Code (claude.ai/code) when working with code repositories.

## 🔨 Rule Evolution Process

When receiving user instructions that should become permanent standards:

1. Ask: "これを標準のルールにしますか？" (Should this become a standard rule?)
2. If YES, add the new rule to CLAUDE.md
3. Apply as standard rule going forward

This process enables continuous improvement of project rules.

## 🛠️ Development Tools

**Use the Makefile for all development tasks!** Standardize development workflows through a comprehensive Makefile.

Essential Makefile targets to implement:
- **Quick start:** `make help` - Show all available commands
- **Code quality:** `make quality` - Run all quality checks (lint + format + type-check)
- **Auto-fix:** `make quality-fix` - Auto-fix issues where possible
- **Development:** `make dev` - Quick setup and run cycle
- **PR preparation:** `make pr-ready` - Ensure code is ready for submission
- **Git hooks:** `make git-hooks` - Setup pre-commit hooks

### Individual Quality Targets
- `make lint` - Run linting
- `make format` - Format code
- `make type-check` - Type checking
- `make test` - Run tests
- `make test-cov` - Run tests with coverage

### Development Lifecycle
- `make install` - Install dependencies
- `make build` - Build package
- `make clean` - Clean artifacts
- `make env-info` - Show environment information

## GitHub Issue Management Rules

### Required Label System
All issues MUST have both Priority and Type labels:

#### Priority Labels
- `priority: critical` - Urgent (app crashes, security issues)
- `priority: high` - Important (core features, major bugs)
- `priority: medium` - Standard (improvements, minor bugs)
- `priority: low` - Future (nice-to-have features, docs)

#### Type Labels
- `type: feature` - New functionality
- `type: bug` - Bug fixes
- `type: enhancement` - Existing feature improvements
- `type: docs` - Documentation
- `type: test` - Testing related
- `type: refactor` - Code refactoring
- `type: ci/cd` - CI/CD pipeline
- `type: security` - Security related

### Label Application Examples
```
title: "Add retry mechanism for API calls"
labels: ["priority: high", "type: enhancement"]

title: "Fix crash when database is missing"  
labels: ["priority: critical", "type: bug"]

title: "Add web interface"
labels: ["priority: low", "type: feature"]
```

## Git Workflow and Branch Management

### Core Git Rules
- **NEVER commit directly to main branch**
- Always create feature branches for changes
- Create Pull Requests for ALL changes, regardless of size
- All commits must follow conventional commit format
- Include issue references in PR descriptions: `Closes #X`

### Branch Naming Convention
Use descriptive, consistent branch names:
- Feature: `feat/issue-X-feature-name`
- Bug fix: `fix/issue-X-description`
- Hotfix: `hotfix/X-description`
- Test: `test/X-description`
- Docs: `docs/X-description`
- CI/CD: `cicd/X-description`

### Commit Message Format
```
<type>: <description>

<optional body explaining what and why>

<optional footer with issue references>
🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Commit Types:** feat, fix, docs, style, refactor, test, chore, ci

### Required Development Workflow
1. Create feature branch from main
2. Make changes
3. **Run quality checks before commit:**
   - `make quality` (comprehensive checks)
   - OR `make quality-fix` (auto-fix + check)
4. Commit only after all checks pass
5. Push branch to remote
6. Create Pull Request with descriptive title and body
7. Wait for CI checks to pass
8. Merge via GitHub interface (not locally)

### Pre-commit Hook Setup
- Run `make git-hooks` to setup automatic quality checks
- Prevents committing code that fails quality standards
- Saves time by catching issues early

## Code Quality Standards

### Quality Check Integration
Quality checks should be:
- **Automated** through Makefile targets
- **Consistent** across all development environments
- **Enforceable** through pre-commit hooks and CI/CD
- **Fast** to encourage frequent use

### Essential Quality Tools
- **Linting:** Language-specific linters (ruff for Python, eslint for JS, etc.)
- **Formatting:** Code formatters (black/ruff for Python, prettier for JS, etc.)
- **Type Checking:** Static type analysis (mypy for Python, TypeScript, etc.)
- **Testing:** Unit and integration tests with coverage reporting

### CI/CD Integration
- All quality checks must pass in CI before merge
- Separate CI jobs for different check types (lint, test, type-check)
- Coverage reporting and tracking
- Security scanning where applicable

## Testing Standards

### Test Organization
- Unit tests for individual components
- Integration tests for system interactions
- Mocking external dependencies to avoid platform issues
- Clear test naming: `test_<function>_<scenario>_<expected_result>`

### Coverage Requirements
- Set minimum coverage thresholds
- Track coverage trends over time
- Exclude generated files and non-testable code
- Focus on critical path coverage

### CI Test Environment
- Mock platform-specific dependencies for cross-platform compatibility
- Use consistent test databases/fixtures
- Parallel test execution where possible
- Clear error reporting and debugging information

## Error Handling and Debugging

### Logging Standards
- Structured logging with appropriate levels
- Context-rich error messages
- Avoid logging sensitive information
- Performance-conscious logging (lazy evaluation)

### Error Recovery
- Graceful degradation for non-critical failures
- Clear error messages for users
- Retry mechanisms with exponential backoff
- Circuit breaker patterns for external services

## Documentation Standards

### Code Documentation
- Clear docstrings for public APIs
- Type hints for better IDE support
- README with setup and usage instructions
- CHANGELOG for version tracking

### Process Documentation
- This CLAUDE.md file for development standards
- Contributing guidelines for external contributors
- Architecture decision records (ADRs) for major decisions
- Troubleshooting guides for common issues

## Security Considerations

### Secrets Management
- Never commit secrets to version control
- Use environment variables for configuration
- Implement secret rotation policies
- Scan for accidentally committed secrets

### Dependency Management
- Regular dependency updates
- Security vulnerability scanning
- Pin versions for reproducible builds
- Audit new dependencies before adoption

## Performance Monitoring

### Resource Management
- Memory usage monitoring
- Disk space management (cache cleanup, log rotation)
- Network request optimization
- Database query performance

### Caching Strategies
- Implement cache size limits
- Age-based cache expiration
- LRU (Least Recently Used) cleanup algorithms
- Cache performance metrics

## Additional Best Practices

### Environment Configuration
- Support for multiple environments (dev, staging, prod)
- Environment-specific configuration files
- Graceful handling of missing configuration
- Configuration validation on startup

### Monitoring and Observability
- Health check endpoints
- Metrics collection and reporting
- Alert thresholds for critical issues
- Performance profiling capabilities

### Backup and Recovery
- Regular data backups
- Backup verification procedures
- Disaster recovery plans
- Point-in-time recovery capabilities

---

## Usage Instructions

1. Copy this template to your project as `CLAUDE.md`
2. Customize the project-specific sections (remove this template header)
3. Add your project's specific requirements and constraints
4. Update the Makefile to include all mentioned targets
5. Setup CI/CD pipelines to enforce the quality standards
6. Train team members on the workflow and standards

This template provides a solid foundation for consistent, high-quality software development practices across projects.