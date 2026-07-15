#!/usr/bin/env bash
# =============================================================================
# MIL Pipeline - Inicializar repositorio Git
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  MIL Pipeline - Init Git"
echo "========================================"

# --- Verificar Git ---
if ! command -v git &>/dev/null; then
    echo "[ERRO] git nao encontrado. Instale git."
    exit 1
fi

# --- Verificar se ja e um repositorio Git ---
if [ -d ".git" ]; then
    echo "[AVISO] Repositorio Git ja existe."
    echo ""
    echo "Status atual:"
    git status --short
    echo ""
    echo "Para ver o historico: git log --oneline"
    exit 0
fi

# --- Inicializar repositorio ---
echo "[GIT] Inicializando repositorio..."
git init

# --- Configurar .gitignore (ja deve existir) ---
if [ ! -f ".gitignore" ]; then
    echo "[ERRO] .gitignore nao encontrado. Crie-o antes de inicializar o Git."
    exit 1
fi

# --- Adicionar apenas codigo e configuracao ---
echo "[GIT] Adicionando arquivos de codigo e configuracao..."
git add \
    .gitignore \
    config.yaml \
    pyproject.toml \
    requirements.txt \
    setup.sh \
    update.sh \
    scripts/*.py \
    src/mil/*.py \
    docs/*.md

# --- Verificar o que sera commitado ---
echo ""
echo "[GIT] Arquivos que serao commitados:"
git status --short

# --- Commit inicial ---
echo ""
read -p "Criar commit inicial? (s/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    git commit -m "feat: inicializacao do projeto mil pipeline

- Pipeline de triagem e classificacao de laminas renais (HE/PAS)
- Fase 1: Classificacao de stain (Schreiber pinkness / CLAM HSV)
- Fase 2: Deteccao de tecido (morfologia adaptativa)
- Fase 3: Organizacao do dataset
- Fase 4: Cropping via OpenSlide + GeoJSON
- Configuracao externa (config.yaml)
- Setup para Linux (setup.sh)"
    echo ""
    echo "[OK] Commit inicial criado."
else
    echo "[INFO] Commit nao criado. Arquivos adicionados ao staging."
fi

echo ""
echo "========================================"
echo "  Repositorio Git inicializado!"
echo "========================================"
echo ""
echo "Proximos passos:"
echo "  1. Edite config.local.yaml com os caminhos da sua maquina"
echo "  2. git add . && git commit -m 'update: config local'"
echo "  3. git remote add origin <url-do-repositorio>"
echo "  4. git push -u origin main"
echo ""
echo "Na maquina remota (via SSH):"
echo "  git clone <url-do-repositorio>"
echo "  cd mil && ./setup.sh"
echo ""
echo "Para atualizar sem resetar:"
echo "  cd mil && ./update.sh"
echo ""
