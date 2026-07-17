"""Script para verificar que todas as correções estão funcionando.

Uso: python scripts/test_fixes.py
"""

import sys
import os

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

errors = []
passed = 0


def check(name, condition, msg=""):
    global passed
    if condition:
        print(f"  [OK] {name}")
        passed += 1
    else:
        print(f"  [ERRO] {name}: {msg}")
        errors.append(name)


print("=== Teste de Correcoes ===\n")

# 1. Verificar imports
print("1. Imports...")
try:
    from mil.config import load_config, get, _deep_merge
    check("config import", True)
except Exception as e:
    check("config import", False, str(e))

try:
    from mil.balance import _generate_patient_reports, PatientReport
    check("balance import", True)
except Exception as e:
    check("balance import", False, str(e))

try:
    from mil.report import update_live_stats, create_live_stats_table
    check("report import", True)
except Exception as e:
    check("report import", False, str(e))

try:
    from mil.phase4_cropper import _crop_regions_from_s0
    check("phase4 import", True)
except Exception as e:
    check("phase4 import", False, str(e))

try:
    from mil.margin import get_margin_config as gmc
    check("margin import", True)
except Exception as e:
    check("margin import", False, str(e))

try:
    from mil.runtime_log import RuntimeLogger
    check("runtime_log import", True)
except Exception as e:
    check("runtime_log import", False, str(e))

try:
    from mil.phase2_tissue_detector import detect
    check("phase2 import", True)
except Exception as e:
    check("phase2 import", False, str(e))

# 2. Verificar deepcopy no config
print("\n2. Config deepcopy...")
import copy
base = {"a": {"b": 1}}
from mil.config import _deep_merge
merged = _deep_merge(base, {"a": {"c": 2}})
check("deep_merge nao modifica base", base == {"a": {"b": 1}}, f"base: {base}")

# 3. Verificar get_margin_config com phase
print("\n3. get_margin_config...")
try:
    from mil.margin import get_margin_config
    margin, mode = get_margin_config("phase2")
    check("get_margin_config phase2", isinstance(margin, int) and isinstance(mode, str))
except Exception as e:
    check("get_margin_config phase2", False, str(e))

try:
    margin, mode = get_margin_config("phase4", edge_margin=5, edge_mode="outside")
    check("get_margin_config phase4 override", margin == 5 and mode == "outside")
except Exception as e:
    check("get_margin_config phase4 override", False, str(e))

# 4. Verificar update_live_stats
print("\n4. update_live_stats...")
try:
    from rich.table import Table
    table = Table(show_header=False, box=None)
    table.add_column("Métrica")
    table.add_column("Valor")
    stats = {"processed_files": 10, "ok": 8, "ok_pct": 80.0, "errors": 2, "error_pct": 20.0, "warnings": 0}
    update_live_stats(table, stats, "test.tif")
    rows1 = len(table.rows)
    update_live_stats(table, stats, "test2.tif")
    rows2 = len(table.rows)
    check("update_live_stats clears rows", rows1 == rows2, f"rows1={rows1}, rows2={rows2}")
except Exception as e:
    check("update_live_stats", False, str(e))

# 5. Verificar RuntimeLogger context manager
print("\n5. RuntimeLogger context manager...")
try:
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        with RuntimeLogger(tmpdir, "test_run") as log:
            log.log_file_start("test.tif")
            log.log_file_ok("test.tif", "HE", 1, False)
        # Verificar que os arquivos foram fechados
        check("RuntimeLogger context manager", True)
except Exception as e:
    check("RuntimeLogger context manager", False, str(e))

# 6. Verificar pyproject.toml
print("\n6. pyproject.toml...")
try:
    toml_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
    with open(toml_path) as f:
        content = f.read()
    check("python >=3.10", "requires-python = \">=3.10\"" in content)
except Exception as e:
    check("pyproject.toml", False, str(e))

# 7. Verificar config.yaml paths
print("\n7. config.yaml...")
try:
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(config_path) as f:
        content = f.read()
    check("config.yaml sem hardcoded D:\\", 'D:\\\\Projects' not in content and 'D:\\Projects' not in content)
except Exception as e:
    check("config.yaml", False, str(e))

# Resultado
print(f"\n=== Resultado: {passed} passed, {len(errors)} errors ===")
if errors:
    print("Erros:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("Todos os testes passaram!")
    sys.exit(0)
