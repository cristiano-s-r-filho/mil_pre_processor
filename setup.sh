#!/usr/bin/env bash
# =============================================================================
# MIL Pipeline - Setup para Linux
# =============================================================================
# Uso: ./setup.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  MIL Pipeline - Setup"
echo "========================================"

# --- Verificar Python ---
if ! command -v python3 &>/dev/null; then
    echo "[ERRO] python3 nao encontrado. Instale Python 3.12+."
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[OK] Python $PY_VER encontrado"

# --- Criar virtual environment ---
if [ ! -d ".venv" ]; then
    echo "[SETUP] Criando virtual environment..."
    python3 -m venv .venv
else
    echo "[OK] Virtual environment ja existe"
fi

# --- Ativar venv ---
echo "[SETUP] Ativando virtual environment..."
source .venv/bin/activate

# --- Atualizar pip ---
echo "[SETUP] Atualizando pip..."
pip install --upgrade pip --quiet

# --- Instalar dependencias ---
echo "[SETUP] Instalando dependencias..."
pip install -r requirements.txt --quiet

# --- Instalar pacote em modo editavel ---
echo "[SETUP] Instalando mil em modo editavel..."
pip install -e . --quiet

# --- Criar config.local.yaml se nao existir ---
if [ ! -f "config.local.yaml" ]; then
    echo "[SETUP] Criando config.local.yaml..."
    cp config.yaml config.local.yaml
    echo "[AVISO] Edite config.local.yaml com os caminhos da sua maquina."
else
    echo "[OK] config.local.yaml ja existe"
fi

# --- Criar alias run-proc ---
echo ""
echo "[SETUP] Configurando alias 'run-proc'..."
ALIAS_LINE="alias run-proc='source $(pwd)/.venv/bin/activate && python $(pwd)/scripts/run.py'"
BASHRC="$HOME/.bashrc"

if ! grep -q "alias run-proc=" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# MIL Pipeline - run-proc alias" >> "$BASHRC"
    echo "alias run-proc='$ALIAS_LINE'" >> "$BASHRC"
    echo "[OK] Alias 'run-proc' adicionado ao .bashrc"
else
    echo "[OK] Alias 'run-proc' ja existe no .bashrc"
fi

echo ""
echo "========================================"
echo "  Setup concluido!"
echo "========================================"
echo ""
echo "Proximos passos:"
echo "  1. Edite config.local.yaml com os caminhos da sua maquina"
echo "  2. Abra um novo terminal (ou execute: source ~/.bashrc)"
echo "  3. Use 'run-proc' para executar o pipeline"
echo ""
echo "Exemplos de uso:"
echo "  run-proc --alelo 0alelos"
echo "  run-proc --alelo 1alelo --verbose"
echo "  run-proc --phase4 --alelo 0alelos"
echo "  run-proc --report"
echo ""
