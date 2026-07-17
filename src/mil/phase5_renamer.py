"""Phase 5 - Renomeacao de arquivos para patching.

Renomeia arquivos da Phase 4:
  SD: ID{patient}_{image}_{stain}_SD_{section}.tif -> ID{patient}_{image}_{section}.tif
  ND: ID{patient}_{image}_{stain}_ND.tif          -> ID{patient}_{image}_0.tif
"""

import logging
import os
import re
import shutil

from mil.config import get

logger = logging.getLogger(__name__)

SD_PATTERN = re.compile(
    get(
        "renamer.sd_pattern",
        r"^ID(?P<patient>\d+)_(?P<image>\d+)_(?P<stain>HE|PAS)_SD_(?P<section>\d+)\.tif$",
    )
)
ND_PATTERN = re.compile(
    get(
        "renamer.nd_pattern",
        r"^ID(?P<patient>\d+)_(?P<image>\d+)_(?P<stain>HE|PAS)_ND\.tif$",
    )
)

OUTPUT_PATTERN = get("renamer.output_pattern", "ID{patient}_{image}_{section}.tif")


def process_alelo(
    input_root: str,
    output_root: str,
    alelo: str,
) -> tuple[int, int, int]:
    """Renomeia arquivos de um alelo para formato de patching.

    Args:
        input_root: Raiz de entrada (dados_para_patching).
        output_root: Raiz de saida (dados_renamed).
        alelo: Nome do alelo (0alelos, 1alelo, 2alelos).

    Returns:
        Tupla (sd_count, nd_count, skipped_count).
    """
    src_dir = os.path.join(input_root, alelo)
    if not os.path.isdir(src_dir):
        logger.error("Diretorio nao encontrado: %s", src_dir)
        return 0, 0, 0

    out_dir = os.path.join(output_root, alelo)
    os.makedirs(out_dir, exist_ok=True)

    files = sorted(
        f for f in os.listdir(src_dir)
        if f.lower().endswith(".tif") and not f.startswith(".")
    )

    sd_count = 0
    nd_count = 0
    skipped = 0

    for fname in files:
        src_path = os.path.join(src_dir, fname)

        # Tentar SD
        m = SD_PATTERN.match(fname)
        if m:
            new_name = OUTPUT_PATTERN.format(
                patient=m.group("patient"),
                image=m.group("image"),
                section=m.group("section"),
            )
            dst_path = os.path.join(out_dir, new_name)
            if os.path.exists(dst_path):
                logger.warning("Colisao (pulando): %s", new_name)
                skipped += 1
                continue
            shutil.copy2(src_path, dst_path)
            logger.info("SD: %s -> %s", fname, new_name)
            sd_count += 1
            continue

        # Tentar ND
        m = ND_PATTERN.match(fname)
        if m:
            new_name = OUTPUT_PATTERN.format(
                patient=m.group("patient"),
                image=m.group("image"),
                section="0",
            )
            dst_path = os.path.join(out_dir, new_name)
            if os.path.exists(dst_path):
                logger.warning("Colisao (pulando): %s", new_name)
                skipped += 1
                continue
            shutil.copy2(src_path, dst_path)
            logger.info("ND: %s -> %s", fname, new_name)
            nd_count += 1
            continue

        logger.debug("Padrao nao reconhecido (pulando): %s", fname)
        skipped += 1

    return sd_count, nd_count, skipped


def run(
    input_root: str = "dados_para_patching",
    output_root: str = "dados_renamed",
    alelos: list[str] | None = None,
) -> None:
    """Executa renomeacao para todos os alelos.

    Args:
        input_root: Raiz de entrada.
        output_root: Raiz de saida.
        alelos: Lista de alelos. Se None, processa todos.
    """
    if alelos is None:
        alelos = sorted(
            d for d in os.listdir(input_root)
            if os.path.isdir(os.path.join(input_root, d))
        )

    total_sd = 0
    total_nd = 0
    total_skipped = 0

    for alelo in alelos:
        logger.info("=== Renomeando %s ===", alelo)
        sd, nd, skipped = process_alelo(input_root, output_root, alelo)
        logger.info(
            "  SD: %d | ND: %d | Pulados: %d | Total: %d",
            sd, nd, skipped, sd + nd,
        )
        total_sd += sd
        total_nd += nd
        total_skipped += skipped

    logger.info(
        "\nResumo geral:\n"
        "  SD renomeados: %d\n"
        "  ND renomeados: %d\n"
        "  Pulados: %d\n"
        "  Total: %d",
        total_sd, total_nd, total_skipped, total_sd + total_nd,
    )
