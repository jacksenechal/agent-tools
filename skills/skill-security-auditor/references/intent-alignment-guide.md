# Intent Alignment Guide

Maps common skill categories to expected capability profiles. Use during Step 4 to calibrate expectations: what's normal for this type of skill, what's suspicious, and what safeguards to recommend.

**These categories are illustrative, not exhaustive.** Many skills span categories or don't fit neatly. For uncategorized skills, apply the core alignment question directly: do the capabilities support the stated intent? The categories provide calibration shortcuts, not rigid gates.

*Framework informed by antigravity/security-auditor (sickn33) threat modeling methodology.*

## Formatter / Linter

**Purpose**: Transform or validate code/text format without changing semantics.

**Reasonable capabilities**: Read files, Write files (in-place or to output), Grep for patterns. May need Bash for running external formatters (prettier, black, eslint).

**Suspicious for this category**: Network access, credential access, reading files outside the project, executing downloaded code, modifying shell configuration.

**Safeguards**: None typically needed. If it writes files, verify it only modifies target files.

## Developer Tool (test, build, CI/CD)

**Purpose**: Run tests, build projects, manage development workflows.

**Reasonable capabilities**: Read, Write, Bash (running test suites, build commands, package managers). May need network for downloading dependencies or reporting to CI services. May access environment variables for configuration.

**Suspicious for this category**: Accessing SSH keys or cloud credentials unrelated to build, uploading source code to undisclosed endpoints, modifying files outside the project directory, persistence mechanisms.

**Safeguards**: Verify network endpoints are disclosed. Confirm dependency installation commands are standard. Check that environment variable access is limited to build-relevant vars.

## Deployment Tool

**Purpose**: Deploy applications to servers, cloud services, or container registries.

**Reasonable capabilities**: Read project files, Bash (docker, kubectl, terraform, cloud CLIs), network access to cloud providers, access to deployment credentials (disclosed).

**Suspicious for this category**: Accessing credentials for services not mentioned in docs, uploading data to endpoints other than the deployment target, modifying local system configuration, accessing other projects.

**Safeguards**: Confirm deployment targets match documentation. Verify credential access is scoped to stated services. Recommend dry-run mode. Confirm destructive deployments (overwriting production).

## Security / Audit Tool

**Purpose**: Scan for vulnerabilities, audit configurations, assess security posture.

**Reasonable capabilities**: Read broadly (needs to inspect many files), Bash (running security scanners), may need network for CVE databases or vulnerability feeds. May access system configuration files for audit.

**Suspicious for this category**: Writing to files outside reports/output, uploading scanned data to undisclosed endpoints, modifying the files it's scanning, credential access beyond what's being audited, persistence mechanisms.

**Safeguards**: Verify scan results stay local unless upload is disclosed. Confirm it's read-only on scanned targets. Check that network access is limited to known security databases.

## System Admin / Cleanup

**Purpose**: Manage system resources, clean temporary files, configure environments.

**Reasonable capabilities**: Read and Write system files (disclosed scope), Bash for system commands, may need elevated permissions for specific operations (disclosed).

**Suspicious for this category**: Network access (cleanup doesn't need internet), accessing credentials unrelated to system config, scope that extends beyond stated targets, modifying other users' files.

**Safeguards**: Confirm destructive operations have confirmation prompts. Verify scope is limited to stated targets. Recommend dry-run mode. Check for backup/undo capability.

## Destructive by Design

**Purpose**: Delete files, clear caches, purge data, where destruction IS the stated intent.

**Reasonable capabilities**: Find and delete operations within disclosed scope. Bash for recursive operations. May need broad file system access within scope.

**Suspicious for this category**: Scope exceeding what's described (says "delete node_modules" but also deletes .git), network access (deletion doesn't need internet), credential access, targeting paths not mentioned in documentation.

**Safeguards**: Confirmation prompt showing exact targets before execution. Dry-run mode listing what would be deleted. Scope enforcement (default to current directory, require explicit flag for broader scope). Audit log of deletions.

## Privacy-Sensitive (credentials, secrets)

**Purpose**: Manage secrets, rotate keys, configure authentication, where handling sensitive data IS the stated purpose.

**Reasonable capabilities**: Access credential files and secret stores (disclosed and scoped). May need network to communicate with secret management services (Vault, AWS Secrets Manager). Bash for CLI tools.

**Suspicious for this category**: Accessing credentials for services not mentioned, uploading secrets to undisclosed endpoints, storing credentials in plaintext, logging secret values, accessing credentials it doesn't need to manage.

**Safeguards**: Verify secrets are never logged or written to unprotected files. Confirm network endpoints for secret management are disclosed and legitimate. Check that credential access is scoped to managed services only.

## Network-Active (API client, webhook)

**Purpose**: Interact with external APIs, manage webhooks, fetch remote data.

**Reasonable capabilities**: Network operations to disclosed endpoints. May read local config files for API keys. Bash for curl/httpie operations. May write response data locally.

**Suspicious for this category**: Contacting endpoints not documented, uploading local files not specified by user, accessing credentials for services not mentioned, reading file system broadly, persistence mechanisms.

**Safeguards**: Verify all endpoints are disclosed in documentation. Confirm data sent matches user intent. Check that API key access is limited to relevant services. Recommend reviewing request/response data.
