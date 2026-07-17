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
from mil.margin import apply_margin_to_polygon, get_margin_config

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
    feather_radius: int = 0,
    edge_margin: int | None = None,
    edge_mode: str | None = None,
) -> int:
    """Recorta regiões de um S0 usando GeoJSON com margem configurável.

    Args:
        s0_path: Caminho do S0.tif.
        geojson_path: Caminho do GeoJSON.
        out_dir: Diretório de saída.
        patient: ID do paciente.
        image: Número da imagem.
        stain: Tipo de stain (HE/PAS).
        feather_radius: Raio de feathering (0 = desativado).
        edge_margin: Margem de borda (sobrescreve config).
        edge_mode: Modo de borda (sobrescreve config).

    Returns:
        Número de regiões recortadas.
    """
    slide = openslide.OpenSlide(s0_path)
    try:
        with open(geojson_path) as f:
            geojson = json.load(f)
        features = geojson.get("features", [])
        sw, sh = slide.dimensions
        count = 0

        margin, mode = get_margin_config("phase4", edge_margin, edge_mode)

        # Tamanho do tile para processamento chunked (evita MemoryError)
        TILE_SIZE = 512

        for idx, feat in enumerate(features, start=1):
            geom = feat.get("geometry", {})
            if geom.get("type") != "Polygon":
                continue

            coords = np.array(geom["coordinates"][0], dtype=np.float64)
            coords = apply_margin_to_polygon(coords, margin, mode)

            xs, ys = coords[:, 0], coords[:, 1]

            x0 = max(0, int(xs.min()))
            y0 = max(0, int(ys.min()))
            x1 = min(sw, int(xs.max()) + 1)
            y1 = min(sh, int(ys.max()) + 1)
            w, h = x1 - x0, y1 - y0

            if w <= 0 or h <= 0:
                continue

            shifted = coords - np.array([x0, y0], dtype=np.float64)

            if feather_radius > 0:
                mask = _create_feathered_mask(shifted, h, w, feather_radius)
            else:
                mask = _create_binary_mask(shifted, h, w)

            if mask.max() == 0:
                continue

            # Processar em tiles para evitar MemoryError
            out_name = f"ID{patient}_{image}_{stain}_SD_{idx}.tif"
            out_path = os.path.join(out_dir, out_name)

            # Criar array de saída vazio
            output = np.zeros((h, w, 3), dtype=np.uint8)

            # Processar tile por tile
            for ty in range(0, h, TILE_SIZE):
                for tx in range(0, w, TILE_SIZE):
                    # Calcular dimensões do tile
                    tile_h = min(TILE_SIZE, h - ty)
                    tile_w = min(TILE_SIZE, w - tx)

                    # Coordenadas absolutas no slide
                    abs_x = x0 + tx
                    abs_y = y0 + ty

                    try:
                        # Ler tile do slide
                        tile_region = slide.read_region((abs_x, abs_y), 0, (tile_w, tile_h))
                        tile_np = np.array(tile_region.convert("RGB"))

                        # Aplicar máscara do tile
                        tile_mask = mask[ty:ty+tile_h, tx:tx+tile_w]
                        tile_masked = tile_np * tile_mask[:, :, np.newaxis]
                        tile_masked = np.clip(tile_masked, 0, 255).astype(np.uint8)

                        # Colocar no array de saída
                        output[ty:ty+tile_h, tx:tx+tile_w] = tile_masked

                        # Liberar memória
                        del tile_region, tile_np, tile_mask, tile_masked
                    except Exception as e:
                        logger.warning("Falha ao ler tile (%d,%d) de %s: %s", abs_x, abs_y, s0_path, e)
                        continue

            # Salvar resultado
            cv2.imwrite(out_path, output[:, :, ::-1])
            logger.info("Crop %s -> %s", os.path.basename(s0_path), out_name)
            count += 1

            # Liberar memória
            del output, mask, shifted, coords

    finally:
        slide.close()
    return count


def _create_binary_mask(
    polygon: np.ndarray,
    h: int,
    w: int,
) -> np.ndarray:
    """Cria máscara binária sem feathering.

    Args:
        polygon: Coordenadas do polígono (N, 2) em coordenadas locais.
        h: Altura da região.
        w: Largura da região.

    Returns:
        Máscara uint8 (H, W) com valores 0 ou 1.
    """
    binary = np.zeros((h, w), dtype=np.uint8)
    pts = polygon.astype(np.int32).reshape((-1, 1, 2))
    cv2.fillPoly(binary, [pts], 255)
    return (binary > 0).astype(np.float32)


def _create_feathered_mask(
    polygon: np.ndarray,
    h: int,
    w: int,
    feather_radius: int = 10,
) -> np.ndarray:
    """Cria mascara com bordas suaves usando distance transform + Gaussian blur.

    Args:
        polygon: Coordenadas do poligono (N, 2) em coordenadas locais.
        h: Altura da regiao.
        w: Largura da regiao.
        feather_radius: Raio do feathering (pixels).

    Returns:
        Mascara float32 (H, W) com valores [0.0, 1.0].
    """
    binary = np.zeros((h, w), dtype=np.uint8)
    pts = polygon.astype(np.int32).reshape((-1, 1, 2))
    cv2.fillPoly(binary, [pts], 255)

    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
    dist_norm = np.clip(dist / max(feather_radius, 1), 0, 1)

    ksize = feather_radius * 2 + 1
    dist_smooth = cv2.GaussianBlur(dist_norm, (ksize, ksize), 0)

    return dist_smooth.astype(np.float32)


def process_alelo(
    dados_processados_root: str,
    output_root: str,
    alelo: str,
    edge_margin: int | None = None,
    edge_mode: str | None = None,
) -> tuple[int, int]:
    """Processa um alelo na fase 4 (cropping).

    Args:
        dados_processados_root: Raiz dos dados processados.
        output_root: Raiz de saída.
        alelo: Nome do alelo.
        edge_margin: Margem de borda (sobrescreve config).
        edge_mode: Modo de borda (sobrescreve config).

    Returns:
        Tupla (cortadas_count, nao_cortadas_count).
    """
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

                n = _crop_regions_from_s0(
                    s0_path, geojson_path, out_alelo, patient, image, stain,
                    feather_radius=get("cropper.feather_radius", 0),
                    edge_margin=edge_margin,
                    edge_mode=edge_mode,
                )
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
