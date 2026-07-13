import logging
import os

from tqdm import tqdm

from mil.phase1_stain_classifier import classify
from mil.phase2_tissue_detector import detect
from mil.phase3_dataset_builder import build, parse_filename
from mil.run_logger import log_file
from mil.slide_reader import read_thumbnail

logger = logging.getLogger(__name__)


def process_alelo(
    dataset_root: str,
    output_root: str,
    alelo: str,
    run: dict,
) -> None:
    src_dir = os.path.join(dataset_root, alelo)
    if not os.path.isdir(src_dir):
        logger.error("Diretorio nao encontrado: %s", src_dir)
        return

    files = sorted(
        f
        for f in os.listdir(src_dir)
        if f.endswith(".tif") and not f.startswith(".")
    )
    logger.info("Processando %s: %d arquivos", alelo, len(files))

    for fname in tqdm(files, desc=alelo, unit="img"):
        src_path = os.path.join(src_dir, fname)
        parsed = parse_filename(fname)
        if parsed is None:
            logger.warning("Nome fora do padrao: %s", fname)
            log_file(run, fname, "error", reason="Nome fora do padrao")
            continue

        patient, image = parsed
        result = read_thumbnail(src_path)
        if result is None:
            log_file(
                run, fname, "error",
                reason="Formato de imagem nao reconhecido ou corrompido",
                patient=patient, image=image,
            )
            continue

        thumb, orig_size = result

        try:
            stain = classify(thumb)
            thumb_rgb = thumb[:, :, ::-1]
            has_mult, polygons = detect(thumb_rgb, stain=stain, orig_size=orig_size)
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
            log_file(
                run, fname, "ok",
                patient=patient, image=image,
                stain=stain, sections=len(polygons),
                has_multiple=has_mult,
            )
        except Exception as e:
            logger.exception("Erro ao processar %s: %s", fname, e)
            log_file(
                run, fname, "error",
                reason=f"Excecao: {e}",
                patient=patient, image=image,
            )
