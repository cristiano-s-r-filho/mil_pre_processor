# MIL Pipeline

Pipeline de triagem, classificação automática de coloração (stain) e detecção de múltiplas seções de tecido para laminas renais (biópsias e secções).

## Pré-requisitos

- Python 3.12+
- Git
- Linux (recomendado) ou Windows

## Instalação

```bash
# Clonar o repositório
git clone <url-do-repositorio>
cd mil

# Executar setup (cria venv, instala dependências, configura alias)
./setup.sh
```

O setup cria:
- Virtual environment em `.venv/`
- Arquivo `config.local.yaml` (caminhos locais)
- Alias `run-proc` no `.bashrc`

### Atualizando uma instalação existente

Se a máquina já possui uma instalação anterior, use `update.sh` para preservar as configurações locais:

```bash
cd mil
./update.sh              # Git pull + atualizar dependências
./update.sh --pull-only  # Apenas git pull
./update.sh --deps-only  # Apenas atualizar dependências
```

Arquivos preservados automaticamente:
- `config.local.yaml` (sua configuração)
- `.venv/` (dependências instaladas)
- `_logs/runs.json` (histórico de execuções)

## Configuração

Edite `config.local.yaml` com os caminhos da sua máquina:

```yaml
paths:
  project_root: "/home/usuario/mil"        # Linux
  # project_root: "D:\\Projects\\mil"      # Windows
  dataset_root: "/home/usuario/mil/dataset"
  dados_processados_root: "/home/usuario/mil/dados_processados"
  dados_para_patching_root: "/home/usuario/mil/dados_para_patching"
```

**Importante:** Use caminhos absolutos.

### Configuração do Cropping (Fase 4)

```yaml
cropper:
  feather_radius: 0        # 0 = desativado
  edge_margin: 0           # pixels no espaço original
  edge_mode: "exact"       # "exact" | "outside" | "inside"
```

### Configuração da Margem de Borda

A margem permite preservar mais informação ao redor do tecido detectado:

| Parâmetro | Fase | Descrição |
|-----------|------|-----------|
| `edge_margin` | 2 e 4 | Pixels de margem |
| `edge_mode` | 2 e 4 | Modo: `exact`, `outside`, `inside` |

```yaml
tissue_detector:
  edge_margin: 0           # pixels no thumbnail
  edge_mode: "exact"       # "exact" | "outside" | "inside"

cropper:
  edge_margin: 0           # pixels no espaço original
  edge_mode: "exact"       # "exact" | "outside" | "inside"
```

**Modos:**
- `exact` = comportamento atual (sem margem)
- `outside` = expandir polígono (mais contexto)
- `inside` = contrair polígono (mais conservador)

## Uso

### Executar o pipeline (fases 1-3)

```bash
# Processar todos os alelos
run-proc

# Processar alelo específico
run-proc --alelo 0alelos

# Com log detalhado
run-proc --alelo 0alelos --verbose

# Ver relatório de execuções anteriores
run-proc --report

# Relatório extenso (detalhado por arquivo)
run-proc --report --extensive
```

### Executar cropping (fase 4)

```bash
# Cortar todas as imagens processadas
run-proc --phase4

# Cortar alelo específico
run-proc --phase4 --alelo 0alelos

# Com margem de 50px (expandir bordas)
run-proc --phase4 --alelo 0alelos --edge-margin 50 --edge-mode outside

# Com margem conservadora (contrair bordas)
run-proc --phase4 --alelo 0alelos --edge-margin 30 --edge-mode inside
```

### Relatório

```bash
# Relatório resumido
run-proc --report

# Relatório extenso (mostra cada arquivo processado e com erro)
run-proc --report --extensive
```

### Usar script standalone (sem alias)

```bash
./run-proc.sh --alelo 0alelos
./run-proc.sh --phase4 --alelo 0alelos
```

## Estrutura do Projeto

```
mil/
├── config.yaml              # Configuração padrão (versionado)
├── config.local.yaml        # Configuração local (NÃO versionado)
├── pyproject.toml           # Metadados e dependências
├── requirements.txt         # Dependências pip
├── setup.sh                 # Script de setup
├── update.sh                # Script de atualização
├── run-proc.sh              # Script de execução
├── src/mil/
│   ├── config.py            # Loader de configuração
│   ├── margin.py            # Funções de margem (buffer/morph)
│   ├── pipeline.py          # Pipeline principal (fases 1-3)
│   ├── phase1_stain_classifier.py   # Classificação HE/PAS
│   ├── phase2_tissue_detector.py    # Deteção de tecido
│   ├── phase3_dataset_builder.py    # Organização do dataset
│   ├── phase4_cropper.py            # Cropping via OpenSlide
│   ├── slide_reader.py      # Leitura de imagens
│   ├── run_logger.py        # Logging de execuções
│   └── report.py            # Relatórios com Rich
├── scripts/
│   ├── run.py               # Script principal
│   └── run_phase4.py        # Script da fase 4
└── dataset/                 # Dados de entrada (NÃO versionado)
    ├── 0alelos/
    ├── 1alelo/
    └── 2alelos/
```

## Pipeline

| Fase | Descrição | Entrada | Saída |
|------|-----------|---------|-------|
| 1 | Classificação de stain (HE/PAS) | `.tif` original | Metadados |
| 2 | Deteção de tecido (polígonos) | Thumbnail | GeoJSON |
| 3 | Organização do dataset | `.tif` + GeoJSON | `dados_processados/` |
| 4 | Cropping das regiões | `dados_processados/` | `dados_para_patching/` |

### Funcionalidades

- **Margem configurável**: Expansão/contração de bordas (fases 2 e 4)
- **Feathering opcional**: Suavização de bordas (fase 4)
- **Relatórios Rich**: UI formatada com cores e tabelas
- **CLI flexível**: Flags para teste rápido sem editar config

## Formatos de Arquivo

### Entrada
- Formato: `.tif` (WSI - Whole Slide Image)
- Nomenclatura: `ID<paciente>_<imagem>.tif`

### Saída fase 3
- `ID<paciente>_<imagem>_<stain>_S0.tif` (com múltiplas seções)
- `ID<paciente>_<imagem>_<stain>_N0.tif` (seção única)
- `ID<paciente>_<imagem>_<stain>_S0.geojson` (polígonos)

### Saída fase 4
- `ID<paciente>_<imagem>_<stain>_SD_<n>.tif` (seção cortada)
- `ID<paciente>_<imagem>_<stain>_ND.tif` (cópia sem corte)

## Dependências

- `openslide-python` - Leitura de imagens WSI
- `opencv-python-headless` - Processamento de imagem
- `shapely` - Geometria (polígonos)
- `numpy` - Computação numérica
- `Pillow` - Manipulação de imagens
- `PyYAML` - Leitura de configuração
- `tqdm` - Barra de progresso
- `rich` - Relatórios formatados e cores no terminal

## Solução de Problemas

### Erro: `ModuleNotFoundError: No module named 'yaml'`
```bash
pip install PyYAML
```

### Erro: DLL do OpenSlide (Windows)
```bash
pip install openslide-bin
```

### Erro: `config.local.yaml` não encontrado
```bash
cp config.yaml config.local.yaml
# Edite com os caminhos corretos
```

### Alias `run-proc` não funciona
```bash
source ~/.bashrc
# ou
./run-proc.sh --help
```

## Licença

MIT
