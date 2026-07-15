"""Relatórios ricos usando Rich para UI/UX moderna."""

import os
from datetime import datetime
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
