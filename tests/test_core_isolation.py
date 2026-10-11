"""Kriteria penerimaan: core/ tidak boleh bergantung pada kerangka web atau ORM."""
import ast
from pathlib import Path

FORBIDDEN_ROOTS = {"flask", "flask_sqlalchemy", "flask_login", "flask_wtf", "sqlalchemy", "wtforms"}
CORE_DIR = Path(__file__).resolve().parent.parent / "core"


def imported_roots(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_core_has_python_files():
    assert list(CORE_DIR.rglob("*.py"))


def test_core_does_not_import_web_or_orm():
    offenders = {
        str(path.relative_to(CORE_DIR)): sorted(imported_roots(path) & FORBIDDEN_ROOTS)
        for path in CORE_DIR.rglob("*.py")
        if imported_roots(path) & FORBIDDEN_ROOTS
    }
    assert offenders == {}


def test_core_does_not_read_sensitive_tables():
    # Nama tabel sensitif hanya boleh muncul sebagai daftar pengecualian/dokumentasi.
    source = (CORE_DIR / "sql_dump_parser.py").read_text(encoding="utf-8")
    assert "ALLOWED_TABLES" in source
    assert 'tables["apptb_user"]' not in source and 'tables["apptb_log"]' not in source
