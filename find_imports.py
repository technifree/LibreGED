import ast
import sys
from pathlib import Path
from importlib.util import find_spec

# === Liste des modules standards à ignorer ===
import sysconfig
stdlib_modules = set(sys.builtin_module_names)
stdlib_modules |= set(sysconfig.get_paths().keys())

EXCLUDE = stdlib_modules | {
    "config", "views", "database", "tests",
    "PySide6", "shiboken6", "main", "__future__",
    "__main__", "__pypy__", "_frozen_importlib", "_frozen_importlib_external"
}

project_root = Path(__file__).parent.resolve()
found = set()

for py_file in project_root.rglob("*.py"):
    if "venv" in str(py_file):
        continue
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    except Exception:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                top = n.name.split(".")[0]
                if top not in EXCLUDE:
                    found.add(top)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            top = node.module.split(".")[0]
            if top not in EXCLUDE:
                found.add(top)

# Vérifier que le module est bien installable
valid = [mod for mod in sorted(found) if find_spec(mod) is not None]

print("# Modules réels à inclure dans Nuitka :")
for mod in valid:
    print(f"--include-module={mod} \\")
