"""Pipeline principal (fases 1-3) com logging de runtime."""

import logging
import os
import time
from typing import Any

# Suprimir warnings do OpenCV sobre tags TIFF desconhecidas (MetaSystems VSlide)
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"

from mil.phase1_stain_classifier import classify
from mil.phase2_tissue_detector import detect
from mil.phase3_dataset_builder import build, parse_filename
from mil.report import (
    console,
    create_live_stats_table,
    create_progress,
    print_error,
    print_file_processing,
    print_phase_indicator,
    print_warning,
    report_balance_table,
    report_corruption_table,
    report_patching_ready,
    report_skipped_files,
    save_reports_to_directory,
    update_runs_index,
)
from mil.human_report import generate_human_report, print_human_report_summary
from mil.runtime_log import RuntimeLogger, load_runtime_logs
from mil.slide_reader import read_thumbnail, validate_tiff_before_read

logger = logging.getLogger(__name__)


def process_alelo(
    dataset_root: str,
    output_root: str,
    alelo: str,
    run: dict,
    edge_margin: int | None = None,
    edge_mode: str | None = None,
    skip_tiff_validation: bool = False,
) -> None:
    """Processa um alelo (fases 1-3) com logging de runtime.

    Args:
        dataset_root: Raiz do dataset de entrada.
        output_root: Raiz de saída.
        alelo: Nome do alelo.
        run: Dicionário de logging da execução.
        edge_margin: Margem de borda (sobrescreve config).
        edge_mode: Modo de borda (sobrescreve config).
        skip_tiff_validation: Se True, pula validação TIFF prévia.
    """
    from mil.config import get

    src_dir = os.path.join(dataset_root, alelo)
    if not os.path.isdir(src_dir):
        logger.error("Diretorio nao encontrado: %s", src_dir)
        return

    # Inicializar runtime logger
    runtime_log = RuntimeLogger(output_root, run.get("run_id", alelo))

    files = sorted(
        f
        for f in os.listdir(src_dir)
        if f.endswith(".tif") and not f.startswith(".")
    )
    logger.info("Processando %s: %d arquivos", alelo, len(files))

    # Estatísticas para live stats
    stats = {
        "total_files": len(files),
        "processed_files": 0,
        "ok": 0,
        "errors": 0,
        "warnings": 0,
        "stains": {},
        "skipped_files": [],  # Lista de arquivos pulados com detalhes
    }

    # Criar progress bar e live stats
    progress = create_progress()
    stats_table = create_live_stats_table()

    with progress:
        task = progress.add_task(alelo, total=len(files))

        for fname in files:
            src_path = os.path.join(src_dir, fname)
            parsed = parse_filename(fname)

            # Log início do arquivo
            runtime_log.log_file_start(
                fname,
                patient=parsed[0] if parsed else None,
                image=parsed[1] if parsed else None,
                alelo=alelo,
            )

            if parsed is None:
                stats["errors"] += 1
                runtime_log.log_warning(
                    f"Nome fora do padrão: {fname}",
                    filename=fname,
                )
                print_warning(f"Nome fora do padrão: {fname}", fname)
                progress.update(task, advance=1)
                continue

            patient, image = parsed

            # Verificar se o arquivo já foi processado (evitar reprocessamento)
            from mil.config import get as config_get
            output_stains = ["PAS", "HE"]  # Stains possíveis
            already_processed = False
            for s in output_stains:
                for status in ["S0", "N0"]:
                    check_name = f"ID{patient}_{image}_{s}_{status}.tif"
                    check_dirs = ["cortadas", "nao_cortadas"]
                    for sub in check_dirs:
                        check_path = os.path.join(output_root, alelo, f"ID{patient}", sub, check_name)
                        if os.path.exists(check_path):
                            already_processed = True
                            break
                    if already_processed:
                        break
                if already_processed:
                    break

            if already_processed:
                stats["ok"] += 1
                stats["processed_files"] += 1
                runtime_log.log_file_ok(
                    fname,
                    stain="unknown",
                    sections=0,
                    has_multiple=False,
                    patient=patient,
                    image=image,
                    alelo=alelo,
                    tiff_analysis=None,
                )
                progress.update(task, advance=1)
                continue

            # Validação TIFF prévia (opcional) - apenas informativo
            tiff_analysis = None
            if not skip_tiff_validation:
                tiff_analysis = validate_tiff_before_read(src_path)
                if tiff_analysis and tiff_analysis.get("has_critical_corruption"):
                    # Apenas warning - não bloquear leitura
                    runtime_log.log_warning(
                        f"TIFF com possible corrupção (tentando ler): {tiff_analysis.get('error_message', 'desconhecido')}",
                        filename=fname,
                        patient=patient,
                        image=image,
                        details={"tiff_analysis": tiff_analysis},
                    )
                    print_warning(
                        f"Possible corrupção TIFF (tentando ler): {tiff_analysis.get('error_message', 'desconhecido')}",
                        fname,
                    )
            
            # Verificar se é formato MetaSystems VSlide (híbrido TIFF-JPEG)
            # Este formato NÃO é suportado - pular com aviso claro
            if tiff_analysis and tiff_analysis.get("format") == "metasystems_vslide":
                stats["errors"] += 1
                skipped_info = {
                    "filename": fname,
                    "patient": patient,
                    "image": image,
                    "reason": "Formato MetaSystems VSlide não suportado",
                    "details": "Tiles sem tabelas DQT/DHT",
                    "format": tiff_analysis.get("format"),
                    "scanner": tiff_analysis.get("scanner"),
                }
                stats["skipped_files"].append(skipped_info)
                runtime_log.log_skipped(
                    reason="Formato MetaSystems VSlide não suportado",
                    filename=fname,
                    patient=patient,
                    image=image,
                    tiff_analysis=tiff_analysis,
                    skip_category="unsupported_format",
                )
                print_warning(
                    "Formato MetaSystems VSlide não suportado (tiles sem tabelas DQT/DHT)",
                    fname,
                )
                # Adicionar ao run dict para relatório final
                run.setdefault("skipped_files", []).append(skipped_info)
                run["errors"] = run.get("errors", 0) + 1
                run["total"] = run.get("total", 0) + 1
                progress.update(task, advance=1)
                continue

            # Ler thumbnail
            result = read_thumbnail(src_path, skip_validation=True)
            if result is None:
                stats["errors"] += 1
                
                # Mensagem de erro mais detalhada baseada no tipo de problema
                error_msg = "Formato de imagem não reconhecido ou corrompido"
                if tiff_analysis:
                    if tiff_analysis.get("format") == "tiff_jpeg_hybrid":
                        error_msg = "Formato híbrido TIFF-JPEG detectado, mas falha ao ler dados JPEG"
                    elif tiff_analysis.get("has_critical_corruption"):
                        corruptions = tiff_analysis.get("corruptions", [])
                        if corruptions:
                            first_corruption = corruptions[0]
                            error_msg = f"Corrupção detectada: {first_corruption.get('description', 'desconhecido')}"
                
                runtime_log.log_error(
                    error_msg,
                    filename=fname,
                    patient=patient,
                    image=image,
                    tiff_analysis=tiff_analysis,
                    error_category="format",
                )
                print_error(
                    f"Formato não reconhecido",
                    fname,
                )
                progress.update(task, advance=1)
                continue

            thumb, orig_size = result

            try:
                # Fase 1: Classificação de stain
                stain = classify(thumb)

                # Fase 2: Deteção de tecido
                thumb_rgb = thumb[:, :, ::-1]
                has_mult, polygons = detect(
                    thumb_rgb,
                    stain=stain,
                    orig_size=orig_size,
                    edge_margin=edge_margin,
                    edge_mode=edge_mode,
                )

                # Fase 3: Organização do dataset
                build(
                    src_path=src_path,
                    dst_root=output_root,
                    alelo=alelo,
                    patient=patient,
                    image=image,
                    stain=stain,
                    has_multiple=has_mult,
                    polygons=polygons,
                )

                # Atualizar estatísticas
                stats["ok"] += 1
                stats["processed_files"] += 1
                stats["stains"][stain] = stats["stains"].get(stain, 0) + 1

                # Log sucesso
                runtime_log.log_file_ok(
                    fname,
                    stain=stain,
                    sections=len(polygons),
                    has_multiple=has_mult,
                    patient=patient,
                    image=image,
                    alelo=alelo,
                    tiff_analysis=tiff_analysis,
                )

                # Atualizar run dict para relatório final
                run.setdefault("files", []).append({
                    "filename": fname,
                    "status": "ok",
                    "patient": patient,
                    "image": image,
                    "stain": stain,
                    "sections": len(polygons),
                    "has_multiple": has_mult,
                    "tiff_analysis": tiff_analysis,
                })
                run["ok"] = run.get("ok", 0) + 1
                run["total"] = run.get("total", 0) + 1
                if has_mult:
                    run["cortados"] = run.get("cortados", 0) + 1

                # Imprimir processamento do arquivo
                print_file_processing(
                    fname,
                    patient=patient,
                    image=image,
                    stain=stain,
                    sections=len(polygons),
                )

            except Exception as e:
                stats["errors"] += 1
                runtime_log.log_error(
                    f"Exceção ao processar: {e}",
                    filename=fname,
                    patient=patient,
                    image=image,
                    exception=e,
                    tiff_analysis=tiff_analysis,
                    error_category="processing",
                )
                print_error(
                    f"Exceção: {e}",
                    fname,
                    exception=str(type(e).__name__),
                )

                # Atualizar run dict para relatório final
                run.setdefault("files", []).append({
                    "filename": fname,
                    "status": "error",
                    "reason": f"Exceção: {e}",
                    "patient": patient,
                    "image": image,
                })
                run["errors"] = run.get("errors", 0) + 1
                run["total"] = run.get("total", 0) + 1

            progress.update(task, advance=1)

    # Finalizar runtime logger
    runtime_log.finish()

    # Imprimir estatísticas finais
    console.print()
    print_phase_indicator(f"Processamento de {alelo}", "end")


def generate_reports(
    output_root: str,
    run_ids: list[str],
    alelos: list[str],
    skipped_files: list[dict] | None = None,
) -> None:
    """Gera relatórios detalhados após processamento.

    Args:
        output_root: Diretório de saída.
        run_ids: Lista de IDs de execução (um por alelo).
        alelos: Lista de alelos processados.
        skipped_files: Lista de arquivos pulados (opcional).
    """
    from mil.alerts import generate_alert_report
    from mil.balance import generate_balance_report
    from mil.config import get

    print_phase_indicator("Geração de Relatórios", "start")

    # Carregar e mesclar logs de todos os run_ids
    merged_logs = {"files": [], "warnings": [], "errors": [], "summary": []}
    for run_id in run_ids:
        runtime_logs = load_runtime_logs(output_root, run_id)
        for key in merged_logs:
            merged_logs[key].extend(runtime_logs.get(key, []))

    if not merged_logs.get("files"):
        print_warning("Nenhum log de runtime encontrado para gerar relatórios")
        return

    # Usar o último run_id para salvamento
    last_run_id = run_ids[-1] if run_ids else "unknown"

    # Gerar relatório de balanceamento
    balance_report = generate_balance_report(merged_logs, alelos)

    # Gerar relatório de alertas
    alert_report = generate_alert_report(balance_report, last_run_id)

    # Salvar relatórios em _reports/{run_id}/
    reports_dir = get("paths.reports_dir", os.path.join(output_root, "_reports"))
    save_reports_to_directory(
        run_id=last_run_id,
        reports_dir=reports_dir,
        balance_report=balance_report,
        alert_report=alert_report,
    )

    # Atualizar runs_index.json
    run_summary = {
        "total_images": balance_report.total_images,
        "total_sections": balance_report.total_sections,
        "total_patients": balance_report.total_patients,
        "alelos": alelos,
        "processing_summary": balance_report.processing_summary,
    }
    update_runs_index(last_run_id, reports_dir, run_summary)

    # Imprimir relatórios no terminal
    console.print()
    report_balance_table(balance_report)
    report_corruption_table(balance_report)
    report_patching_ready(balance_report)

    # Imprimir arquivos pulados (se houver)
    if skipped_files:
        format_info = {
            "Formato": "MetaSystems VSlide (híbrido TIFF-JPEG)",
            "Scanner": "Zeiss Axio Imager Z2 com software MetaCyte/Metafer",
            "Empresa": "MetaSystems (Altlussheim, Alemanha, desde 1986)",
            "Presença": "103+ países worldwide",
            "Problema": "Tiles JPEG sem tabelas DQT/DHT (armazenadas externamente)",
            "Solução": "Injeção de tabelas padrão ou uso do software MetaSystems",
        }
        report_skipped_files(skipped_files, format_info)

    # Imprimir alertas
    from mil.alerts import format_alerts_for_display
    console.print()
    console.print("[bold]Alertas[/bold]")
    console.print(format_alerts_for_display(alert_report))

    # Gerar relatório legível por humanos
    reports_dir = get("paths.reports_dir", os.path.join(output_root, "_reports"))
    human_reports_dir = os.path.join(reports_dir, last_run_id, "human")
    human_files = generate_human_report(
        run_id=last_run_id,
        run_data={"files": [], "skipped_files": skipped_files or []},  # Placeholder
        balance_report=balance_report,
        skipped_files=skipped_files,
        output_dir=human_reports_dir,
        formats=["md", "yaml", "txt"],
    )
    print_human_report_summary(human_files)

    print_phase_indicator("Geração de Relatórios", "end")
