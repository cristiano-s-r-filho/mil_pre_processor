"""Relatórios ricos usando Rich para UI/UX moderna."""

import json
import os
from datetime import datetime, timezone
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

console = Console()


def create_progress() -> Progress:
    """Cria barra de progresso Rich para processamento de arquivos.

    Returns:
        Progress configurado.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
    )


def create_live_stats_table() -> Table:
    """Cria tabela de estatísticas em tempo real.

    Returns:
        Table configurada.
    """
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Métrica", style="dim")
    table.add_column("Valor")
    return table


def update_live_stats(
    table: Table,
    stats: dict[str, Any],
    current_file: str = "",
) -> None:
    """Atualiza tabela de estatísticas em tempo real.

    Args:
        table: Tabela Rich para atualizar.
        stats: Estatísticas atuais.
        current_file: Arquivo sendo processado.
    """
    table.rows.clear()

    table.add_row("Processados", str(stats.get("processed_files", 0)))
    table.add_row(
        "OK",
        f"[green]{stats.get('ok', 0)}[/green] "
        f"({stats.get('ok_pct', 0):.1f}%)"
    )
    table.add_row(
        "Erros",
        f"[red]{stats.get('errors', 0)}[/red] "
        f"({stats.get('error_pct', 0):.1f}%)"
    )
    table.add_row("Warnings", f"[yellow]{stats.get('warnings', 0)}[/yellow]")

    stains = stats.get("stains", {})
    if stains:
        stain_str = ", ".join(f"{k}: {v}" for k, v in stains.items())
        table.add_row("Stains", stain_str)

    if current_file:
        table.add_row("Atual", f"[cyan]{current_file}[/cyan]")


def print_phase_indicator(phase: str, status: str = "start") -> None:
    """Imprime indicador de fase.

    Args:
        phase: Nome da fase (ex: "Fase 1", "Fase 2").
        status: "start", "end", ou "error".
    """
    if status == "start":
        console.print(f"[bold bright_blue]>>[/bold bright_blue] [bold]{phase}[/bold]")
    elif status == "end":
        console.print(f"[green]OK[/green] {phase} concluída")
    elif status == "error":
        console.print(f"[red]ERRO[/red] {phase} falhou")


def print_file_processing(
    filename: str,
    patient: str = "",
    image: str = "",
    stain: str = "",
    sections: int = 0,
) -> None:
    """Imprime informações do arquivo sendo processado.

    Args:
        filename: Nome do arquivo.
        patient: ID do paciente.
        image: Número da imagem.
        stain: Tipo de stain.
        sections: Número de seções.
    """
    parts = [f"[cyan]{filename}[/cyan]"]
    if patient:
        parts.append(f"Paciente: [green]{patient}[/green]")
    if image:
        parts.append(f"Imagem: {image}")
    if stain:
        parts.append(f"Stain: [yellow]{stain}[/yellow]")
    if sections > 0:
        parts.append(f"Seções: {sections}")

    console.print(f"  {' • '.join(parts)}")


def print_warning(message: str, filename: str = "") -> None:
    """Imprime warning formatado.

    Args:
        message: Mensagem de warning.
        filename: Arquivo relacionado.
    """
    if filename:
        console.print(f"[yellow]WARN[/yellow] [dim]{filename}[/dim]: {message}")
    else:
        console.print(f"[yellow]WARN[/yellow] {message}")


def print_error(message: str, filename: str = "", exception: str = "") -> None:
    """Imprime erro formatado.

    Args:
        message: Mensagem de erro.
        filename: Arquivo relacionado.
        exception: Exceção capturada.
    """
    parts = [f"[red]ERRO[/red]"]
    if filename:
        parts.append(f"[dim]{filename}[/dim]")
    parts.append(message)
    if exception:
        parts.append(f"[dim]({exception})[/dim]")

    console.print(" ".join(parts))


def report_summary(run: dict) -> None:
    """Relatório resumido (uma tela)."""
    total = run.get("total", 0)
    ok = run.get("ok", 0)
    errors = run.get("errors", 0)
    cortados = run.get("cortados", 0)
    alelo = run.get("alelo", "?")
    run_id = run.get("run_id", "?")

    pct_ok = (ok / total * 100) if total > 0 else 0
    pct_err = (errors / total * 100) if total > 0 else 0

    status = "SUCESSO" if errors == 0 else "COM ERROS"
    style = "green" if errors == 0 else "yellow" if pct_err < 50 else "red"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Alelo", alelo)
    table.add_row("Run ID", run_id)
    table.add_row("Total", str(total))
    table.add_row("OK", f"[green]{ok}[/green] ({pct_ok:.1f}%)")
    table.add_row("Erros", f"[red]{errors}[/red] ({pct_err:.1f}%)")
    table.add_row("Cortados", f"[cyan]{cortados}[/cyan]")

    console.print(Panel(table, title=f"[{style}]{status}[/{style}]", border_style=style))


def report_extensive(run: dict) -> None:
    """Relatório extenso (detalhado por arquivo)."""
    report_summary(run)

    files = run.get("files", [])
    if not files:
        return

    console.print()

    ok_files = [f for f in files if f.get("status") == "ok"]
    err_files = [f for f in files if f.get("status") == "error"]

    if ok_files:
        table_ok = Table(title="Arquivos Processados", show_lines=True)
        table_ok.add_column("Arquivo", style="cyan", no_wrap=True)
        table_ok.add_column("Paciente", style="green")
        table_ok.add_column("Stain", style="yellow")
        table_ok.add_column("Secoes", justify="right")
        table_ok.add_column("Multi", justify="center")

        for f in ok_files:
            table_ok.add_row(
                f.get("filename", "?"),
                f.get("patient", "?"),
                f.get("stain", "?"),
                str(f.get("sections", 0)),
                "S" if f.get("has_multiple") else "N",
            )
        console.print(table_ok)

    if err_files:
        console.print()
        table_err = Table(title="Arquivos com Erro", show_lines=True)
        table_err.add_column("Arquivo", style="red", no_wrap=True)
        table_err.add_column("Motivo", style="yellow")

        for f in err_files:
            table_err.add_row(
                f.get("filename", "?"),
                f.get("reason", "?"),
            )
        console.print(table_err)


def report_phase4(stats: dict, alelo: str) -> None:
    """Relatório da fase 4 (cropping)."""
    sd_ok = stats.get("sd_ok", 0)
    nd_ok = stats.get("nd_ok", 0)
    polygons = stats.get("polygons_total", 0)
    errors = stats.get("errors", 0)
    total = sd_ok + nd_ok

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Alelo", alelo)
    table.add_row("Cortados (SD)", f"[cyan]{sd_ok}[/cyan]")
    table.add_row("Copiados (ND)", f"[green]{nd_ok}[/green]")
    table.add_row("Total poligonos", str(polygons))
    table.add_row("Erros", f"[red]{errors}[/red]" if errors > 0 else "0")

    style = "green" if errors == 0 else "yellow"
    console.print(Panel(table, title=f"[{style}]Fase 4 - {alelo}[/{style}]", border_style=style))


def report_margin(margin: int, mode: str, phase: str) -> None:
    """Relatório de configuração de margem."""
    if margin == 0 or mode == "exact":
        return

    style = "cyan" if mode == "outside" else "yellow"
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Fase", phase)
    table.add_row("Margem", f"{margin}px")
    table.add_row("Modo", f"[{style}]{mode}[/{style}]")

    console.print(Panel(table, title=f"[{style}]Configuração de Margem[/{style}]", border_style=style))


def report_runtime_stats(stats: dict) -> None:
    """Relatório de estatísticas de runtime."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Métrica", style="dim")
    table.add_column("Valor")

    table.add_row("Total", str(stats.get("total_files", 0)))
    table.add_row("Processados", str(stats.get("processed_files", 0)))
    table.add_row("Warnings", f"[yellow]{stats.get('warnings', 0)}[/yellow]")
    table.add_row("Erros", f"[red]{stats.get('errors', 0)}[/red]")

    stains = stats.get("stains", {})
    if stains:
        stain_str = ", ".join(f"{k}: {v}" for k, v in stains.items())
        table.add_row("Stains", stain_str)

    console.print(Panel(table, title="Estatísticas de Runtime", border_style="bright_blue"))


def print_header() -> None:
    """Cabeçalho do pipeline."""
    console.print()
    console.print(
        Panel(
            "[bold]MIL Pipeline[/bold]\n"
            "Triagem e classificação de lâminas renais",
            border_style="bright_blue",
        )
    )


def print_step(step: str, detail: str = "") -> None:
    """Imprime etapa do pipeline."""
    msg = f"[bold bright_blue]>>[/bold bright_blue] {step}"
    if detail:
        msg += f" [dim]({detail})[/dim]"
    console.print(msg)


def print_success(msg: str) -> None:
    console.print(f"[green]OK[/green] {msg}")


def print_warning_msg(msg: str) -> None:
    console.print(f"[yellow]AVISO[/yellow] {msg}")


def print_error_msg(msg: str) -> None:
    console.print(f"[red]ERRO[/red] {msg}")


def print_config(key: str, value: str) -> None:
    """Imprime configuração."""
    console.print(f"  [dim]{key}:[/dim] {value}")


def print_separator() -> None:
    """Imprime separador."""
    console.print("[dim]" + "─" * 50 + "[/dim]")


# ============================================================
# Relatórios Detalhados (JSON + Terminal)
# ============================================================

from mil.balance import BalanceReport, PatientReport


def generate_classification_report(balance_report: BalanceReport) -> dict[str, Any]:
    """Gera relatório de classificação (phase1 + phase2).

    Args:
        balance_report: Relatório de balanceamento.

    Returns:
        Dicionário com o relatório.
    """
    return {
        "type": "classification",
        "summary": {
            "total_images": balance_report.total_images,
            "total_sections": balance_report.total_sections,
            "total_patients": balance_report.total_patients,
        },
        "by_alelo": {
            alelo: {
                "total_images": balance.total_images,
                "total_sections": balance.total_sections,
                "he_images": balance.he_images,
                "pas_images": balance.pas_images,
                "he_sections": balance.he_sections,
                "pas_sections": balance.pas_sections,
                "processing_rate": balance.processing_rate,
            }
            for alelo, balance in balance_report.alelos.items()
        },
        "by_stain": {
            stain: {
                "total_images": s.total_images,
                "total_sections": s.total_sections,
                "percentage": s.percentage_of_total_images,
            }
            for stain, s in balance_report.stains.items()
        },
    }


def generate_cropping_report(
    balance_report: BalanceReport,
    phase4_stats: dict | None = None,
) -> dict[str, Any]:
    """Gera relatório de cropping (phase4).

    Args:
        balance_report: Relatório de balanceamento.
        phase4_stats: Estatísticas da fase 4 (se disponível).

    Returns:
        Dicionário com o relatório.
    """
    report: dict[str, Any] = {
        "type": "cropping",
        "summary": {
            "total_images": balance_report.total_images,
            "total_sections": balance_report.total_sections,
            "total_patients": balance_report.total_patients,
        },
        "images_per_patient": {
            "avg": 0,
            "min": 0,
            "max": 0,
        },
        "sections_per_image": {
            "avg": 0,
            "min": 0,
            "max": 0,
        },
    }

    # Calcular estatísticas por paciente
    patients = balance_report.patients
    if patients:
        images_per_patient = [p.total_images for p in patients]
        sections_per_patient = [p.total_sections for p in patients]

        report["images_per_patient"] = {
            "avg": sum(images_per_patient) / len(images_per_patient),
            "min": min(images_per_patient),
            "max": max(images_per_patient),
        }

        # Calcular média de seções por imagem
        all_sections = [p.sections_per_image_avg for p in patients if p.total_images > 0]
        if all_sections:
            report["sections_per_image"] = {
                "avg": sum(all_sections) / len(all_sections),
                "min": min(all_sections),
                "max": max(p.sections_per_image_max for p in patients),
            }

    # Adicionar estatísticas da fase 4 se disponíveis
    if phase4_stats:
        report["phase4_stats"] = phase4_stats

    # Prontos para patching
    total_s0 = sum(p.images_s0 for p in patients)
    total_n0 = sum(p.images_n0 for p in patients)
    total_polygons = sum(p.total_polygons for p in patients)

    report["ready_for_patching"] = {
        "images_s0": total_s0,
        "images_n0": total_n0,
        "total_images": total_s0 + total_n0,
        "total_polygons": total_polygons,
    }

    return report


def generate_patient_reports(
    balance_report: BalanceReport,
) -> dict[str, Any]:
    """Gera relatório detalhado por paciente.

    Args:
        balance_report: Relatório de balanceamento.

    Returns:
        Dicionário com relatório de pacientes.
    """
    patients = balance_report.patients

    # Resumo geral
    total_patients = len(patients)
    processed_patients = sum(1 for p in patients if p.processing_status == "complete")
    partial_patients = sum(1 for p in patients if p.processing_status == "partial")
    failed_patients = sum(1 for p in patients if p.processing_status == "failed")

    # Estatísticas de seções
    sections_stats = []
    for p in patients:
        if p.total_sections > 0:
            sections_stats.append(p.total_sections)

    report: dict[str, Any] = {
        "type": "patients",
        "summary": {
            "total_patients": total_patients,
            "processed_patients": processed_patients,
            "partial_patients": partial_patients,
            "failed_patients": failed_patients,
            "processing_rate": (processed_patients / total_patients * 100) if total_patients > 0 else 0,
        },
        "sections_distribution": {
            "total_sections": sum(sections_stats),
            "avg_sections_per_patient": sum(sections_stats) / len(sections_stats) if sections_stats else 0,
            "min_sections": min(sections_stats) if sections_stats else 0,
            "max_sections": max(sections_stats) if sections_stats else 0,
        },
        "corrupted_images": {
            "total": sum(p.corrupted_images for p in patients),
            "by_patient": [
                {
                    "patient_id": p.patient_id,
                    "corrupted": p.corrupted_images,
                    "types": p.corruption_types,
                }
                for p in patients if p.corrupted_images > 0
            ],
        },
        "patients": [p.to_dict() for p in patients],
    }

    return report


def generate_full_report(
    balance_report: BalanceReport,
    phase4_stats: dict | None = None,
) -> dict[str, Any]:
    """Gera relatório completo combinando todos os tipos.

    Args:
        balance_report: Relatório de balanceamento.
        phase4_stats: Estatísticas da fase 4 (se disponível).

    Returns:
        Dicionário com relatório completo.
    """
    return {
        "type": "full",
        "run_id": "",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "classification": generate_classification_report(balance_report),
        "cropping": generate_cropping_report(balance_report, phase4_stats),
        "patients": generate_patient_reports(balance_report),
        "balance": {
            "alelo_imbalance": {
                "detected": balance_report.alelo_imbalance_detected,
                "severity": balance_report.alelo_imbalance_severity,
                "details": balance_report.alelo_imbalance_details,
                "recommendation": balance_report.alelo_recommendation,
            },
            "stain_imbalance": {
                "detected": balance_report.stain_imbalance_detected,
                "severity": balance_report.stain_imbalance_severity,
                "details": balance_report.stain_imbalance_details,
                "recommendation": balance_report.stain_recommendation,
            },
            "statistics": {
                "expected_images_per_alelo": balance_report.expected_images_per_alelo,
                "expected_sections_per_alelo": balance_report.expected_sections_per_alelo,
                "std_deviation_images": balance_report.std_deviation_images,
                "std_deviation_sections": balance_report.std_deviation_sections,
                "cv_images": balance_report.coefficient_of_variation_images,
                "cv_sections": balance_report.coefficient_of_variation_sections,
            },
        },
        "processing_summary": balance_report.processing_summary,
    }


def save_report_json(
    report: dict[str, Any],
    output_dir: str,
    filename: str = "report.json",
) -> str:
    """Salva relatório em JSON.

    Args:
        report: Dicionário do relatório.
        output_dir: Diretório de saída.
        filename: Nome do arquivo.

    Returns:
        Caminho do arquivo salvo.
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return filepath


def save_reports_to_directory(
    run_id: str,
    reports_dir: str,
    balance_report: BalanceReport,
    alert_report: Any | None = None,
    phase4_stats: dict | None = None,
    classification_report: dict | None = None,
    cropping_report: dict | None = None,
    patient_reports: dict | None = None,
) -> str:
    """Salva todos os relatórios em _reports/{run_id}/.

    Args:
        run_id: ID da execução.
        reports_dir: Diretório raiz de relatórios.
        balance_report: Relatório de balanceamento.
        alert_report: Relatório de alertas (opcional).
        phase4_stats: Estatísticas da fase 4 (opcional).
        classification_report: Relatório de classificação (opcional).
        cropping_report: Relatório de cropping (opcional).
        patient_reports: Relatório de pacientes (opcional).

    Returns:
        Caminho do diretório criado.
    """
    run_dir = os.path.join(reports_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)

    # Salvar relatório completo
    full_report = generate_full_report(balance_report, phase4_stats)
    full_report["run_id"] = run_id
    save_report_json(full_report, run_dir, "full_report.json")

    # Salvar relatório de classificação
    if classification_report is None:
        classification_report = generate_classification_report(balance_report)
    save_report_json(classification_report, run_dir, "classification_report.json")

    # Salvar relatório de cropping
    if cropping_report is None:
        cropping_report = generate_cropping_report(balance_report, phase4_stats)
    save_report_json(cropping_report, run_dir, "cropping_report.json")

    # Salvar relatório de pacientes
    if patient_reports is None:
        patient_reports = generate_patient_reports(balance_report)
    save_report_json(patient_reports, run_dir, "patient_reports.json")

    # Salvar relatório de balanceamento
    balance_dict = balance_report.to_dict()
    save_report_json(balance_dict, run_dir, "balance_report.json")

    # Salvar alertas
    if alert_report is not None:
        from mil.alerts import save_alert_report
        save_alert_report(alert_report, run_dir)

    return run_dir


def update_runs_index(
    run_id: str,
    reports_dir: str,
    run_summary: dict[str, Any],
) -> str:
    """Atualiza runs_index.json com informações da execução.

    Args:
        run_id: ID da execução.
        reports_dir: Diretório raiz de relatórios.
        run_summary: Resumo da execução.

    Returns:
        Caminho do arquivo atualizado.
    """
    index_path = os.path.join(reports_dir, "runs_index.json")

    # Carregar índice existente
    runs = []
    if os.path.isfile(index_path):
        with open(index_path, encoding="utf-8") as f:
            runs = json.load(f)

    # Adicionar nova execução
    run_entry = {
        "run_id": run_id,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "summary": run_summary,
    }
    runs.append(run_entry)

    # Salvar índice atualizado
    os.makedirs(reports_dir, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(runs, f, ensure_ascii=False, indent=2)

    return index_path


def report_balance_table(balance_report: BalanceReport) -> None:
    """Imprime tabela de balanceamento no terminal.

    Args:
        balance_report: Relatório de balanceamento.
    """
    console.print()
    console.print("[bold]Balanceamento por Alelo[/bold]")

    table = Table(show_header=True, box=None)
    table.add_column("Alelo", style="cyan")
    table.add_column("Imagens", justify="right")
    table.add_column("Seções", justify="right")
    table.add_column("HE", justify="right", style="yellow")
    table.add_column("PAS", justify="right", style="magenta")
    table.add_column("% Total", justify="right")
    table.add_column("Razão", justify="right")
    table.add_column("Status", justify="center")

    for alelo, balance in balance_report.alelos.items():
        status_style = "green" if balance.is_balanced else "yellow" if balance.imbalance_level == "warning" else "red"
        table.add_row(
            alelo,
            str(balance.total_images),
            str(balance.total_sections),
            str(balance.he_images),
            str(balance.pas_images),
            f"{balance.percentage_of_total_images:.1f}%",
            f"{balance.ratio_to_average_images:.2f}",
            f"[{status_style}]{balance.imbalance_level.upper()}[/{status_style}]",
        )

    console.print(table)


def report_corruption_table(balance_report: BalanceReport) -> None:
    """Imprime tabela de corrupções no terminal.

    Args:
        balance_report: Relatório de balanceamento.
    """
    corrupted_patients = [p for p in balance_report.patients if p.corrupted_images > 0]

    if not corrupted_patients:
        return

    console.print()
    console.print("[bold]Imagens Corrompidas[/bold]")

    table = Table(show_header=True, box=None)
    table.add_column("Paciente", style="cyan")
    table.add_column("Corrompidas", justify="right", style="red")
    table.add_column("Total", justify="right")
    table.add_column("Taxa", justify="right")
    table.add_column("Tipos", style="dim")

    for patient in corrupted_patients:
        rate = (patient.corrupted_images / patient.total_images * 100) if patient.total_images > 0 else 0
        types_str = ", ".join(f"{k}: {v}" for k, v in patient.corruption_types.items())

        table.add_row(
            patient.patient_id,
            str(patient.corrupted_images),
            str(patient.total_images),
            f"{rate:.1f}%",
            types_str,
        )

    console.print(table)


def report_patching_ready(balance_report: BalanceReport) -> None:
    """Imprime resumo de imagens prontas para patching.

    Args:
        balance_report: Relatório de balanceamento.
    """
    total_s0 = sum(p.images_s0 for p in balance_report.patients)
    total_n0 = sum(p.images_n0 for p in balance_report.patients)
    total_polygons = sum(p.total_polygons for p in balance_report.patients)

    console.print()
    console.print("[bold]Prontas para Patching[/bold]")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Cortadas (S0)", f"[cyan]{total_s0}[/cyan]")
    table.add_row("Não Cortadas (N0)", f"[green]{total_n0}[/green]")
    table.add_row("Total Polígonos", str(total_polygons))

    console.print(table)


def report_skipped_files(
    skipped_files: list[dict[str, Any]],
    format_info: dict[str, Any] | None = None,
) -> None:
    """Imprime relatório de arquivos pulados (formato não suportado).

    Args:
        skipped_files: Lista de arquivos pulados com detalhes.
        format_info: Informações sobre o formato (se disponível).
    """
    if not skipped_files:
        return

    console.print()
    console.print("[bold yellow]Arquivos Pulados (Formato Não Suportado)[/bold yellow]")

    # Informações sobre o formato
    if format_info:
        console.print()
        console.print("[bold]Formato Detectado:[/bold]")
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_column(style="bold")
        info_table.add_column()
        
        for key, value in format_info.items():
            info_table.add_row(key, str(value))
        
        console.print(info_table)

    # Tabela de arquivos pulados
    console.print()
    console.print(f"[bold]Total: {len(skipped_files)} arquivos[/bold]")
    
    table = Table(show_header=True, box=None)
    table.add_column("Arquivo", style="cyan", no_wrap=True)
    table.add_column("Paciente", style="green")
    table.add_column("Motivo", style="yellow")
    table.add_column("Detalhes", style="dim")

    for f in skipped_files:
        table.add_row(
            f.get("filename", "?"),
            f.get("patient", "?"),
            f.get("reason", "?"),
            f.get("details", ""),
        )

    console.print(table)

    # Recomendação
    console.print()
    console.print(
        "[dim]Recomendação: Estes arquivos são do formato MetaSystems VSlide (Zeiss Axio Imager Z2). "
        "O formato usa tiles JPEG sem tabelas DQT/DHT (armazenadas externamente no software MetaCyte). "
        "Não é possível processar com OpenSlide/PIL/OpenCV padrão.[/dim]"
    )
