#!/usr/bin/env bash
# =============================================================================
# MIL Pipeline - Atualizar via Git (remoto)
# =============================================================================
# Para maquinas Linux com acesso SSH que ja possuem config local.
# Uso: ./update.sh [--pull-only | --deps-only]
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

PULL_ONLY=false
DEPS_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --pull-only)  PULL_ONLY=true ;;
        --deps-only)  DEPS_ONLY=true ;;
        --help|-h)
            echo "Uso: $0 [--pull-only | --deps-only]"
            echo ""
            echo "Opcoes:"
            echo "  --pull-only   Apenas git pull (sem atualizar deps)"
            echo "  --deps-only   Apenas atualizar dependencias (sem git pull)"
            echo "  (nenhum)      Atualizar tudo (git pull + deps)"
            exit 0
            ;;
    esac
done

echo "========================================"
echo "  MIL Pipeline - Atualizacao"
echo "========================================"
echo ""

# --- Verificar Git ---
if ! command -v git &>/dev/null; then
    err "git nao encontrado."
    exit 1
fi

# --- Verificar se e repositorio Git ---
if [ ! -d ".git" ]; then
    err "Nao e um repositorio Git."
    exit 1
fi

# --- Verificar arquivos locais ---
info "Verificando arquivos locais..."

LOCAL_FILES=()
[ -f "config.local.yaml" ] && LOCAL_FILES+=("config.local.yaml")
[ -d ".venv" ] && LOCAL_FILES+=(".venv/")
[ -f "_logs/runs.json" ] && LOCAL_FILES+=("_logs/")

if [ ${#LOCAL_FILES[@]} -gt 0 ]; then
    ok "Arquivos locais preservados:"
    for f in "${LOCAL_FILES[@]}"; do
        echo "    - $f"
    done
else
    warn "Nenhum arquivo local encontrado (executou setup.sh?)"
fi

echo ""

# --- Git Pull ---
if [ "$DEPS_ONLY" = false ]; then
    info "Verificando status do repositorio..."
    
    # Verificar se ha mudancas locais nao commitadas
    if ! git diff --quiet HEAD 2>/dev/null; then
        warn "Ha mudancas locais nao commitadas."
        echo ""
        git status --short
        echo ""
        read -p "Continuar? (s/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            info "Atualizacao cancelada."
            exit 0
        fi
    fi
    
    info "Baixando atualizacoes do Git..."
    
    # Stash local changes se houver
    STASHED=false
    if ! git diff --quiet; then
        git stash push -m "auto-stash before update" 2>/dev/null && STASHED=true
    fi
    
    # Pull
    if git pull origin main 2>/dev/null || git pull origin master 2>/dev/null; then
        ok "Codigo atualizado com sucesso."
    else
        warn "Falha ao fazer pull. Verificando remote..."
        git remote -v
        echo ""
        warn "Adicione o remote manualmente:"
        echo "  git remote add origin <url-do-repositorio>"
    fi
    
    # Restaurar stash
    if [ "$STASHED" = true ]; then
        git stash pop 2>/dev/null || warn "Conflito ao restaurar stash. Resolva manualmente."
    fi
fi

echo ""

# --- Atualizar dependencias ---
if [ "$PULL_ONLY" = false ]; then
    if [ ! -d ".venv" ]; then
        warn "Virtual environment nao encontrado. Execute: ./setup.sh"
    else
        info "Atualizando dependencias..."
        source .venv/bin/activate
        
        # Atualizar pip
        pip install --upgrade pip --quiet 2>/dev/null
        
        # Instalar/atualizar dependencias
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt --quiet 2>/dev/null
            ok "Dependencias atualizadas."
        fi
        
        # Reinstalar pacote em modo editavel
        pip install -e . --quiet 2>/dev/null
        ok "Pacote mil reinstalado."
    fi
fi

echo ""

# --- Verificar config.local.yaml ---
if [ -f "config.local.yaml" ]; then
    ok "config.local.yaml preservado."
    echo ""
    echo "  Se houver novas configuracoes no config.yaml, adicione manualmente:"
    echo "  diff config.yaml config.local.yaml"
else
    warn "config.local.yaml nao encontrado."
    echo ""
    read -p "Criar a partir de config.yaml? (s/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        cp config.yaml config.local.yaml
        ok "config.local.yaml criado. Edite com os caminhos da sua maquina."
    fi
fi

echo ""
echo "========================================"
echo "  Atualizacao concluida!"
echo "========================================"
echo ""
echo "Status do repositorio:"
git log --oneline -3
echo ""
echo "Proximos passos:"
echo "  1. Teste: run-proc --report"
echo "  2. Se houver erros: run-proc --alelo 0alelos --verbose"
echo ""
