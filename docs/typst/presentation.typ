// MIL Pipeline — Relatório de Resultados
// Typst professional template

#set document(
  title: "MIL Pipeline — Relatório de Resultados",
  author: "Cristiano S. R. Filho",
  date: datetime(day: 16, month: 7, year: 2026),
)

#set page(
  paper: "a4",
  margin: (x: 2.5cm, y: 2.5cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(size: 8pt, fill: gray)
      [MIL Pipeline — Relatório de Resultados]
      h(1fr)
      [Cristiano S. R. Filho]
    }
  },
  footer: context {
    if counter(page).get().first() > 1 {
      set text(size: 8pt, fill: gray)
      h(1fr)
      counter(page).display("1 / 1", both: true)
    }
  },
)

#set text(size: 11pt, font: "New Computer Modern", fill: black)
#set par(justify: true, leading: 0.7em)
#set heading(numbering: none)
#show heading.where(level: 1): it => {
  v(1.2cm)
  block(width: 100%)[
    #set text(size: 16pt, weight: "bold")
    #it.body
  ]
  v(0.3cm)
  line(length: 100%, stroke: 0.5pt + black)
  v(0.4cm)
}
#show heading.where(level: 2): it => {
  v(0.8cm)
  block(width: 100%)[
    #set text(size: 12pt, weight: "bold")
    #it.body
  ]
  v(0.2cm)
}
#show heading.where(level: 3): it => {
  v(0.5cm)
  block(width: 100%)[
    #set text(size: 11pt, weight: "bold")
    #it.body
  ]
  v(0.1cm)
}


// ══════════════════════════════════════════════════════════════════════════════
// CAPA
// ══════════════════════════════════════════════════════════════════════════════

#page(header: none, footer: none)[
  #align(center + horizon)[
    #block(width: 70%)[
      #align(center)[
        #text(size: 28pt, weight: "bold")[MIL Pipeline]
        #v(0.3cm)
        #text(size: 14pt)[Relatório de Resultados]
        #v(2cm)
        #line(length: 40%, stroke: 0.5pt + black)
        #v(1cm)
        #text(size: 12pt)[
          Processamento de Whole-Slide Images\
          para Biópsia Renal
        ]
        #v(2cm)
        #grid(
          columns: (1fr, 1fr),
          gutter: 1cm,
          align(left)[
            #text(size: 9pt, fill: gray)[DATA]
            #v(2pt)
            #text(size: 11pt)[16 de Julho de 2026]
          ],
          align(left)[
            #text(size: 9pt, fill: gray)[AUTOR]
            #v(2pt)
            #text(size: 11pt)[Cristiano S. R. Filho]
          ],
        )
      ]
    ]
  ]
]


// ══════════════════════════════════════════════════════════════════════════════
// 1. VISÃO GERAL
// ══════════════════════════════════════════════════════════════════════════════

= Visão Geral

O pipeline processou *324 lâminas TIFF* de biópsia renal, distribuídas em 3 classes de alelos e 33 pacientes. O processamento Resultou em *192 imagens* organizadas e *473 imagens* prontas para patching.

#v(0.3cm)

#table(
  columns: (1fr, auto, auto, auto),
  align: (left, right, right, right),
  stroke: 0.4pt + gray.lighten(60%),
  fill: (_, y) => if y == 0 { gray.lighten(90%) } else if y == 5 { gray.lighten(95%) } else { white },
  [*Fase*], [*Entrada*], [*Saída*], [*Conversão*],
  [Dataset original], [—], [324 lâminas], [—],
  [Classificação + Detecção], [324], [192], [59.3%],
  [Organização S0/N0], [192], [122 S0 + 70 N0], [—],
  [Recorte de Regiões], [192], [348 SD + 125 ND], [2.46×],
  [*Total Pronto p/ Patching*], [*—*], [*473 imagens*], [*—*],
)


// ══════════════════════════════════════════════════════════════════════════════
// 2. FORMATO DOS ARQUIVOS
// ══════════════════════════════════════════════════════════════════════════════

= Formato dos Arquivos

Dos 324 arquivos originais, *195* são TIFF padrão (legíveis por OpenSlide/PIL/OpenCV) e *129* usam o formato proprietário *MetaSystems VSlide* (tiles JPEG sem tabelas DQT/DHT), não suportado por bibliotecas padrão.

#v(0.3cm)

#table(
  columns: (1fr, auto, auto, auto),
  align: (left, right, right, right),
  stroke: 0.4pt + gray.lighten(60%),
  fill: (_, y) => if y == 0 { gray.lighten(90%) } else { white },
  [*Alelo*], [*TIFF Padrão*], [*MetaSystems*], [*Total*],
  [0alelos], [62], [46], [108],
  [1alelo], [27], [81], [108],
  [2alelos], [106], [2], [108],
  [*Total*], [*195*], [*129*], [*324*],
)

#v(0.3cm)

*Classificação de Stain* — Das 192 imagens processadas:

#grid(
  columns: (1fr, 1fr),
  gutter: 1cm,
  [
    #table(
      columns: (1fr, auto, auto),
      align: (left, right, right),
      stroke: 0.4pt + gray.lighten(60%),
      fill: (_, y) => if y == 0 { gray.lighten(90%) } else { white },
      [*Stain*], [*Quantidade*], [*Percentual*],
      [PAS], [185], [96.4%],
      [HE], [7], [3.6%],
      [*Total*], [*192*], [*100%*],
    )
  ],
  [
    *Imagens HE identificadas em:*
    - ID548: 2 imagens
    - ID83: 1 imagem
    - ID95: 2 imagens
    - ID518: 2 imagens
  ],
)


// ══════════════════════════════════════════════════════════════════════════════
// 3. DISTRIBUIÇÃO POR ALELO
// ══════════════════════════════════════════════════════════════════════════════

= Distribuição por Alelo

#table(
  columns: (1fr, auto, auto, auto, auto, auto),
  align: (left, right, right, right, right, right),
  stroke: 0.4pt + gray.lighten(60%),
  fill: (_, y) => if y == 0 { gray.lighten(90%) } else { white },
  [*Alelo*], [*Original*], [*Processado*], [*S0*], [*N0*], [*Pronto*],
  [0alelos], [108], [62], [43], [19], [161],
  [1alelo], [108], [27], [6], [21], [39],
  [2alelos], [108], [103], [73], [30], [273],
  [*Total*], [*324*], [*192*], [*122*], [*70*], [*473*],
)


// ══════════════════════════════════════════════════════════════════════════════
// 4. PACIENTES E LÂMINAS
// ══════════════════════════════════════════════════════════════════════════════

= Pacientes e Lâminas

#grid(
  columns: (1fr, 1fr),
  gutter: 1cm,
  [
    === Pacientes

    #table(
      columns: (1fr, auto, auto),
      align: (left, right, right),
      stroke: 0.4pt + gray.lighten(60%),
      fill: (_, y) => if y == 0 { gray.lighten(90%) } else { white },
      [*Alelo*], [*No Dataset*], [*Processados*],
      [0alelos], [12], [11],
      [1alelo], [12], [6],
      [2alelos], [9], [9],
      [*Total*], [*33*], [*26*],
    )

    #v(0.3cm)

    *Taxa de processamento:* 78.8% (26/33)
  ],
  [
    === Lâminas por Paciente

    #table(
      columns: (auto, auto, auto, auto),
      align: (left, right, right, right),
      stroke: 0.4pt + gray.lighten(60%),
      fill: (_, y) => if y == 0 { gray.lighten(90%) } else { white },
      [*Alelo*], [*Média*], [*Máximo*], [*Total*],
      [0alelos], [9.0], [21], [108],
      [1alelo], [9.0], [25], [108],
      [2alelos], [12.0], [21], [108],
      [*Geral*], [*9.8*], [*25*], [*324*],
    )

    #v(0.3cm)

    *Paciente com mais lâminas:* ID83 (25 lâminas, 1alelo)
  ],
)


// ══════════════════════════════════════════════════════════════════════════════
// 5. SEÇÕES E POLÍGONOS
// ══════════════════════════════════════════════════════════════════════════════

= Seções e Polígonos

Das 324 lâminas, *122* geraram seções (S0 — multi-seção) e *70* foram classificadas como N0 (sem seção detectável).

#grid(
  columns: (1fr, 1fr),
  gutter: 1cm,
  [
    === Lâminas com Seções

    #table(
      columns: (1fr, auto, auto, auto),
      align: (left, right, right, right),
      stroke: 0.4pt + gray.lighten(60%),
      fill: (_, y) => if y == 0 { gray.lighten(90%) } else { white },
      [*Alelo*], [*S0*], [*Total*], [*Taxa*],
      [0alelos], [43], [108], [39.8%],
      [1alelo], [6], [108], [5.6%],
      [2alelos], [73], [108], [67.6%],
      [*Total*], [*122*], [*324*], [*37.7%*],
    )
  ],
  [
    === Seções por Lâmina S0

    #table(
      columns: (auto, auto, auto, auto),
      align: (left, right, right, right),
      stroke: 0.4pt + gray.lighten(60%),
      fill: (_, y) => if y == 0 { gray.lighten(90%) } else { white },
      [*Alelo*], [*Média*], [*Máximo*], [*Total*],
      [0alelos], [2.81], [6], [121],
      [1alelo], [2.83], [4], [17],
      [2alelos], [3.25], [6], [237],
      [*Geral*], [*3.07*], [*6*], [*375*],
    )
  ],
)

#v(0.3cm)

*Total de GeoJSONs gerados:* 122 (um por lâmina S0)


// ══════════════════════════════════════════════════════════════════════════════
// 6. DADOS PRONTOS PARA PATCHING
// ══════════════════════════════════════════════════════════════════════════════

= Dados Prontos para Patching

#table(
  columns: (1fr, auto, auto, auto),
  align: (left, right, right, right),
  stroke: 0.4pt + gray.lighten(60%),
  fill: (_, y) => if y == 0 { gray.lighten(90%) } else { white },
  [*Tipo*], [*0alelos*], [*1alelo*], [*2alelos*],
  [SD (recortes de S0)], [121], [17], [210],
  [ND (cópias de N0)], [40], [22], [63],
  [*Total*], [*161*], [*39*], [*273*],
)

#v(0.2cm)

*Total de imagens prontas:* 473 (348 SD + 125 ND)


// ══════════════════════════════════════════════════════════════════════════════
// 7. ACHIEVEMENTS
// ══════════════════════════════════════════════════════════════════════════════

= Resultados Atingidos

+ Pipeline completo — 4 fases funcionais (classificação, detecção, organização, recorte)
+ Classificação HE/PAS por HSV — 96.4% PAS, 3.6% HE (7 imagens em 4 pacientes)
+ Detecção de tecido — Schreiber Pinkness (H&E) + CLAM HSV-saturation (PAS)
+ Organização automática — S0/N0 com GeoJSONs contendo polígonos de tecido
+ Recorte por polígonos — chunked processing 512×512 tiles (fix MemoryError)
+ 473 imagens prontas para patching (348 SD + 125 ND)
+ 122 GeoJSONs gerados com 375 seções totais
+ Formato MetaSystems VSlide caracterizado (129 arquivos, 39.8%)
+ Margem configurável — edge_margin (0, 50, 100, 200px)
+ Relatórios estruturados — JSON + Markdown + YAML + TXT


// ══════════════════════════════════════════════════════════════════════════════
// ENCERRAMENTO
// ══════════════════════════════════════════════════════════════════════════════

#v(2cm)
#line(length: 100%, stroke: 0.5pt + gray)
#v(0.5cm)

#grid(
  columns: (1fr, 1fr),
  gutter: 1cm,
  [
    #text(size: 9pt, fill: gray)[CONTATO]
    #v(2pt)
    #text(size: 10pt)[cristiano.filho\@ufba.br]
  ],
  [
    #text(size: 9pt, fill: gray)[CÓDIGO]
    #v(2pt)
    #text(size: 10pt)[github.com/cristiano-s-r-filho/mil_pre_processor]
  ],
)
