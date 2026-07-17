"""Sistema de alertas e checks de qualidade.

Gera alerts.json com verificações automáticas de:
- Balanceamento entre alelos (principal)
- Balanceamento entre stains (secundário)
- Imagens corrompidas por classe
- Distribuição de pacientes
- Status de processamento
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any

from mil.balance import BalanceReport


@dataclass
class Alert:
    """Um alerta individual."""
    level: str  # "info", "warning", "critical"
    category: str  # "balance", "corruption", "stain", "patient", "processing"
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário (para JSON)."""
        return {
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "details": self.details,
            "recommendation": self.recommendation,
        }


@dataclass
class AlertReport:
    """Relatório completo de alertas."""
    run_id: str
    timestamp: str

    # Alertas por categoria
    alerts: list[Alert]

    # Resumo
    total_critical: int
    total_warnings: int
    total_info: int

    # Status geral
    overall_status: str  # "ok", "warning", "critical"
    overall_details: str

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário (para JSON)."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "alerts": [a.to_dict() for a in self.alerts],
            "total_critical": self.total_critical,
            "total_warnings": self.total_warnings,
            "total_info": self.total_info,
            "overall_status": self.overall_status,
            "overall_details": self.overall_details,
        }


def check_balance_alerts(
    balance_report: BalanceReport,
    run_id: str = "",
) -> list[Alert]:
    """Verifica balanceamento e gera alertas.

    Args:
        balance_report: Relatório de balanceamento.
        run_id: ID da execução.

    Returns:
        Lista de alertas encontrados.
    """
    alerts = []

    # --- Balanceamento de Alelos (PRINCIPAL) ---
    if balance_report.alelo_imbalance_severity == "critical":
        alerts.append(Alert(
            level="critical",
            category="balance",
            message=balance_report.alelo_imbalance_details,
            details={
                "expected_images_per_alelo": balance_report.expected_images_per_alelo,
                "std_deviation_images": balance_report.std_deviation_images,
                "coefficient_of_variation": balance_report.coefficient_of_variation_images,
                "alelos": {
                    k: {
                        "total_images": v.total_images,
                        "percentage": v.percentage_of_total_images,
                        "ratio_to_average": v.ratio_to_average_images,
                    }
                    for k, v in balance_report.alelos.items()
                },
            },
            recommendation=balance_report.alelo_recommendation,
        ))
    elif balance_report.alelo_imbalance_severity == "warning":
        alerts.append(Alert(
            level="warning",
            category="balance",
            message=balance_report.alelo_imbalance_details,
            details={
                "expected_images_per_alelo": balance_report.expected_images_per_alelo,
                "std_deviation_images": balance_report.std_deviation_images,
                "coefficient_of_variation": balance_report.coefficient_of_variation_images,
            },
            recommendation=balance_report.alelo_recommendation,
        ))

    # Verificar por alelo individualmente
    for alelo, balance in balance_report.alelos.items():
        if balance.imbalance_level == "critical":
            alerts.append(Alert(
                level="critical",
                category="balance",
                message=f"Alelo '{alelo}': {balance.imbalance_details}",
                details={
                    "alelo": alelo,
                    "total_images": balance.total_images,
                    "total_sections": balance.total_sections,
                    "percentage_of_total_images": balance.percentage_of_total_images,
                    "processing_rate": balance.processing_rate,
                },
                recommendation=f"Verificar processamento do alelo '{alelo}'. "
                               f"Taxa de processamento: {balance.processing_rate:.1f}%",
            ))
        elif balance.imbalance_level == "warning":
            alerts.append(Alert(
                level="warning",
                category="balance",
                message=f"Alelo '{alelo}': {balance.imbalance_details}",
                details={
                    "alelo": alelo,
                    "total_images": balance.total_images,
                    "processing_rate": balance.processing_rate,
                },
            ))

    # --- Balanceamento de Stains (SECUNDÁRIO) ---
    if balance_report.stain_imbalance_detected:
        alerts.append(Alert(
            level="warning",
            category="stain",
            message=balance_report.stain_imbalance_details,
            details={
                "stains": {
                    k: {
                        "total_images": v.total_images,
                        "percentage": v.percentage_of_total_images,
                    }
                    for k, v in balance_report.stains.items()
                },
            },
            recommendation=balance_report.stain_recommendation,
        ))

    return alerts


def check_corruption_alerts(
    balance_report: BalanceReport,
    run_id: str = "",
) -> list[Alert]:
    """Verifica imagens corrompidas e gera alertas.

    Args:
        balance_report: Relatório de balanceamento.
        run_id: ID da execução.

    Returns:
        Lista de alertas encontrados.
    """
    alerts = []

    # Verificar por paciente
    for patient in balance_report.patients:
        if patient.corrupted_images > 0:
            level = "critical" if patient.corrupted_images > 2 else "warning"
            alerts.append(Alert(
                level=level,
                category="corruption",
                message=f"Paciente '{patient.patient_id}': {patient.corrupted_images} imagens corrompidas",
                details={
                    "patient_id": patient.patient_id,
                    "corrupted_images": patient.corrupted_images,
                    "total_images": patient.total_images,
                    "corruption_types": patient.corruption_types,
                    "processing_status": patient.processing_status,
                },
                recommendation=f"Verificar integridade dos arquivos do paciente '{patient.patient_id}'. "
                               f"Tipos: {', '.join(patient.corruption_types.keys())}",
            ))

    # Verificar taxa de corrupção geral
    total_images = balance_report.total_images
    total_corrupted = sum(p.corrupted_images for p in balance_report.patients)
    corruption_rate = (total_corrupted / total_images * 100) if total_images > 0 else 0

    if corruption_rate > 10:
        alerts.append(Alert(
            level="critical",
            category="corruption",
            message=f"Taxa de corrupção elevada: {corruption_rate:.1f}% ({total_corrupted}/{total_images})",
            details={
                "total_images": total_images,
                "total_corrupted": total_corrupted,
                "corruption_rate": corruption_rate,
            },
            recommendation="Considerar rebaixar as configurações de validação ou verificar fonte dos dados.",
        ))
    elif corruption_rate > 5:
        alerts.append(Alert(
            level="warning",
            category="corruption",
            message=f"Taxa de corrupção moderada: {corruption_rate:.1f}% ({total_corrupted}/{total_images})",
            details={
                "total_images": total_images,
                "total_corrupted": total_corrupted,
                "corruption_rate": corruption_rate,
            },
        ))

    return alerts


def check_patient_alerts(
    balance_report: BalanceReport,
    run_id: str = "",
) -> list[Alert]:
    """Verifica processamento de pacientes e gera alertas.

    Args:
        balance_report: Relatório de balanceamento.
        run_id: ID da execução.

    Returns:
        Lista de alertas encontrados.
    """
    alerts = []

    # Pacientes com falha total
    failed_patients = [p for p in balance_report.patients if p.processing_status == "failed"]
    if failed_patients:
        alerts.append(Alert(
            level="critical",
            category="patient",
            message=f"{len(failed_patients)} paciente(s) falharam completamente",
            details={
                "failed_patients": [p.patient_id for p in failed_patients],
                "count": len(failed_patients),
            },
            recommendation="Verificar logs de erro para esses pacientes.",
        ))

    # Pacientes com processamento parcial
    partial_patients = [p for p in balance_report.patients if p.processing_status == "partial"]
    if partial_patients:
        alerts.append(Alert(
            level="warning",
            category="patient",
            message=f"{len(partial_patients)} paciente(s) processados parcialmente",
            details={
                "partial_patients": [
                    {
                        "patient_id": p.patient_id,
                        "processed": p.processed_images,
                        "total": p.total_images,
                    }
                    for p in partial_patients
                ],
                "count": len(partial_patients),
            },
            recommendation="Verificar se arquivos faltantes existem no diretório de origem.",
        ))

    # Verificar distribuição por alelo
    alelo_counts = {}
    for patient in balance_report.patients:
        alelo = patient.alelo
        if alelo not in alelo_counts:
            alelo_counts[alelo] = {"total": 0, "processed": 0, "errors": 0}
        alelo_counts[alelo]["total"] += patient.total_images
        alelo_counts[alelo]["processed"] += patient.processed_images
        alelo_counts[alelo]["errors"] += patient.error_images

    for alelo, counts in alelo_counts.items():
        if counts["errors"] > 0:
            error_rate = counts["errors"] / counts["total"] * 100 if counts["total"] > 0 else 0
            if error_rate > 30:
                alerts.append(Alert(
                    level="critical",
                    category="patient",
                    message=f"Alelo '{alelo}': {error_rate:.1f}% de erros ({counts['errors']}/{counts['total']})",
                    details={
                        "alelo": alelo,
                        "total_images": counts["total"],
                        "error_images": counts["errors"],
                        "error_rate": error_rate,
                    },
                    recommendation=f"Verificar processamento do alelo '{alelo}'.",
                ))
            elif error_rate > 10:
                alerts.append(Alert(
                    level="warning",
                    category="patient",
                    message=f"Alelo '{alelo}': {error_rate:.1f}% de erros ({counts['errors']}/{counts['total']})",
                    details={
                        "alelo": alelo,
                        "error_rate": error_rate,
                    },
                ))

    return alerts


def check_processing_alerts(
    balance_report: BalanceReport,
    run_id: str = "",
) -> list[Alert]:
    """Verifica status de processamento e gera alertas.

    Args:
        balance_report: Relatório de balanceamento.
        run_id: ID da execução.

    Returns:
        Lista de alertas encontrados.
    """
    alerts = []

    # Verificar taxa de processamento geral
    processing_summary = balance_report.processing_summary
    total = processing_summary.get("total_images", 0)
    processed = processing_summary.get("processed_images", 0)
    errors = processing_summary.get("error_images", 0)

    if total > 0:
        success_rate = processed / total * 100
        error_rate = errors / total * 100

        if success_rate < 50:
            alerts.append(Alert(
                level="critical",
                category="processing",
                message=f"Taxa de sucesso baixa: {success_rate:.1f}% ({processed}/{total})",
                details={
                    "total_images": total,
                    "processed_images": processed,
                    "success_rate": success_rate,
                    "error_rate": error_rate,
                },
                recommendation="Verificar logs de erro para entender a causa das falhas.",
            ))
        elif success_rate < 80:
            alerts.append(Alert(
                level="warning",
                category="processing",
                message=f"Taxa de sucesso moderada: {success_rate:.1f}% ({processed}/{total})",
                details={
                    "success_rate": success_rate,
                    "error_rate": error_rate,
                },
            ))

    # Verificar seções por imagem
    sections_stats = []
    for patient in balance_report.patients:
        if patient.total_sections > 0:
            sections_stats.append({
                "patient_id": patient.patient_id,
                "total_sections": patient.total_sections,
                "sections_per_image_avg": patient.sections_per_image_avg,
                "sections_per_image_max": patient.sections_per_image_max,
            })

    # Pacientes com muitas seções (possível outlier)
    if sections_stats:
        avg_sections = sum(s["total_sections"] for s in sections_stats) / len(sections_stats)
        for stat in sections_stats:
            if stat["total_sections"] > avg_sections * 3:
                alerts.append(Alert(
                    level="info",
                    category="processing",
                    message=f"Paciente '{stat['patient_id']}': {stat['total_sections']} seções (média: {avg_sections:.1f})",
                    details=stat,
                    recommendation="Verificar se esse paciente tem muitas seções esperadas.",
                ))

    return alerts


def generate_alert_report(
    balance_report: BalanceReport,
    run_id: str = "",
) -> AlertReport:
    """Gera relatório completo de alertas.

    Args:
        balance_report: Relatório de balanceamento.
        run_id: ID da execução.

    Returns:
        AlertReport com todos os alertas.
    """
    from datetime import datetime, timezone

    alerts = []

    # Verificar cada categoria
    alerts.extend(check_balance_alerts(balance_report, run_id))
    alerts.extend(check_corruption_alerts(balance_report, run_id))
    alerts.extend(check_patient_alerts(balance_report, run_id))
    alerts.extend(check_processing_alerts(balance_report, run_id))

    # Contar por nível
    total_critical = sum(1 for a in alerts if a.level == "critical")
    total_warnings = sum(1 for a in alerts if a.level == "warning")
    total_info = sum(1 for a in alerts if a.level == "info")

    # Determinar status geral
    if total_critical > 0:
        overall_status = "critical"
        overall_details = f"{total_critical} alerta(s) crítico(s), {total_warnings} aviso(s)"
    elif total_warnings > 0:
        overall_status = "warning"
        overall_details = f"{total_warnings} aviso(s)"
    else:
        overall_status = "ok"
        overall_details = "Nenhum alerta detectado"

    return AlertReport(
        run_id=run_id,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        alerts=alerts,
        total_critical=total_critical,
        total_warnings=total_warnings,
        total_info=total_info,
        overall_status=overall_status,
        overall_details=overall_details,
    )


def save_alert_report(
    alert_report: AlertReport,
    output_dir: str,
) -> str:
    """Salva relatório de alertas em JSON.

    Args:
        alert_report: Relatório de alertas.
        output_dir: Diretório de saída.

    Returns:
        Caminho do arquivo salvo.
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "alerts.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(alert_report.to_dict(), f, ensure_ascii=False, indent=2)

    return filepath


def format_alerts_for_display(alert_report: AlertReport) -> str:
    """Formata alertas para exibição no terminal.

    Args:
        alert_report: Relatório de alertas.

    Returns:
        String formatada com os alertas.
    """
    lines = []

    # Status geral
    if alert_report.overall_status == "critical":
        lines.append(f"[red]CRÍTICO[/red] {alert_report.overall_details}")
    elif alert_report.overall_status == "warning":
        lines.append(f"[yellow]AVISO[/yellow] {alert_report.overall_details}")
    else:
        lines.append(f"[green]OK[/green] {alert_report.overall_details}")

    # Detalhar alertas críticos
    critical_alerts = [a for a in alert_report.alerts if a.level == "critical"]
    if critical_alerts:
        lines.append("")
        lines.append("[bold red]Alertas Críticos:[/bold red]")
        for alert in critical_alerts:
            lines.append(f"  [red]•[/red] [{alert.category}] {alert.message}")
            if alert.recommendation:
                lines.append(f"    [dim]Recomendação: {alert.recommendation}[/dim]")

    # Detalhar warnings
    warning_alerts = [a for a in alert_report.alerts if a.level == "warning"]
    if warning_alerts:
        lines.append("")
        lines.append("[bold yellow]Avisos:[/bold yellow]")
        for alert in warning_alerts:
            lines.append(f"  [yellow]•[/yellow] [{alert.category}] {alert.message}")

    return "\n".join(lines)
