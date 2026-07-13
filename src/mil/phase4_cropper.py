import json
import logging
import os
import re
import shutil

import cv2
import numpy as np
import openslide
from tqdm import tqdm

from mil.config import get

logger = logging.getLogger(__name__)

S0_PATTERN = re.compile(get("cropper.s0_pattern", r"^ID(?P<patient>\d+)_(?P<image>\d+)_(?P<stain>HE|PAS)_S0\.tif$"))
N0_PATTERN = re.compile(get("cropper.n0_pattern", r"^ID(?P<patient>\d+)_(?P<image>\d+)_(?P<stain>HE|PAS)_N0\.tif$"))


def _crop_regions_from_s0(
    s0_path: str,
    geojson_path: str,
    out_dir: str,
    patient: str,
    image: str,
    stain: str,
) -> int:
    slide = openslide.OpenSlide(s0_path)
    geojson = json.loads(open(geojson_path).read())
    features = geojson.get("features", [])
    sw, sh = slide.dimensions
    count = 0

    for idx, feat in enumerate(features, start=1):
        geom = feat.get("geometry", {})
        if geom.get("type") != "Polygon":
            continue

        coords = np.array(geom["coordinates"][0], dtype=np.float64)
        xs, ys = coords[:, 0], coords[:, 1]

        x0 = max(0, int(xs.min()))
        y0 = max(0, int(ys.min()))
        x1 = min(sw, int(xs.max()) + 1)
        y1 = min(sh, int(ys.max()) + 1)
        w, h = x1 - x0, y1 - y0

        if w <= 0 or h <= 0:
            continue

        try:
            region = slide.read_region((x0, y0), 0, (w, h))
        except Exception as e:
            logger.warning("Falha ao ler regiao (%d,%d,%d,%d) de %s: %s", x0, y0, w, h, s0_path, e)
            continue

        region_np = np.array(region.convert("RGB"))

        shifted = coords - np.array([x0, y0], dtype=np.float64)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [shifted.astype(np.int32)], 255)

        if mask.sum() == 0:
            continue

        masked = region_np * (mask[:, :, np.newaxis] > 0)

        out_name = f"ID{patient}_{image}_{stain}_SD_{idx}.tif"
        out_path = os.path.join(out_dir, out_name)
        cv2.imwrite(out_path, masked[:, :, ::-1])
        logger.info("Crop %s -> %s", os.path.basename(s0_path), out_name)
        count += 1

    slide.close()
    return count


def process_alelo(
    dados_processados_root: str,
    output_root: str,
    alelo: str,
) -> tuple[int, int]:
    alelo_dir = os.path.join(dados_processados_root, alelo)
    if not os.path.isdir(alelo_dir):
        logger.error("Diretorio nao encontrado: %s", alelo_dir)
        return 0, 0

    out_alelo = os.path.join(output_root, alelo)
    os.makedirs(out_alelo, exist_ok=True)

    cortadas_count = 0
    nao_cortadas_count = 0

    patient_dirs = sorted(
        d for d in os.listdir(alelo_dir)
        if os.path.isdir(os.path.join(alelo_dir, d)) and d.startswith("ID")
    )

    for patient_dir in patient_dirs:
        patient_id = patient_dir[2:]
        patient_path = os.path.join(alelo_dir, patient_dir)

        cortadas_dir = os.path.join(patient_path, "cortadas")
        if os.path.isdir(cortadas_dir):
            s0_files = sorted(f for f in os.listdir(cortadas_dir) if f.endswith("_S0.tif"))
            for s0_name in s0_files:
                m = S0_PATTERN.match(s0_name)
                if m is None:
                    continue
                patient = m.group("patient")
                image = m.group("image")
                stain = m.group("stain")

                s0_path = os.path.join(cortadas_dir, s0_name)
                geojson_name = s0_name.replace(".tif", ".geojson")
                geojson_path = os.path.join(cortadas_dir, geojson_name)

                if not os.path.isfile(geojson_path):
                    logger.warning("GeoJSON nao encontrado para %s", s0_name)
                    continue

                n = _crop_regions_from_s0(s0_path, geojson_path, out_alelo, patient, image, stain)
                cortadas_count += n

        nao_cortadas_dir = os.path.join(patient_path, "nao_cortadas")
        if os.path.isdir(nao_cortadas_dir):
            n0_files = sorted(f for f in os.listdir(nao_cortadas_dir) if f.endswith("_N0.tif"))
            for n0_name in n0_files:
                m = N0_PATTERN.match(n0_name)
                if m is None:
                    continue
                patient = m.group("patient")
                image = m.group("image")
                stain = m.group("stain")

                src = os.path.join(nao_cortadas_dir, n0_name)
                dst_name = f"ID{patient}_{image}_{stain}_ND.tif"
                dst = os.path.join(out_alelo, dst_name)
                shutil.copy2(src, dst)
                logger.info("Copiado %s -> %s", n0_name, dst_name)
                nao_cortadas_count += 1

    return cortadas_count, nao_cortadas_count


def run(
    dados_processados_root: str = "dados_processados",
    output_root: str = "dados_para_patching",
    alelos: list[str] | None = None,
) -> None:
    if alelos is None:
        alelos = sorted(
            d for d in os.listdir(dados_processados_root)
            if os.path.isdir(os.path.join(dados_processados_root, d))
        )

    total_cortadas = 0
    total_nao_cortadas = 0

    for alelo in alelos:
        logger.info("=== Processando %s ===", alelo)
        c, nc = process_alelo(dados_processados_root, output_root, alelo)
        total_cortadas += c
        total_nao_cortadas += nc
        logger.info("%s: %d cortadas, %d nao_cortadas", alelo, c, nc)

    logger.info(
        "Total: %d cortadas + %d nao_cortadas = %d",
        total_cortadas,
        total_nao_cortadas,
        total_cortadas + total_nao_cortadas,
    )
