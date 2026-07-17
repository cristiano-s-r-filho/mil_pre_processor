#!/usr/bin/env bash
# =============================================================================
# MIL Pipeline - Setup para Linux
# =============================================================================
# Uso: ./setup.sh [--update]
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[AVISO]${NC} $*"; }
err()   { echo -e "${RED}[ERRO]${NC} $*"; }

UPDATE_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --update)  UPDATE_ONLY=true ;;
    esac
done

echo "========================================"
echo "  MIL Pipeline - Setup"
echo "========================================"

# --- Verificar Python ---
if ! command -v python3 &>/dev/null; then
    err "python3 nao encontrado. Instale Python 3.12+."
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    err "Python $PY_VER encontrado, mas e necessario Python 3.10+."
    exit 1
fi
ok "Python $PY_VER encontrado"

# --- Verificar se ja existe setup ---
if [ -d ".venv" ] && [ -f "config.local.yaml" ]; then
    warn "Setup ja existe neste diretorio."
    echo ""
    info "Arquivos locais encontrados:"
    [ -d ".venv" ] && echo "    - .venv/"
    [ -f "config.local.yaml" ] && echo "    - config.local.yaml"
    [ -f "_logs/runs.json" ] && echo "    - _logs/runs.json"
    echo ""
    
    if [ "$UPDATE_ONLY" = true ]; then
        info "Modo update: pulando criacao de venv."
    else
        read -p "Deseja apenas atualizar (sem resetar)? (s/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            UPDATE_ONLY=true
        fi
    fi
fi

# --- Verificar OpenSlide (dependencia do sistema) ---
if ! dpkg -s libopenslide-dev &>/dev/null && ! dpkg -s libopenslide0 &>/dev/null; then
    warn "OpenSlide nao detectado. Instale com: sudo apt install libopenslide-dev"
    warn "Se ja esta instalado, ignore este aviso."
else
    ok "OpenSlide detectado"
fi

# --- Criar virtual environment ---
if [ "$UPDATE_ONLY" = false ]; then
    if [ ! -d ".venv" ]; then
        info "Criando virtual environment..."
        python3 -m venv .venv
    else
        ok "Virtual environment ja existe"
    fi
else
    ok "Virtual environment preservado"
fi

# --- Ativar venv ---
info "Ativando virtual environment..."
source .venv/bin/activate

# --- Atualizar pip ---
info "Atualizando pip..."
pip install --upgrade pip --quiet

# --- Instalar dependencias ---
info "Instalando dependencias..."
pip install -r requirements.txt --quiet

# --- Instalar pacote em modo editavel ---
info "Instalando mil em modo editavel..."
pip install -e . --quiet

# --- Criar config.local.yaml se nao existir ---
if [ ! -f "config.local.yaml" ]; then
    info "Criando config.local.yaml..."
    cp config.yaml config.local.yaml
    warn "Edite config.local.yaml com os caminhos da sua maquina."
else
    ok "config.local.yaml preservado"
fi

# --- Criar alias run-proc ---
echo ""
info "Configurando alias 'run-proc'..."
ALIAS_LINE="alias run-proc='source $(pwd)/.venv/bin/activate && python $(pwd)/scripts/run.py'"
BASHRC="$HOME/.bashrc"

if ! grep -q "alias run-proc=" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# MIL Pipeline - run-proc alias" >> "$BASHRC"
    echo "alias run-proc='$ALIAS_LINE'" >> "$BASHRC"
    ok "Alias 'run-proc' adicionado ao .bashrc"
else
    ok "Alias 'run-proc' ja existe no .bashrc"
fi

echo ""
echo "========================================"
echo "  Setup concluido!"
echo "========================================"
echo ""
echo "Arquivos locais:"
[ -f "config.local.yaml" ] && echo "  - config.local.yaml (sua configuracao)"
[ -d ".venv" ] && echo "  - .venv/ (dependencias instaladas)"
[ -f "_logs/runs.json" ] && echo "  - _logs/runs.json (historico de execucoes)"
echo ""
echo "Proximos passos:"
echo "  1. Abra um novo terminal (ou execute: source ~/.bashrc)"
echo "  2. Use 'run-proc' para executar o pipeline"
echo ""
echo "Exemplos de uso:"
echo "  run-proc --alelo 0alelos"
echo "  run-proc --alelo 1alelo --verbose"
echo "  run-proc --phase4 --alelo 0alelos"
echo "  run-proc --report"
echo ""
