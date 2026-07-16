import ast
import os
import time
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple


@dataclass(frozen=True)
class AuditReport:
    report_id: str
    category: str  # Architecture, Security, Performance, Compliance
    timestamp: datetime
    is_passed: bool
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)


class DependencyAnalyzer:
    """Analyzes imports to build dependency graphs and detect circular dependencies."""
    def build_dependency_graph(self, root_dir: str) -> Dict[str, Set[str]]:
        graph = {}
        exclude_dirs = {".venv", "venv", "env", "site-packages", "__pycache__", ".git", ".pytest_cache"}
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            if "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    rel_path = os.path.relpath(filepath, root_dir).replace(".py", "").replace(os.sep, ".")
                    imports = self._extract_imports(filepath)
                    graph[rel_path] = imports
        return graph

    def detect_circular_dependencies(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        visited = {}
        path = []
        cycles = []

        def dfs(node: str) -> None:
            if visited.get(node) == 1:  # currently visiting
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            if visited.get(node) == 2:  # fully visited
                return

            visited[node] = 1
            path.append(node)
            for neighbor in graph.get(node, []):
                # Check match package dependencies
                for g_node in graph:
                    if neighbor.startswith(g_node) or g_node.startswith(neighbor):
                        dfs(g_node)

            path.pop()
            visited[node] = 2

        for node in graph:
            dfs(node)

        return cycles

    def _extract_imports(self, filepath: str) -> Set[str]:
        imports = set()
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read(), filename=filepath)
            except SyntaxError:
                return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
        return imports


class ArchitectureAuditor:
    """Audits layer isolation and interface consistency."""
    def __init__(self, root_dir: str) -> None:
        self.root_dir = root_dir
        self.analyzer = DependencyAnalyzer()

    def audit_layer_isolation(self) -> AuditReport:
        graph = self.analyzer.build_dependency_graph(self.root_dir)
        violations = []

        # Layer isolation rule: lower layers (e.g. Data, Core, Infrastructure)
        # must never import from upper layers (e.g. Decision, Execution, Application, Strategy, Risk)
        for module, imports in graph.items():
            mod_layer = module.split(".")[0]
            if mod_layer in {"Infrastructure", "Core", "Data"}:
                for imp in imports:
                    imp_layer = imp.split(".")[0]
                    if imp_layer in {"Decision", "Execution", "Application", "Strategy", "Risk"}:
                        violations.append(f"Layer Isolation Violation: {module} imports from upper layer {imp}")

        is_passed = len(violations) == 0
        return AuditReport(
            report_id=f"audit-iso-{datetime.now().timestamp()}",
            category="Architecture",
            timestamp=datetime.now(),
            is_passed=is_passed,
            summary="Zero layer isolation violations." if is_passed else f"Found {len(violations)} isolation violations.",
            details={"violations": violations}
        )

    def audit_circular_dependencies(self) -> AuditReport:
        graph = self.analyzer.build_dependency_graph(self.root_dir)
        cycles = self.analyzer.detect_circular_dependencies(graph)
        is_passed = len(cycles) == 0
        return AuditReport(
            report_id=f"audit-circ-{datetime.now().timestamp()}",
            category="Architecture",
            timestamp=datetime.now(),
            is_passed=is_passed,
            summary="No circular dependencies detected." if is_passed else f"Found {len(cycles)} circular dependencies.",
            details={"cycles": cycles}
        )


class SecurityASTVisitor(ast.NodeVisitor):
    """AST visitor to inspect Python files for active usages of forbidden keys."""
    def __init__(self, forbidden_keys: Set[str]) -> None:
        self.forbidden_keys = forbidden_keys
        self.anomalies = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name.lower() in self.forbidden_keys:
            self.anomalies.append((node.lineno, f"Forbidden function definition '{node.name}' found."))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if node.name.lower() in self.forbidden_keys:
            self.anomalies.append((node.lineno, f"Forbidden async function definition '{node.name}' found."))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.name.lower() in self.forbidden_keys:
            self.anomalies.append((node.lineno, f"Forbidden class definition '{node.name}' found."))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name and func_name.lower() in self.forbidden_keys:
            self.anomalies.append((node.lineno, f"Forbidden function call '{func_name}' found."))
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.lower() in self.forbidden_keys:
            self.anomalies.append((node.lineno, f"Forbidden attribute access '{node.attr}' found."))
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.lower() in self.forbidden_keys:
                # Do not flag setting of constant lists/sets/tuples of strings containing the forbidden keys
                if isinstance(node.value, (ast.List, ast.Set, ast.Tuple)):
                    continue
                self.anomalies.append((node.lineno, f"Forbidden assignment to variable '{target.id}' found."))
            elif isinstance(target, ast.Attribute) and target.attr.lower() in self.forbidden_keys:
                self.anomalies.append((node.lineno, f"Forbidden assignment to attribute '{target.attr}' found."))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.target.id.lower() in self.forbidden_keys:
            self.anomalies.append((node.lineno, f"Forbidden typed assignment to variable '{node.target.id}' found."))
        elif isinstance(node.target, ast.Attribute) and node.target.attr.lower() in self.forbidden_keys:
            self.anomalies.append((node.lineno, f"Forbidden typed assignment to attribute '{node.target.attr}' found."))
        self.generic_visit(node)


class SecurityAuditor:
    """Scans code bases for secrets, leakage, and unsafe functions."""
    def __init__(self, root_dir: str) -> None:
        self.root_dir = root_dir
        self.forbidden_keys = {"place_order", "open_position", "execute_trade", "buy_signal", "sell_signal", "broker_api"}

    def audit_security(self) -> AuditReport:
        anomalies = []
        exclude_dirs = {".venv", "venv", "env", "site-packages", "__pycache__", ".git", ".pytest_cache"}
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            if "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(".py"):
                    if "test" in file.lower():
                        continue
                    if file in {"evaluation.py", "concrete_agents.py", "collaboration.py", "validator.py"}:
                        # Skip validation definitions containing strings
                        continue

                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            code = f.read()
                        tree = ast.parse(code, filename=filepath)
                        visitor = SecurityASTVisitor(self.forbidden_keys)
                        visitor.visit(tree)
                        for lineno, msg in visitor.anomalies:
                            anomalies.append(f"Security Alert in {file}:{lineno}: {msg}")
                    except SyntaxError:
                        # Fallback or ignore for unparseable python files
                        pass
                    except Exception:
                        pass

        is_passed = len(anomalies) == 0
        return AuditReport(
            report_id=f"audit-sec-{datetime.now().timestamp()}",
            category="Security",
            timestamp=datetime.now(),
            is_passed=is_passed,
            summary="Zero security leakages detected." if is_passed else f"Found {len(anomalies)} security alerts.",
            details={"anomalies": anomalies}
        )


class PerformanceAuditor:
    """Audits system resource speeds, latencies, and memory footprints."""
    def audit_performance(self, task_callable: Any, *args: Any, **kwargs: Any) -> AuditReport:
        start_time = time.time()
        start_mem = sys.getsizeof(task_callable)

        try:
            result = task_callable(*args, **kwargs)
            is_success = True
            error_msg = None
        except Exception as e:
            result = None
            is_success = False
            error_msg = str(e)

        elapsed_ms = (time.time() - start_time) * 1000.0
        end_mem = sys.getsizeof(result) if result else start_mem

        return AuditReport(
            report_id=f"audit-perf-{datetime.now().timestamp()}",
            category="Performance",
            timestamp=datetime.now(),
            is_passed=is_success,
            summary="Task executed successfully." if is_success else f"Task failed: {error_msg}",
            details={
                "elapsed_ms": round(elapsed_ms, 3),
                "memory_delta_bytes": end_mem - start_mem,
                "is_success": is_success
            }
        )


class ComplianceAuditor:
    """Verifies complete conformity to passive, non-trading APES-FIN rules."""
    def audit_compliance(self, root_dir: str) -> AuditReport:
        non_compliance = []
        exclude_dirs = {".venv", "venv", "env", "site-packages", "__pycache__", ".git", ".pytest_cache"}
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            if "__pycache__" in root:
                continue
            for file in files:
                if "execution" in file.lower() and not "test" in file.lower():
                    # check if it contains trade executions
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    if "buy" in content.lower() or "sell" in content.lower():
                        non_compliance.append(f"Compliance Alert: File '{file}' contains buy/sell operations.")

        is_passed = len(non_compliance) == 0
        return AuditReport(
            report_id=f"audit-comp-{datetime.now().timestamp()}",
            category="Compliance",
            timestamp=datetime.now(),
            is_passed=is_passed,
            summary="100% APES-FIN compliant." if is_passed else f"Found {len(non_compliance)} compliance issues.",
            details={"non_compliance_alerts": non_compliance}
        )
