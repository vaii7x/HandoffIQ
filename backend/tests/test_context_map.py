"""Comprehensive tests for ContextMap project indexing, safety guards, and context retrieval."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.errors import (
    OversizedFileError,
    PathTraversalError,
    WorkspaceNotFoundError,
    WorkspaceSecurityError,
)
from app.main import app
from app.models.context_map import ProjectIndex, SymbolType
from app.models.requirement import Requirement, RequirementPriority, RequirementStatus
from app.models.task import Task, TaskStatus
from app.repositories.in_memory import InMemoryTaskRepository
from app.services.context_map.indexer import ProjectIndexerService
from app.services.context_map.parsers import (
    detect_language,
    parse_css_symbols,
    parse_html_symbols,
    parse_js_ts_symbols,
    parse_json_symbols,
)
from app.services.context_map.retriever import ContextRetrieverService
from app.services.context_map.scanner import SafeWorkspaceScanner

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixture: Sample HTML / CSS / React project workspace
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a realistic small HTML, CSS, JavaScript, and React workspace."""
    workspace = tmp_path / "sample_app"
    workspace.mkdir()

    # 1. package.json
    pkg_json = {
        "name": "sample-react-app",
        "version": "1.0.0",
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
        },
        "devDependencies": {
            "jest": "^29.5.0",
        },
    }
    (workspace / "package.json").write_text(json.dumps(pkg_json, indent=2), encoding="utf-8")

    # 2. public/index.html
    public_dir = workspace / "public"
    public_dir.mkdir()
    (public_dir / "index.html").write_text(
        """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Sample App</title>
    <link rel="stylesheet" href="../src/styles/main.css" />
  </head>
  <body>
    <div id="root"></div>
    <script src="../src/index.js"></script>
  </body>
</html>
""",
        encoding="utf-8",
    )

    # 3. src/styles/main.css
    src_dir = workspace / "src"
    src_dir.mkdir()
    styles_dir = src_dir / "styles"
    styles_dir.mkdir()
    (styles_dir / "main.css").write_text(
        """.btn {
  padding: 8px 16px;
  border-radius: 4px;
}

.btn-primary {
  background-color: blue;
  color: white;
}

#header {
  font-size: 24px;
}
""",
        encoding="utf-8",
    )

    # 4. src/components/Button.jsx
    comp_dir = src_dir / "components"
    comp_dir.mkdir()
    (comp_dir / "Button.jsx").write_text(
        """import React from 'react';
import '../styles/main.css';

export function Button({ label, onClick }) {
  return (
    <button className="btn btn-primary" onClick={onClick}>
      {label}
    </button>
  );
}

export const IconButton = ({ icon, onClick }) => {
  return <button onClick={onClick}>{icon}</button>;
};
""",
        encoding="utf-8",
    )

    # 5. src/components/Button.test.jsx
    (comp_dir / "Button.test.jsx").write_text(
        """import React from 'react';
import { Button } from './Button';

describe('Button component', () => {
  test('renders button label correctly', () => {
    // test logic
  });
});
""",
        encoding="utf-8",
    )

    # 6. src/App.jsx
    (src_dir / "App.jsx").write_text(
        """import React, { useState } from 'react';
import { Button } from './components/Button';

export default function App() {
  const [count, setCount] = useState(0);

  const handleIncrement = () => {
    setCount(count + 1);
  };

  return (
    <div>
      <h1 id="header">Counter</h1>
      <Button label="Increment" onClick={handleIncrement} />
    </div>
  );
}
""",
        encoding="utf-8",
    )

    # 7. Excluded directories and files
    node_modules = workspace / "node_modules" / "some-lib"
    node_modules.mkdir(parents=True)
    (node_modules / "index.js").write_text("module.exports = {};", encoding="utf-8")

    git_dir = workspace / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]", encoding="utf-8")

    (workspace / ".env").write_text("SECRET_KEY=12345", encoding="utf-8")
    (workspace / "credentials.json").write_text('{"private_key": "abc"}', encoding="utf-8")

    return workspace


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_language_detection():
    """Verify file extensions map to expected language tags."""
    assert detect_language(".html") == "html"
    assert detect_language(".css") == "css"
    assert detect_language(".js") == "javascript"
    assert detect_language(".jsx") == "react_jsx"
    assert detect_language(".ts") == "typescript"
    assert detect_language(".tsx") == "react_tsx"
    assert detect_language(".json") == "json"
    assert detect_language(".unknown") == "unknown"


def test_heuristic_parser_js_react():
    """Verify regex heuristic extractor identifies functions, components, classes, and imports."""
    code = """
import React, { useState } from 'react';
import { Helper } from './helper';
const local = require('./local');

export default function UserProfile({ userId }) {
  return <div>Profile</div>;
}

export const fetchUserData = async (id) => {
  return await fetch('/api');
};

class AuthManager extends BaseAuth {
  login() {}
}

export { local };
"""
    symbols, imports, exports = parse_js_ts_symbols(code, ".jsx")

    # Symbols check
    symbol_names = [s.name for s in symbols]
    assert "UserProfile" in symbol_names
    assert "fetchUserData" in symbol_names
    assert "AuthManager" in symbol_names

    # Check component distinction (capitalized UserProfile)
    user_prof = next(s for s in symbols if s.name == "UserProfile")
    assert user_prof.symbol_type == SymbolType.component
    assert user_prof.parsing_method == "regex_heuristic"

    # Check class extraction
    auth_mgr = next(s for s in symbols if s.name == "AuthManager")
    assert auth_mgr.symbol_type == SymbolType.class_def
    assert auth_mgr.details.get("extends") == "BaseAuth"

    # Imports check
    assert "react" in imports
    assert "./helper" in imports
    assert "./local" in imports

    # Exports check
    assert "UserProfile" in exports or any(s.is_exported for s in symbols if s.name == "UserProfile")


def test_heuristic_parser_css():
    """Verify CSS parser extracts class and ID selectors."""
    css = """
.card { border: 1px solid #ccc; }
.card-header { font-weight: bold; }
#main-nav { background: #333; }
"""
    symbols, imports = parse_css_symbols(css)
    names = [s.name for s in symbols]
    assert ".card" in names
    assert ".card-header" in names
    assert "#main-nav" in names
    assert all(s.parsing_method == "regex_heuristic" for s in symbols)


def test_safe_scanner_file_exclusion(sample_project: Path):
    """Verify node_modules, .git, and secrets like .env and credentials.json are excluded."""
    scanner = SafeWorkspaceScanner(str(sample_project))
    eligible_paths, excluded_count, oversized_count = scanner.scan_workspace()

    posix_paths = [str(p.relative_to(sample_project)).replace("\\", "/") for p in eligible_paths]

    # Eligible files present
    assert "package.json" in posix_paths
    assert "public/index.html" in posix_paths
    assert "src/styles/main.css" in posix_paths
    assert "src/components/Button.jsx" in posix_paths
    assert "src/components/Button.test.jsx" in posix_paths
    assert "src/App.jsx" in posix_paths

    # Excluded files absent
    assert not any("node_modules" in p for p in posix_paths)
    assert not any(".git" in p for p in posix_paths)
    assert ".env" not in posix_paths
    assert "credentials.json" not in posix_paths
    assert excluded_count >= 2


def test_path_traversal_rejection(sample_project: Path):
    """Verify directory traversal and access outside workspace are blocked."""
    scanner = SafeWorkspaceScanner(str(sample_project))

    with pytest.raises(PathTraversalError):
        scanner.resolve_safe_path("../outside.txt")

    with pytest.raises(PathTraversalError):
        scanner.resolve_safe_path("../../windows/system32/cmd.exe")


def test_secret_access_blocked(sample_project: Path):
    """Verify direct attempts to read credentials or secret files raise WorkspaceSecurityError."""
    scanner = SafeWorkspaceScanner(str(sample_project))

    with pytest.raises(WorkspaceSecurityError):
        scanner.resolve_safe_path(".env")

    with pytest.raises(WorkspaceSecurityError):
        scanner.resolve_safe_path("credentials.json")


def test_oversized_file_handling(tmp_path: Path):
    """Verify oversized files are skipped during scanning and raise OversizedFileError on direct read."""
    workspace = tmp_path / "oversized_ws"
    workspace.mkdir()

    small_file = workspace / "small.js"
    small_file.write_text("console.log('small');", encoding="utf-8")

    large_file = workspace / "large.js"
    # Create 20KB file
    large_file.write_text("x" * 20000, encoding="utf-8")

    # Scanner with 10KB max limit
    scanner = SafeWorkspaceScanner(str(workspace), max_file_size_bytes=10000)
    eligible_paths, excluded_count, oversized_count = scanner.scan_workspace()

    assert len(eligible_paths) == 1
    assert eligible_paths[0].name == "small.js"
    assert oversized_count == 1

    # Direct read of oversized file
    with pytest.raises(OversizedFileError):
        scanner.read_safe_file("large.js")


def test_empty_workspace(tmp_path: Path):
    """Verify indexing an empty directory succeeds with zero files."""
    empty_dir = tmp_path / "empty_ws"
    empty_dir.mkdir()

    indexer = ProjectIndexerService()
    index = indexer.index_workspace(str(empty_dir))

    assert index.total_files == 0
    assert index.total_size_bytes == 0
    assert index.total_lines == 0
    assert len(index.files) == 0


def test_nonexistent_workspace():
    """Verify indexing a non-existent path raises WorkspaceNotFoundError."""
    indexer = ProjectIndexerService()
    with pytest.raises(WorkspaceNotFoundError):
        indexer.index_workspace("c:/non_existent_workspace_path_12345")


def test_project_indexing_and_relationships(sample_project: Path):
    """Verify indexing discovers files, symbols, test files, and relationships."""
    indexer = ProjectIndexerService()
    index = indexer.index_workspace(str(sample_project), force_refresh=True)

    assert index.total_files == 6
    assert index.workspace_path == str(sample_project.resolve())
    assert "src/components/Button.test.jsx" in index.test_files

    # Check discovered relationships
    import_rels = [r for r in index.relationships if r.relationship_type in {"import", "css_reference"}]
    assert any(
        r.source_file == "src/App.jsx" and "Button" in r.target_file for r in import_rels
    )

    # Check test target relationship
    test_rels = [r for r in index.relationships if r.relationship_type == "test_target"]
    assert any(
        r.source_file == "src/components/Button.test.jsx"
        and r.target_file == "src/components/Button.jsx"
        for r in test_rels
    )


@pytest.mark.anyio
async def test_context_retrieval_and_ranking(sample_project: Path):
    """Verify requirements are matched to relevant files and associated tests with deterministic scoring."""
    indexer = ProjectIndexerService()
    index = indexer.index_workspace(str(sample_project), force_refresh=True)

    repo = InMemoryTaskRepository()
    task = Task(
        title="Button Component Task",
        original_request="Build accessible button with primary blue styling.",
    )
    await repo.create_task(task)

    req = Requirement(
        task_id=task.id,
        id="R001",
        description="Render Button component with btn-primary class and onClick handler.",
        original_text="Render Button component with btn-primary class and onClick handler.",
        priority=RequirementPriority.high,
        status=RequirementStatus.registered,
    )
    await repo.add_requirements(task.id, [req])

    retriever = ContextRetrieverService(task_repo=repo)
    package = await retriever.retrieve_context(
        task_id=task.id,
        project_index=index,
        requirement_ids=["R001"],
    )

    assert package.task_id == task.id
    assert len(package.canonical_requirements) == 1
    assert package.canonical_requirements[0].original_text == req.original_text

    # Button.jsx should rank near top because of Button component and keyword match
    matched_paths = [f.relative_path for f in package.matched_files]
    assert "src/components/Button.jsx" in matched_paths

    button_match = next(f for f in package.matched_files if f.relative_path == "src/components/Button.jsx")
    assert button_match.relevance_score > 0
    assert any("Button" in r for r in button_match.match_reasons)

    # Associated tests should automatically be detected
    assert "src/components/Button.test.jsx" in package.related_tests


@pytest.mark.anyio
async def test_token_accounting_estimates(sample_project: Path):
    """Verify token metrics are clearly marked as estimates and baseline comparisons work properly."""
    indexer = ProjectIndexerService()
    index = indexer.index_workspace(str(sample_project), force_refresh=True)

    repo = InMemoryTaskRepository()
    task = Task(
        title="Counter Task",
        original_request="Counter implementation in App.jsx",
    )
    await repo.create_task(task)
    req = Requirement(
        task_id=task.id,
        id="R001",
        description="Counter component in App.jsx",
        original_text="Counter component in App.jsx",
        priority=RequirementPriority.medium,
        status=RequirementStatus.registered,
    )
    await repo.add_requirements(task.id, [req])

    retriever = ContextRetrieverService(task_repo=repo)

    # 1. Without explicit baseline (compares with full project)
    package = await retriever.retrieve_context(
        task_id=task.id,
        project_index=index,
    )

    accounting = package.token_accounting
    assert accounting.total_characters > 0
    assert accounting.total_bytes > 0
    assert accounting.estimated_tokens > 0
    assert accounting.token_count_type == "estimated"  # Never provider_reported for local estimate
    assert accounting.full_project_estimated_tokens is not None
    assert accounting.full_project_estimated_tokens >= accounting.estimated_tokens
    assert accounting.token_savings_percent is not None
    assert 0.0 <= accounting.token_savings_percent <= 100.0

    # 2. With explicit baseline
    package_with_base = await retriever.retrieve_context(
        task_id=task.id,
        project_index=index,
        baseline_tokens=5000,
    )
    assert package_with_base.token_accounting.baseline_tokens == 5000
    assert package_with_base.token_accounting.token_savings_percent is not None


# ---------------------------------------------------------------------------
# API Route Tests
# ---------------------------------------------------------------------------

def test_api_index_workspace(sample_project: Path):
    """Verify POST /api/context-map/index endpoint indexes workspace and returns metadata."""
    response = client.post(
        "/api/context-map/index",
        json={"workspace_path": str(sample_project)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 6
    assert "src/components/Button.jsx" in [f["relative_path"] for f in data["files"]]
    assert "src/components/Button.test.jsx" in data["test_files"]


def test_api_get_cached_index(sample_project: Path):
    """Verify GET /api/context-map/index retrieves previously indexed workspace."""
    # Ensure indexed
    client.post("/api/context-map/index", json={"workspace_path": str(sample_project)})

    response = client.get(
        "/api/context-map/index",
        params={"workspace_path": str(sample_project)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 6


def test_api_safe_file_content(sample_project: Path):
    """Verify GET /api/context-map/file fetches content safely and blocks traversal."""
    # Safe access
    res = client.get(
        "/api/context-map/file",
        params={"workspace_path": str(sample_project), "relative_path": "src/styles/main.css"},
    )
    assert res.status_code == 200
    assert ".btn" in res.json()["content"]

    # Blocked traversal
    res_traversal = client.get(
        "/api/context-map/file",
        params={"workspace_path": str(sample_project), "relative_path": "../outside.txt"},
    )
    assert res_traversal.status_code == 400
    assert res_traversal.json()["error"]["code"] == "PATH_TRAVERSAL_DETECTED"

    # Blocked secret file
    res_secret = client.get(
        "/api/context-map/file",
        params={"workspace_path": str(sample_project), "relative_path": ".env"},
    )
    assert res_secret.status_code == 403
    assert res_secret.json()["error"]["code"] == "WORKSPACE_SECURITY_VIOLATION"


def test_api_task_context_retrieval(sample_project: Path):
    """Verify POST /api/tasks/{task_id}/context-map retrieves context package."""
    # 1. Create a task via API
    task_res = client.post(
        "/api/tasks",
        json={
            "title": "Button Component Task",
            "original_request": "Build accessible button component with test coverage.",
        },
    )
    assert task_res.status_code == 201
    task_id = task_res.json()["task"]["id"]

    # 2. Retrieve context package
    context_res = client.post(
        f"/api/tasks/{task_id}/context-map",
        json={
            "workspace_path": str(sample_project),
            "max_files": 5,
        },
    )
    assert context_res.status_code == 200
    pkg = context_res.json()
    assert pkg["task_id"] == task_id
    assert len(pkg["canonical_requirements"]) >= 1
    assert "token_accounting" in pkg
    assert pkg["token_accounting"]["token_count_type"] == "estimated"
