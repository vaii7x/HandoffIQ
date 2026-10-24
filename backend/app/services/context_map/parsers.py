"""Heuristic static parsers for HTML, CSS, JavaScript, TypeScript, and JSON files."""

import json
import re
from typing import List, Set, Tuple

from app.models.context_map import ParsedSymbol, SymbolType

# Regex patterns for JavaScript/TypeScript/React
RE_JS_FUNC = re.compile(
    r"^(?:\s*export\s+(?:default\s+)?)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)",
    re.MULTILINE,
)
RE_JS_VAR_FUNC = re.compile(
    r"^(?:\s*export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z0-9_$]+)\s*=>",
    re.MULTILINE,
)
RE_JS_VAR_FUNC_EXPR = re.compile(
    r"^(?:\s*export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?function",
    re.MULTILINE,
)
RE_JS_CLASS = re.compile(
    r"^(?:\s*export\s+(?:default\s+)?)?class\s+([A-Za-z0-9_$]+)(?:\s+extends\s+([A-Za-z0-9_$.]+))?",
    re.MULTILINE,
)
RE_JS_IMPORT_FROM = re.compile(
    r"""(?:^|\n)\s*import\s+(?:[\w*\s{},$]+from\s+)?['"]([^'"]+)['"]""",
    re.MULTILINE,
)
RE_JS_REQUIRE = re.compile(
    r"""require\(\s*['"]([^'"]+)['"]\s*\)""",
)
RE_JS_EXPORT_NAMED = re.compile(
    r"""(?:^|\n)\s*export\s*\{\s*([^}]+)\s*\}""",
    re.MULTILINE,
)
RE_JS_EXPORT_DECL = re.compile(
    r"""(?:^|\n)\s*export\s+(?:default\s+)?(?:const|let|var|function|class)\s+([A-Za-z0-9_$]+)""",
    re.MULTILINE,
)

# Regex patterns for CSS
RE_CSS_RULES = re.compile(
    r"""([^{}]+)\s*\{""",
    re.MULTILINE,
)
RE_CSS_CLASS = re.compile(r"""\.([a-zA-Z0-9_\-]+)""")
RE_CSS_ID = re.compile(r"""#([a-zA-Z0-9_\-]+)""")
RE_CSS_IMPORT = re.compile(r"""@import\s+(?:url\(['"]?([^'")]+)['"]?\)|['"]([^'"]+)['"]);""")

# Regex patterns for HTML
RE_HTML_SCRIPT = re.compile(r"""<script[^>]+src=['"]([^'"]+)['"]""", re.IGNORECASE)
RE_HTML_LINK_CSS = re.compile(
    r"""<link[^>]+(?:rel=['"]stylesheet['"][^>]+href=['"]([^'"]+)['"]|href=['"]([^'"]+)['"][^>]+rel=['"]stylesheet['"])""",
    re.IGNORECASE,
)
RE_HTML_IDS = re.compile(r"""\bid=['"]([^'"]+)['"]""", re.IGNORECASE)
RE_HTML_CLASSES = re.compile(r"""\bclass=['"]([^'"]+)['"]""", re.IGNORECASE)


def detect_language(extension: str) -> str:
    """Map file extension to canonical language tag."""
    ext = extension.lower()
    mapping = {
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".js": "javascript",
        ".jsx": "react_jsx",
        ".ts": "typescript",
        ".tsx": "react_tsx",
        ".json": "json",
    }
    return mapping.get(ext, "unknown")


def parse_js_ts_symbols(
    content: str, extension: str
) -> Tuple[List[ParsedSymbol], List[str], List[str]]:
    """Extract functions, React components, classes, imports, and exports from JS/TS code using regex heuristics.

    Returns:
        (symbols, imports, exports)
    """
    symbols: List[ParsedSymbol] = []
    imports: Set[str] = set()
    exports: Set[str] = set()

    is_react = extension.lower() in {".jsx", ".tsx"} or "react" in content.lower()
    lines = content.splitlines()

    # 1. Imports
    for match in RE_JS_IMPORT_FROM.finditer(content):
        specifier = match.group(1).strip()
        if specifier:
            imports.add(specifier)

    for match in RE_JS_REQUIRE.finditer(content):
        specifier = match.group(1).strip()
        if specifier:
            imports.add(specifier)

    # 2. Exports
    for match in RE_JS_EXPORT_DECL.finditer(content):
        exports.add(match.group(1).strip())

    for match in RE_JS_EXPORT_NAMED.finditer(content):
        raw_names = match.group(1).split(",")
        for item in raw_names:
            name = item.strip().split(" as ")[0].strip()
            if name:
                exports.add(name)

    # 3. Line-by-line function, component, and class extraction
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "/*", "*")):
            continue

        # Regular functions
        fn_match = RE_JS_FUNC.match(line)
        if fn_match:
            fn_name = fn_match.group(1)
            is_comp = is_react and bool(fn_name and fn_name[0].isupper())
            symbols.append(
                ParsedSymbol(
                    name=fn_name,
                    symbol_type=SymbolType.component if is_comp else SymbolType.function,
                    line_number=idx,
                    is_exported=fn_name in exports or "export" in line,
                    parsing_method="regex_heuristic",
                    details={"is_async": "async" in line},
                )
            )
            continue

        # Arrow functions or function expressions
        var_fn_match = RE_JS_VAR_FUNC.match(line) or RE_JS_VAR_FUNC_EXPR.match(line)
        if var_fn_match:
            fn_name = var_fn_match.group(1)
            is_comp = is_react and bool(fn_name and fn_name[0].isupper())
            symbols.append(
                ParsedSymbol(
                    name=fn_name,
                    symbol_type=SymbolType.component if is_comp else SymbolType.function,
                    line_number=idx,
                    is_exported=fn_name in exports or "export" in line,
                    parsing_method="regex_heuristic",
                    details={"is_arrow": "=>" in line},
                )
            )
            continue

        # Classes
        class_match = RE_JS_CLASS.match(line)
        if class_match:
            cls_name = class_match.group(1)
            super_cls = class_match.group(2)
            symbols.append(
                ParsedSymbol(
                    name=cls_name,
                    symbol_type=SymbolType.class_def,
                    line_number=idx,
                    is_exported=cls_name in exports or "export" in line,
                    parsing_method="regex_heuristic",
                    details={"extends": super_cls} if super_cls else {},
                )
            )

    return symbols, sorted(list(imports)), sorted(list(exports))


def parse_css_symbols(content: str) -> Tuple[List[ParsedSymbol], List[str]]:
    """Extract CSS class selectors, ID selectors, and import rules.

    Returns:
        (symbols, imports)
    """
    symbols: List[ParsedSymbol] = []
    imports: Set[str] = set()

    # CSS @import
    for match in RE_CSS_IMPORT.finditer(content):
        ref = match.group(1) or match.group(2)
        if ref:
            imports.add(ref.strip())

    seen_selectors: Set[str] = set()
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("/*"):
            continue

        # Extract class selectors
        for match in RE_CSS_CLASS.finditer(line):
            cls_name = f".{match.group(1)}"
            if cls_name not in seen_selectors:
                seen_selectors.add(cls_name)
                symbols.append(
                    ParsedSymbol(
                        name=cls_name,
                        symbol_type=SymbolType.css_selector,
                        line_number=idx,
                        parsing_method="regex_heuristic",
                    )
                )

        # Extract ID selectors
        for match in RE_CSS_ID.finditer(line):
            id_name = f"#{match.group(1)}"
            if id_name not in seen_selectors:
                seen_selectors.add(id_name)
                symbols.append(
                    ParsedSymbol(
                        name=id_name,
                        symbol_type=SymbolType.css_selector,
                        line_number=idx,
                        parsing_method="regex_heuristic",
                    )
                )

    return symbols, sorted(list(imports))


def parse_html_symbols(content: str) -> Tuple[List[ParsedSymbol], List[str]]:
    """Extract script references, stylesheets, and major DOM elements from HTML.

    Returns:
        (symbols, imports)
    """
    symbols: List[ParsedSymbol] = []
    imports: Set[str] = set()

    for match in RE_HTML_SCRIPT.finditer(content):
        src = match.group(1).strip()
        if src:
            imports.add(src)

    for match in RE_HTML_LINK_CSS.finditer(content):
        href = (match.group(1) or match.group(2) or "").strip()
        if href:
            imports.add(href)

    # Line by line IDs and classes
    seen_ids: Set[str] = set()
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        for id_match in RE_HTML_IDS.finditer(line):
            dom_id = id_match.group(1).strip()
            if dom_id and dom_id not in seen_ids:
                seen_ids.add(dom_id)
                symbols.append(
                    ParsedSymbol(
                        name=f"#{dom_id}",
                        symbol_type=SymbolType.css_selector,
                        line_number=idx,
                        parsing_method="regex_heuristic",
                    )
                )

    return symbols, sorted(list(imports))


def parse_json_symbols(content: str) -> Tuple[List[ParsedSymbol], List[str]]:
    """Parse JSON file, extracting dependencies if package.json.

    Returns:
        (symbols, imports)
    """
    symbols: List[ParsedSymbol] = []
    imports: List[str] = []

    try:
        data = json.loads(content)
        if isinstance(data, dict):
            deps = data.get("dependencies", {})
            dev_deps = data.get("devDependencies", {})
            if isinstance(deps, dict):
                for dep_name in deps.keys():
                    imports.append(dep_name)
                    symbols.append(
                        ParsedSymbol(
                            name=dep_name,
                            symbol_type=SymbolType.variable,
                            line_number=1,
                            parsing_method="json_parser",
                            details={"type": "dependency", "version": str(deps[dep_name])},
                        )
                    )
            if isinstance(dev_deps, dict):
                for dep_name in dev_deps.keys():
                    imports.append(dep_name)
    except Exception:
        pass

    return symbols, imports
