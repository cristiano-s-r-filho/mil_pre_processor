# MIL Pipeline — Relatório de Resultados

**Data:** 16 de Julho de 2026
**Autor:** Cristiano S. R. Filho

---

## 1. Visão Geral

O pipeline processou **324 lâminas TIFF** de biópsia renal, distribuídas em 3 classes de alelos e 33 pacientes. Resultado: **192 imagens** organizadas e **473 imagens** prontas para patching.

| Fase | Entrada | Saída | Conversão |
|------|---------|-------|-----------|
| Dataset original | — | 324 lâminas | — |
| Classificação + Detecção | 324 | 192 | 59.3% |
| Organização S0/N0 | 192 | 122 S0 + 70 N0 | — |
| Recorte de Regiões | 192 | 348 SD + 125 ND | 2.46× |
| **Total Pronto p/ Patching** | **—** | **473 imagens** | **—** |

---

## 2. Formato dos Arquivos

195 TIFF padrão (legíveis) + 129 MetaSystems VSlide (formato proprietário, não suportado).

| Alelo | TIFF Padrão | MetaSystems | Total |
|-------|-------------|-------------|-------|
| 0alelos | 62 | 46 | 108 |
| 1alelo | 27 | 81 | 108 |
| 2alelos | 106 | 2 | 108 |
| **Total** | **195** | **129** | **324** |

**Classificação de Stain** (192 processadas):

| Stain | Quantidade | Percentual |
|-------|------------|------------|
| PAS | 185 | 96.4% |
| HE | 7 | 3.6% |

HE encontrado em: ID548 (2), ID83 (1), ID95 (2), ID518 (2).

---

## 3. Distribuição por Alelo

| Alelo | Original | Processado | S0 | N0 | Pronto |
|-------|----------|------------|-----|-----|--------|
| 0alelos | 108 | 62 | 43 | 19 | 161 |
| 1alelo | 108 | 27 | 6 | 21 | 39 |
| 2alelos | 108 | 103 | 73 | 30 | 273 |
| **Total** | **324** | **192** | **122** | **70** | **473** |

---

## 4. Pacientes e Lâminas

### Pacientes

| Alelo | No Dataset | Processados |
|-------|------------|-------------|
| 0alelos | 12 | 11 |
| 1alelo | 12 | 6 |
| 2alelos | 9 | 9 |
| **Total** | **33** | **26** |

Taxa de processamento: 78.8% (26/33)

### Lâminas por Paciente

| Alelo | Média | Máximo | Total |
|-------|-------|--------|-------|
| 0alelos | 9.0 | 21 | 108 |
| 1alelo | 9.0 | 25 | 108 |
| 2alelos | 12.0 | 21 | 108 |
| **Geral** | **9.8** | **25** | **324** |

Paciente com mais lâminas: ID83 (25, 1alelo)

---

## 5. Seções e Polígonos

### Lâminas com Seções

| Alelo | S0 | Total | Taxa |
|-------|-----|-------|------|
| 0alelos | 43 | 108 | 39.8% |
| 1alelo | 6 | 108 | 5.6% |
| 2alelos | 73 | 108 | 67.6% |
| **Total** | **122** | **324** | **37.7%** |

### Seções por Lâmina S0

| Alelo | Média | Máximo | Total |
|-------|-------|--------|-------|
| 0alelos | 2.81 | 6 | 121 |
| 1alelo | 2.83 | 4 | 17 |
| 2alelos | 3.25 | 6 | 237 |
| **Geral** | **3.07** | **6** | **375** |

Total de GeoJSONs gerados: 122

---

## 6. Dados Prontos para Patching

| Tipo | 0alelos | 1alelo | 2alelos |
|------|---------|--------|---------|
| SD (recortes de S0) | 121 | 17 | 210 |
| ND (cópias de N0) | 40 | 22 | 63 |
| **Total** | **161** | **39** | **273** |

Total: 473 imagens (348 SD + 125 ND)

---

## 7. Resultados Atingidos

1. Pipeline completo — 4 fases funcionais
2. Classificação HE/PAS por HSV — 96.4% PAS, 3.6% HE
3. Detecção de tecido — Schreiber Pinkness + CLAM HSV-saturation
4. Organização automática — S0/N0 com GeoJSONs
5. Recorte por polígonos — chunked processing 512×512 tiles
6. 473 imagens prontas para patching
7. 122 GeoJSONs com 375 seções totais
8. Formato MetaSystems caracterizado (129 arquivos)
9. Margem configurável — edge_margin
10. Relatórios estruturados — JSON + Markdown + YAML + TXT

---

*Relatório gerado em 16/07/2026*
