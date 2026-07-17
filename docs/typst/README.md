# MIL Pipeline — Apresentação Typst

## Estrutura

```
docs/typst/
├── presentation.typ    # Apresentação principal (standalone)
├── presentation.pdf    # PDF compilado
└── README.md           # Este arquivo
```

## Design

### Paleta de Cores
- **Primary:** Deep Teal `#0D4F4F`
- **Secondary:** Medium Teal `#1A7A7A`
- **Accent:** Warm Coral `#E8573A`
- **Accent2:** Amber `#F5A623`
- **Background:** Off-white `#FAFBFC`
- **Surface:** Light Gray-blue `#EDF2F7`

### Componentes
- `card()` — Bloco com fundo arredondado
- `stat-card()` — Card de estatística com valor grande
- `alert-box()` — Caixa de alerta com ícone
- `metric-row()` — Linha com barra de progresso

### Estrutura de Slides
1. Capa (gradiente teal)
2. Introdução e Motivação
3. Dados Originais (324 TIFFs)
4. Formato MetaSystems VSlide
5. Convencionamento de Nomes
6. Dados Processados (S0/N0)
7. Dados para Patching (SD/ND)
8. Classificação de Stains
9. Detecção de Tecido
10. Balanceamento
11. Precedentes Acadêmicos
12. Métricas de Precisão
13. Conclusões
14. Agradecimentos (gradiente teal)

## Como Compilar

### Windows
```bash
# Instalar Typst (se não instalado)
# scoop install typst
# ou baixar de https://github.com/typst/typst/releases

# Compilar
typst compile presentation.typ presentation.pdf
```

### VS Code
1. Instalar extensão `Typst` ou `Tinymist`
2. Abrir `presentation.typ`
3. Ctrl+Shift+P → "Typst: Export PDF"

### Typst Web App
1. Acessar https://typst.app
2. Fazer upload de `presentation.typ`
3. Download do PDF gerado

## Personalização

### Cores
Edite as variáveis no início do arquivo:
```typst
#let c-primary    = rgb("#0D4F4F")
#let c-secondary  = rgb("#1A7A7A")
#let c-accent     = rgb("#E8573A")
```

### Adicionar Slides
```typst
= Seção

== Título do Slide

#grid(
  columns: (1fr, 1fr),
  gutter: 1cm,
  [Coluna 1],
  [Coluna 2],
)
```

### Componentes Disponíveis
```typst
#card(fill: c-surface)[Conteúdo]
#stat-card("324", "Arquivos")
#alert-box[Texto de alerta]
#metric-row("Label", "100%", bar-fraction: 1.0)
```
