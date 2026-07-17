"""Relatórios legíveis por humanos em múltiplos formatos.

Gera documentos de relatório formatados para humanos em:
- Markdown (.md) - para visualização e documentação
- YAML (.yaml) - para dados estruturados legíveis
- Texto plain (.txt) - para impressão e logs

Cada relatório inclui:
- Resumo da execução (run summary)
- Tabela de arquivos processados
- Arquivos pulados (MetaSystems VSlide, etc.)
- Análise de balanceamento
- Resumo por paciente
- Alertas e recomendações
"""

import os
from datetime import datetime, timezone
from typing import Any

from rich.console import Console

console = Console()


# ============================================================
# Funções principais
# ============================================================

def generate_human_report(
    run_id: str,
    run_data: dict[str, Any],
    balance_report: Any | None = None,
    skipped_files: list[dict[str, Any]] | None = None,
    output_dir: str = ".",
    formats: list[str] | None = None,
) -> dict[str, str]:
    """Gera relatório legível por humanos em múltiplos formatos.

    Args:
        run_id: ID da execução.
        run_data: Dados da execução (do run dict).
        balance_report: Relatório de balanceamento (opcional).
        skipped_files: Lista de arquivos pulados (opcional).
        output_dir: Diretório de saída.
        formats: Lista de formatos ("md", "yaml", "txt"). Default: ["md", "yaml"].

    Returns:
        Dicionário com caminhos dos arquivos gerados {formato: caminho}.
    """
    if formats is None:
        formats = ["md", "yaml"]

    os.makedirs(output_dir, exist_ok=True)
    generated_files = {}

    # Preparar dados do relatório
    report_data = _prepare_report_data(run_id, run_data, balance_report, skipped_files)

    # Gerar em cada formato
    if "md" in formats:
        path = _generate_markdown(report_data, output_dir)
        generated_files["markdown"] = path

    if "yaml" in formats:
        path = _generate_yaml(report_data, output_dir)
        generated_files["yaml"] = path

    if "txt" in formats:
        path = _generate_text(report_data, output_dir)
        generated_files["text"] = path

    return generated_files


# ============================================================
# Preparação dos dados
# ============================================================

def _prepare_report_data(
    run_id: str,
    run_data: dict[str, Any],
    balance_report: Any | None,
    skipped_files: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Prepara dados estruturados para o relatório."""
    now = datetime.now(tz=timezone.utc)

    # Extrair dados básicos
    total = run_data.get("total", 0)
    ok = run_data.get("ok", 0)
    errors = run_data.get("errors", 0)
    cortados = run_data.get("cortados", 0)
    alelo = run_data.get("alelo", "?")

    # Processar arquivos
    files = run_data.get("files", [])
    skipped = skipped_files or run_data.get("skipped_files", [])

    # Estatísticas por stain
    stains = {}
    for f in files:
        if f.get("status") == "ok":
            stain = f.get("stain", "unknown")
            stains[stain] = stains.get(stain, 0) + 1

    # Estatísticas por paciente
    patients = {}
    for f in files:
        if f.get("status") == "ok":
            patient = f.get("patient", "unknown")
            if patient not in patients:
                patients[patient] = {"total": 0, "stains": {}}
            patients[patient]["total"] += 1
            stain = f.get("stain", "unknown")
            patients[patient]["stains"][stain] = patients[patient]["stains"].get(stain, 0) + 1

    # Dados de balanceamento
    balance_data = None
    if balance_report:
        balance_data = {
            "alelo_imbalance_detected": getattr(balance_report, "alelo_imbalance_detected", False),
            "alelo_imbalance_severity": getattr(balance_report, "alelo_imbalance_severity", "none"),
            "stain_imbalance_detected": getattr(balance_report, "stain_imbalance_detected", False),
            "stain_imbalance_severity": getattr(balance_report, "stain_imbalance_severity", "none"),
        }

    return {
        "metadata": {
            "run_id": run_id,
            "generated_at": now.isoformat(),
            "generator": "MIL Pipeline - Human Report Generator",
            "version": "1.0",
        },
        "summary": {
            "alelo": alelo,
            "total_files": total,
            "processed_ok": ok,
            "errors": errors,
            "skipped": len(skipped),
            "cortados": cortados,
            "success_rate": f"{(ok / total * 100):.1f}%" if total > 0 else "0%",
        },
        "stains": stains,
        "patients": patients,
        "files": files,
        "skipped_files": skipped,
        "balance": balance_data,
    }


# ============================================================
# Geração Markdown
# ============================================================

def _generate_markdown(data: dict[str, Any], output_dir: str) -> str:
    """Gera relatório em formato Markdown."""
    run_id = data["metadata"]["run_id"]
    filepath = os.path.join(output_dir, f"{run_id}_report.md")

    lines = []
    _md_header(lines, data)
    _md_summary(lines, data)
    _md_files_table(lines, data)
    _md_skipped_files(lines, data)
    _md_stains(lines, data)
    _md_patients(lines, data)
    _md_balance(lines, data)
    _md_footer(lines, data)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath


def _md_header(lines: list, data: dict) -> None:
    """Cabeçalho Markdown."""
    meta = data["metadata"]
    lines.append(f"# Relatório de Execução - {meta['run_id']}")
    lines.append("")
    lines.append(f"**Gerado em:** {meta['generated_at']}")
    lines.append(f"**Gerador:** {meta['generator']}")
    lines.append(f"**Versão:** {meta['version']}")
    lines.append("")
    lines.append("---")
    lines.append("")


def _md_summary(lines: list, data: dict) -> None:
    """Resumo Markdown."""
    s = data["summary"]
    lines.append("## Resumo")
    lines.append("")
    lines.append(f"| Métrica | Valor |")
    lines.append(f"|---------|-------|")
    lines.append(f"| Alelo | {s['alelo']} |")
    lines.append(f"| Total de Arquivos | {s['total_files']} |")
    lines.append(f"| Processados (OK) | {s['processed_ok']} |")
    lines.append(f"| Erros | {s['errors']} |")
    lines.append(f"| Pulados (formato não suportado) | {s['skipped']} |")
    lines.append(f"| Cortados (múltiplas seções) | {s['cortados']} |")
    lines.append(f"| Taxa de Sucesso | {s['success_rate']} |")
    lines.append("")
    lines.append("---")
    lines.append("")


def _md_files_table(lines: list, data: dict) -> None:
    """Tabela de arquivos processados Markdown."""
    files = data.get("files", [])
    ok_files = [f for f in files if f.get("status") == "ok"]
    err_files = [f for f in files if f.get("status") == "error"]

    lines.append("## Arquivos Processados")
    lines.append("")

    if ok_files:
        lines.append("### Processados com Sucesso")
        lines.append("")
        lines.append("| Arquivo | Paciente | Imagem | Stain | Seções | Múltiplas |")
        lines.append("|---------|----------|--------|-------|--------|-----------|")
        for f in ok_files:
            multiple = "Sim" if f.get("has_multiple") else "Não"
            lines.append(
                f"| {f.get('filename', '?')} | {f.get('patient', '?')} | "
                f"{f.get('image', '?')} | {f.get('stain', '?')} | "
                f"{f.get('sections', 0)} | {multiple} |"
            )
        lines.append("")

    if err_files:
        lines.append("### Arquivos com Erro")
        lines.append("")
        lines.append("| Arquivo | Paciente | Motivo |")
        lines.append("|---------|----------|--------|")
        for f in err_files:
            lines.append(
                f"| {f.get('filename', '?')} | {f.get('patient', '?')} | "
                f"{f.get('reason', '?')} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")


def _md_skipped_files(lines: list, data: dict) -> None:
    """Seção de arquivos pulados Markdown."""
    skipped = data.get("skipped_files", [])
    if not skipped:
        return

    lines.append("## Arquivos Pulados (Formato Não Suportado)")
    lines.append("")
    lines.append("**Formato detectado:** MetaSystems VSlide (híbrido TIFF-JPEG)")
    lines.append("")
    lines.append("**Características:**")
    lines.append("- Header TIFF fake de 8 bytes")
    lines.append("- Tiles JPEG consecutivos sem tabelas DQT/DHT")
    lines.append("- Tabelas armazenadas externamente no software MetaCyte")
    lines.append("- Scanner: Zeiss Axio Imager Z2")
    lines.append("- Empresa: MetaSystems (Altlussheim, Alemanha, desde 1986)")
    lines.append("")
    lines.append(f"**Total de arquivos pulados:** {len(skipped)}")
    lines.append("")
    lines.append("| Arquivo | Paciente | Imagem | Motivo |")
    lines.append("|---------|----------|--------|--------|")
    for f in skipped:
        lines.append(
            f"| {f.get('filename', '?')} | {f.get('patient', '?')} | "
            f"{f.get('image', '?')} | {f.get('reason', '?')} |"
        )
    lines.append("")
    lines.append("**Recomendação:** Estes arquivos requerem o software MetaSystems para visualização.")
    lines.append("")
    lines.append("---")
    lines.append("")


def _md_stains(lines: list, data: dict) -> None:
    """Seção de stains Markdown."""
    stains = data.get("stains", {})
    if not stains:
        return

    lines.append("## Distribuição de Stains")
    lines.append("")
    lines.append("| Stain | Quantidade |")
    lines.append("|-------|------------|")
    for stain, count in sorted(stains.items()):
        lines.append(f"| {stain} | {count} |")
    lines.append("")
    lines.append("---")
    lines.append("")


def _md_patients(lines: list, data: dict) -> None:
    """Seção de pacientes Markdown."""
    patients = data.get("patients", {})
    if not patients:
        return

    lines.append("## Resumo por Paciente")
    lines.append("")
    lines.append("| Paciente | Total | Stains |")
    lines.append("|----------|-------|--------|")
    for patient_id, info in sorted(patients.items()):
        stains_str = ", ".join(f"{k}: {v}" for k, v in info.get("stains", {}).items())
        lines.append(f"| {patient_id} | {info.get('total', 0)} | {stains_str} |")
    lines.append("")
    lines.append("---")
    lines.append("")


def _md_balance(lines: list, data: dict) -> None:
    """Seção de balanceamento Markdown."""
    balance = data.get("balance")
    if not balance:
        return

    lines.append("## Análise de Balanceamento")
    lines.append("")
    lines.append("| Métrica | Valor |")
    lines.append("|---------|-------|")
    lines.append(f"| Desbalanceamento de Alelos Detectado | {'Sim' if balance.get('alelo_imbalance_detected') else 'Não'} |")
    lines.append(f"| Severidade | {balance.get('alelo_imbalance_severity', 'N/A')} |")
    lines.append(f"| Desbalanceamento de Stains Detectado | {'Sim' if balance.get('stain_imbalance_detected') else 'Não'} |")
    lines.append(f"| Severidade | {balance.get('stain_imbalance_severity', 'N/A')} |")
    lines.append("")
    lines.append("---")
    lines.append("")


def _md_footer(lines: list, data: dict) -> None:
    """Rodapé Markdown."""
    lines.append("")
    lines.append(f"*Relatório gerado automaticamente pelo MIL Pipeline em {data['metadata']['generated_at']}*")


# ============================================================
# Geração YAML
# ============================================================

def _generate_yaml(data: dict[str, Any], output_dir: str) -> str:
    """Gera relatório em formato YAML."""
    run_id = data["metadata"]["run_id"]
    filepath = os.path.join(output_dir, f"{run_id}_report.yaml")

    lines = []
    _yaml_section(lines, "metadata", data["metadata"])
    _yaml_section(lines, "summary", data["summary"])
    _yaml_mapping(lines, "stains", data.get("stains", {}))
    _yaml_mapping(lines, "patients", data.get("patients", {}))
    _yaml_list(lines, "files", data.get("files", []))
    _yaml_list(lines, "skipped_files", data.get("skipped_files", []))
    if data.get("balance"):
        _yaml_section(lines, "balance", data["balance"])

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath


def _yaml_section(lines: list, name: str, data: dict) -> None:
    """Seção YAML simples."""
    lines.append(f"{name}:")
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"  {key}:")
            for k, v in value.items():
                lines.append(f"    {k}: {_yaml_value(v)}")
        elif isinstance(value, list):
            lines.append(f"  {key}:")
            for item in value:
                lines.append(f"    - {_yaml_value(item)}")
        else:
            lines.append(f"  {key}: {_yaml_value(value)}")
    lines.append("")


def _yaml_mapping(lines: list, name: str, data: dict) -> None:
    """Mapping YAML."""
    if not data:
        lines.append(f"{name}: {{}}")
        lines.append("")
        return

    lines.append(f"{name}:")
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"  {key}:")
            for k, v in value.items():
                lines.append(f"    {k}: {_yaml_value(v)}")
        else:
            lines.append(f"  {key}: {_yaml_value(value)}")
    lines.append("")


def _yaml_list(lines: list, name: str, data: list) -> None:
    """Lista YAML."""
    if not data:
        lines.append(f"{name}: []")
        lines.append("")
        return

    lines.append(f"{name}:")
    for item in data:
        if isinstance(item, dict):
            lines.append("  -")
            for key, value in item.items():
                if isinstance(value, dict):
                    lines.append(f"    {key}:")
                    for k, v in value.items():
                        lines.append(f"      {k}: {_yaml_value(v)}")
                elif isinstance(value, list):
                    lines.append(f"    {key}:")
                    for v in value:
                        lines.append(f"      - {_yaml_value(v)}")
                else:
                    lines.append(f"    {key}: {_yaml_value(value)}")
        else:
            lines.append(f"  - {_yaml_value(item)}")
    lines.append("")


def _yaml_value(value: Any) -> str:
    """Formata valor para YAML."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        # Escapar strings especiais
        if any(c in value for c in ":{}[],|>&*!%@`"):
            return f'"{value}"'
        return value
    return str(value)


# ============================================================
# Geração Texto Plain
# ============================================================

def _generate_text(data: dict[str, Any], output_dir: str) -> str:
    """Gera relatório em formato texto plain."""
    run_id = data["metadata"]["run_id"]
    filepath = os.path.join(output_dir, f"{run_id}_report.txt")

    lines = []
    _txt_header(lines, data)
    _txt_summary(lines, data)
    _txt_files(lines, data)
    _txt_skipped(lines, data)
    _txt_stains(lines, data)
    _txt_patients(lines, data)
    _txt_footer(lines, data)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath


def _txt_header(lines: list, data: dict) -> None:
    """Cabeçalho texto."""
    meta = data["metadata"]
    lines.append("=" * 60)
    lines.append(f"RELATORIO DE EXECUCAO - {meta['run_id']}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Gerado em: {meta['generated_at']}")
    lines.append(f"Gerador: {meta['generator']}")
    lines.append("")


def _txt_summary(lines: list, data: dict) -> None:
    """Resumo texto."""
    s = data["summary"]
    lines.append("-" * 60)
    lines.append("RESUMO")
    lines.append("-" * 60)
    lines.append(f"Alelo:                  {s['alelo']}")
    lines.append(f"Total de Arquivos:      {s['total_files']}")
    lines.append(f"Processados (OK):       {s['processed_ok']}")
    lines.append(f"Erros:                  {s['errors']}")
    lines.append(f"Pulados (nao suportado):{s['skipped']}")
    lines.append(f"Cortados (multi):       {s['cortados']}")
    lines.append(f"Taxa de Sucesso:        {s['success_rate']}")
    lines.append("")


def _txt_files(lines: list, data: dict) -> None:
    """Arquivos texto."""
    files = data.get("files", [])
    ok_files = [f for f in files if f.get("status") == "ok"]

    lines.append("-" * 60)
    lines.append("ARQUIVOS PROCESSADOS")
    lines.append("-" * 60)

    if ok_files:
        lines.append(f"{'Arquivo':<25} {'Paciente':<10} {'Stain':<8} {'Secoes':<8}")
        lines.append("-" * 55)
        for f in ok_files:
            lines.append(
                f"{f.get('filename', '?'):<25} "
                f"{f.get('patient', '?'):<10} "
                f"{f.get('stain', '?'):<8} "
                f"{f.get('sections', 0):<8}"
            )
    lines.append("")


def _txt_skipped(lines: list, data: dict) -> None:
    """Arquivos pulados texto."""
    skipped = data.get("skipped_files", [])
    if not skipped:
        return

    lines.append("-" * 60)
    lines.append("ARQUIVOS PULADOS (FORMATO NAO SUPORTADO)")
    lines.append("-" * 60)
    lines.append(f"Formato: MetaSystems VSlide (hybrid TIFF-JPEG)")
    lines.append(f"Scanner: Zeiss Axio Imager Z2")
    lines.append(f"Empresa: MetaSystems (Altlussheim, Alemanha)")
    lines.append("")
    lines.append(f"{'Arquivo':<25} {'Paciente':<10} {'Motivo'}")
    lines.append("-" * 60)
    for f in skipped:
        lines.append(
            f"{f.get('filename', '?'):<25} "
            f"{f.get('patient', '?'):<10} "
            f"{f.get('reason', '?')}"
        )
    lines.append("")
    lines.append("Recomendacao: Estes arquivos requerem software MetaSystems.")
    lines.append("")


def _txt_stains(lines: list, data: dict) -> None:
    """Stains texto."""
    stains = data.get("stains", {})
    if not stains:
        return

    lines.append("-" * 60)
    lines.append("DISTRIBUICAO DE STAINS")
    lines.append("-" * 60)
    for stain, count in sorted(stains.items()):
        lines.append(f"{stain:<15} {count}")
    lines.append("")


def _txt_patients(lines: list, data: dict) -> None:
    """Pacientes texto."""
    patients = data.get("patients", {})
    if not patients:
        return

    lines.append("-" * 60)
    lines.append("RESUMO POR PACIENTE")
    lines.append("-" * 60)
    lines.append(f"{'Paciente':<15} {'Total':<8} {'Stains'}")
    lines.append("-" * 60)
    for patient_id, info in sorted(patients.items()):
        stains_str = ", ".join(f"{k}:{v}" for k, v in info.get("stains", {}).items())
        lines.append(
            f"{patient_id:<15} "
            f"{info.get('total', 0):<8} "
            f"{stains_str}"
        )
    lines.append("")


def _txt_footer(lines: list, data: dict) -> None:
    """Rodapé texto."""
    lines.append("=" * 60)
    lines.append(f"Relatorio gerado automaticamente pelo MIL Pipeline")
    lines.append(f"em {data['metadata']['generated_at']}")
    lines.append("=" * 60)


# ============================================================
# Função de conveniência para Rich
# ============================================================

def print_human_report_summary(generated_files: dict[str, str]) -> None:
    """Imprime resumo dos relatórios gerados no terminal Rich."""
    console.print()
    console.print("[bold]Relatórios Gerados[/bold]")
    console.print()

    for fmt, path in generated_files.items():
        console.print(f"  [cyan]{fmt.upper()}[/cyan]: {path}")

    console.print()
    console.print("[dim]Os relatórios contêm detalhes completos da execução.[/dim]")
    console.print("[dim]JSONs detalhados continuam disponíveis em _runtime_logs/.[/dim]")
