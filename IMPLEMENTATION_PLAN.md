# GitLab MCP Server Implementation Plan

## Overview

This document outlines the implementation plan for adding GitLab REST API integration to the Kepler MCP server. The plan is organized into phases, starting with core functionality and progressively adding more advanced features.

---

## Phase 1: Foundation & Core Project Operations

### 1.1 Configuration Extension

Extend `config.py` to add GitLab-specific settings:

```python
# New fields to add to Config model
gitlab_url: str = "https://gitlab.com"  # Base GitLab instance URL
gitlab_api_version: str = "v4"          # API version
gitlab_token: SecretStr | None = None   # Personal Access Token (alternative to OAuth)
gitlab_default_project_id: str | None = None  # Optional default project
gitlab_default_group_id: str | None = None    # Optional default group
```

### 1.2 GitLab API Client

Create `src/kepler_mcp_gitlab/gitlab/client.py`:

- Async HTTP client using `httpx`
- Automatic pagination handling
- Rate limiting integration
- Error handling with custom exceptions
- Auth header injection via `AuthStrategy`

### 1.3 Core Project Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_projects` | `GET /projects` | List accessible projects with filtering |
| `get_project` | `GET /projects/:id` | Get project details |
| `search_projects` | `GET /projects?search=` | Search projects by name/path |
| `get_project_languages` | `GET /projects/:id/languages` | Get programming language breakdown |

**File:** `src/kepler_mcp_gitlab/tools/projects.py`

---

## Phase 2: Issues & Merge Requests

### 2.1 Issue Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_issues` | `GET /projects/:id/issues` | List project issues |
| `get_issue` | `GET /projects/:id/issues/:iid` | Get issue details |
| `create_issue` | `POST /projects/:id/issues` | Create new issue |
| `update_issue` | `PUT /projects/:id/issues/:iid` | Update issue (title, description, labels, assignee, state) |
| `add_issue_comment` | `POST /projects/:id/issues/:iid/notes` | Add comment to issue |
| `list_issue_comments` | `GET /projects/:id/issues/:iid/notes` | List issue comments |
| `close_issue` | `PUT /projects/:id/issues/:iid` | Close an issue |
| `reopen_issue` | `PUT /projects/:id/issues/:iid` | Reopen an issue |

**File:** `src/kepler_mcp_gitlab/tools/issues.py`

### 2.2 Merge Request Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_merge_requests` | `GET /projects/:id/merge_requests` | List MRs with filtering |
| `get_merge_request` | `GET /projects/:id/merge_requests/:iid` | Get MR details |
| `create_merge_request` | `POST /projects/:id/merge_requests` | Create new MR |
| `update_merge_request` | `PUT /projects/:id/merge_requests/:iid` | Update MR properties |
| `merge_merge_request` | `PUT /projects/:id/merge_requests/:iid/merge` | Merge an MR |
| `approve_merge_request` | `POST /projects/:id/merge_requests/:iid/approve` | Approve an MR |
| `list_mr_comments` | `GET /projects/:id/merge_requests/:iid/notes` | List MR comments |
| `add_mr_comment` | `POST /projects/:id/merge_requests/:iid/notes` | Add MR comment |
| `get_mr_changes` | `GET /projects/:id/merge_requests/:iid/changes` | Get MR diff |
| `list_mr_discussions` | `GET /projects/:id/merge_requests/:iid/discussions` | List MR discussion threads |
| `resolve_mr_discussion` | `PUT /projects/:id/merge_requests/:iid/discussions/:id` | Resolve/unresolve thread |

**File:** `src/kepler_mcp_gitlab/tools/merge_requests.py`

---

## Phase 3: Repository & Code Operations

### 3.1 Repository Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_branches` | `GET /projects/:id/repository/branches` | List repository branches |
| `get_branch` | `GET /projects/:id/repository/branches/:branch` | Get branch details |
| `create_branch` | `POST /projects/:id/repository/branches` | Create new branch |
| `delete_branch` | `DELETE /projects/:id/repository/branches/:branch` | Delete a branch |
| `list_tags` | `GET /projects/:id/repository/tags` | List repository tags |
| `create_tag` | `POST /projects/:id/repository/tags` | Create new tag |
| `compare_branches` | `GET /projects/:id/repository/compare` | Compare two refs |

**File:** `src/kepler_mcp_gitlab/tools/branches.py`

### 3.2 File & Commit Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_repository_tree` | `GET /projects/:id/repository/tree` | Browse repository files/dirs |
| `get_file` | `GET /projects/:id/repository/files/:path` | Get file content (base64) |
| `get_file_raw` | `GET /projects/:id/repository/files/:path/raw` | Get raw file content |
| `create_file` | `POST /projects/:id/repository/files/:path` | Create new file |
| `update_file` | `PUT /projects/:id/repository/files/:path` | Update existing file |
| `delete_file` | `DELETE /projects/:id/repository/files/:path` | Delete a file |
| `get_file_blame` | `GET /projects/:id/repository/files/:path/blame` | Get file blame info |
| `list_commits` | `GET /projects/:id/repository/commits` | List commits |
| `get_commit` | `GET /projects/:id/repository/commits/:sha` | Get commit details |
| `get_commit_diff` | `GET /projects/:id/repository/commits/:sha/diff` | Get commit diff |
| `cherry_pick_commit` | `POST /projects/:id/repository/commits/:sha/cherry_pick` | Cherry-pick commit |

**File:** `src/kepler_mcp_gitlab/tools/repository.py`

---

## Phase 4: CI/CD Operations

### 4.1 Pipeline Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_pipelines` | `GET /projects/:id/pipelines` | List project pipelines |
| `get_pipeline` | `GET /projects/:id/pipelines/:id` | Get pipeline details |
| `get_latest_pipeline` | `GET /projects/:id/pipelines/latest` | Get latest pipeline |
| `create_pipeline` | `POST /projects/:id/pipeline` | Trigger new pipeline |
| `retry_pipeline` | `POST /projects/:id/pipelines/:id/retry` | Retry failed jobs |
| `cancel_pipeline` | `POST /projects/:id/pipelines/:id/cancel` | Cancel pipeline |
| `get_pipeline_variables` | `GET /projects/:id/pipelines/:id/variables` | Get pipeline variables |
| `get_pipeline_test_report` | `GET /projects/:id/pipelines/:id/test_report` | Get test results |

**File:** `src/kepler_mcp_gitlab/tools/pipelines.py`

### 4.2 Job Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_jobs` | `GET /projects/:id/jobs` | List project jobs |
| `list_pipeline_jobs` | `GET /projects/:id/pipelines/:id/jobs` | List jobs in pipeline |
| `get_job` | `GET /projects/:id/jobs/:id` | Get job details |
| `get_job_log` | `GET /projects/:id/jobs/:id/trace` | Get job log output |
| `retry_job` | `POST /projects/:id/jobs/:id/retry` | Retry a job |
| `cancel_job` | `POST /projects/:id/jobs/:id/cancel` | Cancel a job |
| `play_job` | `POST /projects/:id/jobs/:id/play` | Trigger manual job |

**File:** `src/kepler_mcp_gitlab/tools/jobs.py`

---

## Phase 5: Groups, Users & Search

### 5.1 Group Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_groups` | `GET /groups` | List accessible groups |
| `get_group` | `GET /groups/:id` | Get group details |
| `list_group_projects` | `GET /groups/:id/projects` | List projects in group |
| `list_group_members` | `GET /groups/:id/members` | List group members |
| `list_subgroups` | `GET /groups/:id/subgroups` | List subgroups |

**File:** `src/kepler_mcp_gitlab/tools/groups.py`

### 5.2 User Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `get_current_user` | `GET /user` | Get authenticated user info |
| `list_users` | `GET /users` | List/search users |
| `get_user` | `GET /users/:id` | Get user details |

**File:** `src/kepler_mcp_gitlab/tools/users.py`

### 5.3 Search Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `search_global` | `GET /search` | Search across GitLab instance |
| `search_project` | `GET /projects/:id/search` | Search within project |
| `search_group` | `GET /groups/:id/search` | Search within group |

Supported scopes: `projects`, `issues`, `merge_requests`, `milestones`, `users`, `commits`, `blobs`, `notes`

**File:** `src/kepler_mcp_gitlab/tools/search.py`

---

## Phase 6: Labels, Milestones & Organization

### 6.1 Label Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_labels` | `GET /projects/:id/labels` | List project labels |
| `create_label` | `POST /projects/:id/labels` | Create new label |
| `update_label` | `PUT /projects/:id/labels/:id` | Update label |
| `delete_label` | `DELETE /projects/:id/labels/:id` | Delete label |

**File:** `src/kepler_mcp_gitlab/tools/labels.py`

### 6.2 Milestone Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_milestones` | `GET /projects/:id/milestones` | List project milestones |
| `get_milestone` | `GET /projects/:id/milestones/:id` | Get milestone details |
| `create_milestone` | `POST /projects/:id/milestones` | Create milestone |
| `update_milestone` | `PUT /projects/:id/milestones/:id` | Update milestone |
| `list_milestone_issues` | `GET /projects/:id/milestones/:id/issues` | List issues in milestone |
| `list_milestone_merge_requests` | `GET /projects/:id/milestones/:id/merge_requests` | List MRs in milestone |

**File:** `src/kepler_mcp_gitlab/tools/milestones.py`

---

## Phase 7: Releases & Deployments

### 7.1 Release Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_releases` | `GET /projects/:id/releases` | List project releases |
| `get_release` | `GET /projects/:id/releases/:tag_name` | Get release details |
| `create_release` | `POST /projects/:id/releases` | Create new release |
| `update_release` | `PUT /projects/:id/releases/:tag_name` | Update release |
| `delete_release` | `DELETE /projects/:id/releases/:tag_name` | Delete release |

**File:** `src/kepler_mcp_gitlab/tools/releases.py`

### 7.2 Environment & Deployment Tools

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_environments` | `GET /projects/:id/environments` | List environments |
| `get_environment` | `GET /projects/:id/environments/:id` | Get environment details |
| `stop_environment` | `POST /projects/:id/environments/:id/stop` | Stop environment |
| `list_deployments` | `GET /projects/:id/deployments` | List deployments |
| `get_deployment` | `GET /projects/:id/deployments/:id` | Get deployment details |

**File:** `src/kepler_mcp_gitlab/tools/deployments.py`

---

## Phase 8: Advanced Features (Optional/Premium)

### 8.1 Protected Branches

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_protected_branches` | `GET /projects/:id/protected_branches` | List protected branches |
| `protect_branch` | `POST /projects/:id/protected_branches` | Protect a branch |
| `unprotect_branch` | `DELETE /projects/:id/protected_branches/:name` | Unprotect branch |

### 8.2 Project Access Tokens

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `list_access_tokens` | `GET /projects/:id/access_tokens` | List project tokens |
| `create_access_token` | `POST /projects/:id/access_tokens` | Create token |
| `revoke_access_token` | `DELETE /projects/:id/access_tokens/:id` | Revoke token |

### 8.3 Approval Rules (Premium)

| Tool Name | API Endpoint | Description |
|-----------|--------------|-------------|
| `get_approval_state` | `GET /projects/:id/merge_requests/:iid/approval_state` | Get MR approval state |
| `list_approval_rules` | `GET /projects/:id/approval_rules` | List project approval rules |

**File:** `src/kepler_mcp_gitlab/tools/advanced.py`

---

## Implementation Architecture

### Directory Structure

```
src/kepler_mcp_gitlab/
├── gitlab/
│   ├── __init__.py
│   ├── client.py          # Async GitLab API client
│   ├── exceptions.py      # GitLab-specific exceptions
│   └── pagination.py      # Pagination helpers
├── tools/
│   ├── __init__.py
│   ├── base.py            # (existing) Tool utilities
│   ├── health.py          # (existing) Health tools
│   ├── info.py            # (existing) Info tools
│   ├── projects.py        # Phase 1
│   ├── issues.py          # Phase 2
│   ├── merge_requests.py  # Phase 2
│   ├── branches.py        # Phase 3
│   ├── repository.py      # Phase 3
│   ├── pipelines.py       # Phase 4
│   ├── jobs.py            # Phase 4
│   ├── groups.py          # Phase 5
│   ├── users.py           # Phase 5
│   ├── search.py          # Phase 5
│   ├── labels.py          # Phase 6
│   ├── milestones.py      # Phase 6
│   ├── releases.py        # Phase 7
│   └── deployments.py     # Phase 7
└── ...
```

### Tool Registration Pattern

Each tool module will export a `register_*_tools(app, config, client)` function:

```python
# Example: tools/projects.py
def register_project_tools(app: Any, config: Config, client: GitLabClient) -> None:
    @app.tool()
    async def list_projects(
        search: str | None = None,
        visibility: str | None = None,
        owned: bool = False,
        membership: bool = False,
        per_page: int = 20,
    ) -> list[dict[str, Any]]:
        """List GitLab projects accessible to the authenticated user."""
        return await client.get_projects(
            search=search,
            visibility=visibility,
            owned=owned,
            membership=membership,
            per_page=per_page,
        )
```

### Updated application.py

```python
def register_application_tools(app: Any, config: Config) -> None:
    from kepler_mcp_gitlab.gitlab.client import GitLabClient
    from kepler_mcp_gitlab.tools.projects import register_project_tools
    from kepler_mcp_gitlab.tools.issues import register_issue_tools
    from kepler_mcp_gitlab.tools.merge_requests import register_merge_request_tools
    # ... more imports

    # Create shared client (lazy initialization)
    client = GitLabClient(config)

    # Register all tool modules
    register_project_tools(app, config, client)
    register_issue_tools(app, config, client)
    register_merge_request_tools(app, config, client)
    # ... more registrations

    logger.info("GitLab tools registered")
```

---

## Testing Strategy

### Unit Tests

- Mock `httpx` responses using `respx`
- Test each tool function in isolation
- Test pagination handling
- Test error scenarios (404, 401, 500, rate limits)

### Integration Tests (Optional)

- Use GitLab test instance or personal projects
- Mark with `@pytest.mark.integration`
- Skip in CI unless credentials provided

### Test File Structure

```
tests/
├── gitlab/
│   ├── test_client.py
│   ├── test_pagination.py
│   └── test_exceptions.py
├── tools/
│   ├── test_projects.py
│   ├── test_issues.py
│   ├── test_merge_requests.py
│   └── ...
```

---

## Configuration Examples

### Environment Variables

```bash
export KEPLER_MCP_GITLAB_URL="https://gitlab.com"
export KEPLER_MCP_GITLAB_TOKEN="glpat-xxxxxxxxxxxx"
export KEPLER_MCP_GITLAB_DEFAULT_PROJECT_ID="12345"
```

### Config File (YAML)

```yaml
app_name: "kepler-mcp-gitlab"
gitlab_url: "https://gitlab.example.com"
gitlab_token: "glpat-xxxxxxxxxxxx"
gitlab_default_project_id: "my-org/my-project"
log_level: "INFO"
```

### OAuth Configuration (SSE Mode)

```yaml
transport_mode: "sse"
oauth_user_auth_enabled: true
oauth_authorization_url: "https://gitlab.com/oauth/authorize"
oauth_token_url: "https://gitlab.com/oauth/token"
oauth_client_id: "your-app-id"
oauth_client_secret: "your-app-secret"
oauth_scope: "api read_api read_user"
oauth_redirect_uri: "http://localhost:8000/oauth/callback"
oauth_userinfo_url: "https://gitlab.com/api/v4/user"
```

---

## Priority & Effort Estimates

| Phase | Priority | Complexity | Tools Count |
|-------|----------|------------|-------------|
| Phase 1: Foundation | **Critical** | Medium | 4 |
| Phase 2: Issues & MRs | **Critical** | High | 19 |
| Phase 3: Repository | **High** | High | 17 |
| Phase 4: CI/CD | **High** | Medium | 15 |
| Phase 5: Groups/Users/Search | Medium | Medium | 11 |
| Phase 6: Labels/Milestones | Medium | Low | 10 |
| Phase 7: Releases/Deployments | Low | Medium | 10 |
| Phase 8: Advanced | Low | Low | 6 |

**Total: ~92 tools**

---

## Recommended Implementation Order

1. **Start with Phase 1** - Establish GitLab client and basic project operations
2. **Add Phase 2** - Issues and MRs are core developer workflows
3. **Add Phase 4** - CI/CD is highly valuable for automation
4. **Add Phase 3** - Repository operations for code review workflows
5. **Add remaining phases** based on user feedback

---

## Success Criteria

- [ ] All Phase 1-2 tools implemented and tested
- [ ] 80%+ test coverage maintained
- [ ] Type checking passes (mypy strict)
- [ ] Security scanning passes (bandit/safety)
- [ ] Documentation updated
- [ ] Example configurations provided
- [ ] Docker image builds successfully
