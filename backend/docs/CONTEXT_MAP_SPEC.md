# ContextMap Service Specification & Limitations

## Overview
**ContextMap** is HandoffIQ's static workspace indexing and context retrieval engine. It indexes local project files across HTML, CSS, JavaScript, TypeScript, and React without executing code, and deterministically retrieves relevant source context, component symbols, and test suites for canonical requirements.

---

## 1. Supported Languages & Extensions

| Extension | Language Tag | Parsing Strategy | Discovered Elements |
| :--- | :--- | :--- | :--- |
| `.js` | `javascript` | Regex Heuristic | Functions, classes, `import` / `require`, `export` |
| `.jsx` | `react_jsx` | Regex Heuristic | React components (capitalized), hooks, functions, imports |
| `.ts` | `typescript` | Regex Heuristic | Typed functions, classes, interfaces/types (heuristic), imports |
| `.tsx` | `react_tsx` | Regex Heuristic | Typed React components, functions, classes, imports |
| `.css` | `css` | Regex Heuristic | Class selectors (`.btn`), ID selectors (`#root`), `@import` |
| `.html`, `.htm` | `html` | Regex Heuristic | `<script src>`, `<link rel="stylesheet">`, DOM IDs and classes |
| `.json` | `json` | Structured JSON | Package dependencies (`package.json`), devDependencies, scripts |

---

## 2. Safe Workspace Access & Security Boundaries

ContextMap enforces strict security invariants before any file access:

1. **Workspace Containment**:
   - Every file access is resolved against the canonical, absolute workspace root (`Path.resolve()`).
   - Any attempt to resolve paths containing `..` or escaping outside the workspace raises `PathTraversalError` (HTTP 400).
   - Symbolic links pointing outside the workspace are detected and rejected.

2. **Prohibited Secrets & Credentials**:
   - The scanner automatically excludes secret and credential patterns:
     - Environment files: `.env`, `.env.*`
     - Private keys & certificates: `*.pem`, `*.key`, `*.pfx`, `*.p12`
     - SSH keys: `id_rsa`, `id_ed25519`, `id_dsa`, `id_ecdsa`
     - Service accounts & credentials: `credentials.json`, `service-account*.json`, `client_secret*.json`
     - Files with names containing `secret`, `token`, `password`, or `credential`.
   - Direct requests to access secret files raise `WorkspaceSecurityError` (HTTP 403).

3. **Excluded Directories**:
   - The scanner avoids descending into:
     - `node_modules`, `.git`, `.venv`, `venv`, `env`, `dist`, `build`, `.next`, `coverage`, `.cache`, `__pycache__`, `.turbo`.

4. **File Size Limits**:
   - Configurable size threshold (`DEFAULT_MAX_FILE_SIZE_BYTES`, default 512 KB).
   - Files exceeding the threshold are skipped during bulk indexing and recorded under `oversized_files_count`.
   - Direct retrieval of oversized files raises `OversizedFileError` (HTTP 422).

5. **Pure Static Inspection**:
   - Source code is strictly parsed as text; no runtime execution, `eval`, or Node.js process spawning occurs.

---

## 3. Analysis Limitations & Heuristic Disclosures

> [!NOTE]
> ContextMap version 1 utilizes static regex-based heuristics rather than a full semantic compiler / AST toolchain (e.g. Babel, TypeScript Compiler API, or Tree-sitter).

### Known Limitations:
1. **Dynamic Imports**:
   - Statically analyzes string literals in `import ... from '...'` and `require('...')`. Dynamic imports (`import(variable)`) or computed paths are not resolved.
2. **Aliased Path Resolution**:
   - Resolves relative subpaths (e.g., `./Button` -> `./Button.jsx` or `./Button/index.js`). Custom bundler path aliases (`@/components/*` or `tsconfig.json` `compilerOptions.paths`) require future alias-resolver configuration.
3. **Selector Specificity & Shadow DOM**:
   - CSS selectors are parsed as tokens; full CSS cascade calculation, CSS modules hashing, or CSS-in-JS styled components are detected via keyword heuristics.
4. **Attribution**:
   - All extracted symbols are explicitly labeled with `parsing_method: "regex_heuristic"` to distinguish them from full AST parser output.

---

## 4. Deterministic Context Retrieval & Ranking

When querying context for a task's requirements (`POST /api/tasks/{task_id}/context-map`), the retrieval engine:

1. **Tokenizes Requirements**: Extracts meaningful keywords from `Requirement.original_text` and `description` (filtering common English stop words).
2. **Deterministic Scoring**:
   - **Filename match**: +5.0 points if keyword appears in filename/path.
   - **Symbol match**: +4.0 points if keyword matches a function, component, or class name.
   - **Content match**: +1.0 point per matched keyword in source lines.
3. **Associated Tests**:
   - Discovers test files matching `*.test.*` or `*.spec.*`.
   - Automatically links corresponding test suites to relevant source files via `test_target` relationships.
4. **Compact Packaging**:
   - Emits structured `ContextPackage` with top-ranked files, matched symbols, reasons, and focused outlines without discarding original sources.

---

## 5. Token Accounting Transparency

To provide trustworthy metrics without misleading claims:

1. **Token Count Type**:
   - Emits `token_count_type: "estimated"`.
   - Calculated locally using standard code heuristic:
     $$\text{estimated\_tokens} = \left\lceil \frac{\text{total\_characters}}{3.8} \right\rceil$$
   - Marked explicitly as estimated; never flagged as `"provider_reported"` unless measured directly from an LLM API.
2. **Token Savings**:
   - Token savings percentage is calculated **strictly** when a valid baseline exists:
     $$\text{token\_savings\_percent} = \frac{\text{baseline\_tokens} - \text{estimated\_tokens}}{\text{baseline\_tokens}} \times 100\%$$
   - When no baseline is provided, the full project indexed token count is used as the comparative baseline.
   - If no project index exists or baseline is zero, `token_savings_percent` evaluates to `None`.

---

## 6. API Reference

### 1. `POST /api/context-map/index`
Indexes a local workspace directory and returns discovered files, symbols, test suites, and relationships.

**Request**:
```json
{
  "workspace_path": "c:/Users/username/projects/my-app",
  "max_file_size_bytes": 524288,
  "force_refresh": false
}
```

**Response (HTTP 200)**:
```json
{
  "workspace_path": "C:\\Users\\username\\projects\\my-app",
  "total_files": 12,
  "total_size_bytes": 48200,
  "total_lines": 1420,
  "files": [
    {
      "relative_path": "src/components/Button.jsx",
      "extension": ".jsx",
      "language": "react_jsx",
      "size_bytes": 1024,
      "line_count": 45,
      "is_test": false,
      "symbols": [
        {
          "name": "Button",
          "symbol_type": "component",
          "line_number": 4,
          "is_exported": true,
          "parsing_method": "regex_heuristic"
        }
      ],
      "imports": ["react", "../styles/main.css"],
      "exports": ["Button"]
    }
  ],
  "relationships": [
    {
      "source_file": "src/components/Button.test.jsx",
      "target_file": "src/components/Button.jsx",
      "relationship_type": "test_target",
      "raw_reference": "test suite for src/components/Button.jsx"
    }
  ],
  "test_files": ["src/components/Button.test.jsx"],
  "excluded_files_count": 4,
  "oversized_files_count": 0,
  "limitations_notice": "Static regex-based heuristic analysis for HTML, CSS, JS, and React..."
}
```

### 2. `GET /api/context-map/index?workspace_path={path}`
Retrieves cached index summary for a previously analyzed workspace.

### 3. `GET /api/context-map/file?workspace_path={path}&relative_path={rel_path}`
Safely retrieves file content and line metrics, validating directory containment and blocking secrets.

### 4. `POST /api/tasks/{task_id}/context-map`
Retrieves a ranked, compact context package with associated symbols, tests, and token accounting for task requirements.
