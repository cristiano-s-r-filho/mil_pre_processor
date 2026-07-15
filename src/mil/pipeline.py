"""Pipeline principal (fases 1-3) com logging de runtime."""

import logging
import time
from typing import Any

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
    update_live_stats,
)
from mil.runtime_log import RuntimeLogger
from mil.slide_reader import read_thumbnail

logger = logging.getLogger(__name__)


def process_alelo(
    dataset_root: str,
    output_root: str,
    alelo: str,
    run: dict,
    edge_margin: int | None = None,
    edge_mode: str | None = None,
) -> None:
    """Processa um alelo (fases 1-3) com logging de runtime.

    Args:
        dataset_root: Raiz do dataset de entrada.
        output_root: Raiz de saída.
        alelo: Nome do alelo.
        run: Dicionário de logging da execução.
        edge_margin: Margem de borda (sobrescreve config).
        edge_mode: Modo de borda (sobrescreve config).
    """
    from mil.config import get
    import os

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

            # Ler thumbnail
            result = read_thumbnail(src_path)
            if result is None:
                stats["errors"] += 1
                runtime_log.log_error(
                    f"Formato de imagem não reconhecido ou corrompido",
                    filename=fname,
                    patient=patient,
                    image=image,
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
