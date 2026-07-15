import ast
import os
import sys
from typing import List, Tuple, Set


class ComplianceASTVisitor(ast.NodeVisitor):
    """
    AST visitor that traverses code trees to distinguish between safe string
    constants/definitions and actual active function definitions or execution calls.
    """

    def __init__(self, filename: str, forbidden_keywords: Set[str]) -> None:
        self.filename = filename
        self.forbidden_keywords = forbidden_keywords
        self.violations: List[Tuple[int, str, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Reject defining any function with a forbidden name."""
        if node.name in self.forbidden_keywords:
            self.violations.append((
                node.lineno,
                "Function Definition Violation",
                f"Defines forbidden function '{node.name}'."
            ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Reject calling any function/attribute with a forbidden name."""
        func_name = self._get_call_name(node.func)
        if func_name in self.forbidden_keywords:
            self.lineno = getattr(node, 'lineno', 1)
            self.violations.append((
                self.lineno,
                "Active Call Violation",
                f"Executes forbidden call to '{func_name}'."
            ))
        self.generic_visit(node)

    def _get_call_name(self, node: ast.AST) -> str:
        """Helper to resolve call names from identifiers or attribute chains."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ""


class ComplianceScanner:
    """
    Context-aware APES-FIN compliance verifier using Abstract Syntax Trees.
    """

    def __init__(self) -> None:
        self.forbidden_keywords = {
            "place_order",
            "create_order",
            "send_transaction",
            "execute_trade",
            "buy_signal",
            "sell_signal"
        }
        # Allowed locations where defensive/validator code is safe and permitted
        self.allowed_directories = [
            os.path.normpath("src/Application/Audit"),
            os.path.normpath("src/Application/Validation"),
            os.path.normpath("src/Infrastructure/Configuration")
        ]

    def is_path_allowed(self, filepath: str) -> bool:
        """Checks if a file is located in a defensive/security configuration location."""
        norm_path = os.path.normpath(filepath)
        for allowed_dir in self.allowed_directories:
            if norm_path.startswith(allowed_dir):
                return True
        return False

    def scan_file(self, filepath: str) -> List[Tuple[int, str, str]]:
        """Parses and audits a python source file."""
        if self.is_path_allowed(filepath):
            # Safe defensive directory, skip AST inspection
            return []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source, filename=filepath)
            visitor = ComplianceASTVisitor(filepath, self.forbidden_keywords)
            visitor.visit(tree)
            return visitor.violations
        except SyntaxError as e:
            # Report syntax errors as critical scan failures
            return [(e.lineno or 1, "Syntax Error", f"Failed to parse: {str(e)}")]
        except Exception as e:
            return [(1, "Scan Error", f"Error scanning file: {str(e)}")]

    def scan_directory(self, root_dir: str) -> List[Tuple[str, int, str, str]]:
        """Scans all python files in the directory recursively."""
        all_violations = []
        for root, _, files in os.walk(root_dir):
            # Skip tests, build artifacts, venv, and git directories
            if any(part in root.split(os.sep) for part in ("tests", "venv", ".git", "deploy", "__pycache__")):
                continue

            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    violations = self.scan_file(full_path)
                    for line, vtype, msg in violations:
                        all_violations.append((full_path, line, vtype, msg))

        return all_violations


def main():
    scanner = ComplianceScanner()
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "src"

    print(f"[Compliance Scanner] Auditing target directory: '{target_dir}'...")
    violations = scanner.scan_directory(target_dir)

    if violations:
        print(f"\n[SECURITY REJECTION] {len(violations)} APES-FIN Compliance Violations Found:")
        for path, line, vtype, msg in violations:
            print(f"  File: {path}:{line} | [{vtype}] {msg}")
        sys.exit(1)

    print("[SUCCESS] All source directories passed APES-FIN security compliance verification.")
    sys.exit(0)


if __name__ == "__main__":
    main()
