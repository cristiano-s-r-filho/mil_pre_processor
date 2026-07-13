#!/usr/bin/env bash
# =============================================================================
# MIL Pipeline - Executar pipeline
# =============================================================================
# Uso: ./run-proc.sh [argumentos]
# Exemplos:
#   ./run-proc.sh --alelo 0alelos
#   ./run-proc.sh --phase4 --alelo 0alelos
#   ./run-proc.sh --report
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# --- Ativar venv ---
if [ ! -d ".venv" ]; then
    echo "[ERRO] Virtual environment nao encontrado. Execute: ./setup.sh"
    exit 1
fi

source .venv/bin/activate

# --- Executar pipeline ---
python scripts/run.py "$@"
