"""Margem configurável para polígonos e máscaras.

Fornece funções para aplicar margem (expansão/ contração) em:
- Máscaras binárias (operações morfológicas)
- Polígonos Shapely (buffer com join_style=2/mitre)

Usado nas fases 2 e 4 do pipeline para controlar bordas do corte.
"""

import cv2
import numpy as np
from shapely.geometry import Polygon


def apply_margin_to_mask(
    mask: np.ndarray,
    margin: int,
    mode: str = "exact",
) -> np.ndarray:
    """Aplica margem à máscara usando operações morfológicas.

    Args:
        mask: Máscara binária (H, W) uint8 com valores 0 ou 255.
        margin: Número de pixels de margem.
        mode: "exact" (sem mudança), "outside" (dilatar), "inside" (erodir).

    Returns:
        Máscara com margem aplicada.
    """
    if margin <= 0 or mode == "exact":
        return mask

    ksize = margin * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))

    if mode == "outside":
        return cv2.dilate(mask, kernel, iterations=1)
    elif mode == "inside":
        return cv2.erode(mask, kernel, iterations=1)

    return mask


def apply_margin_to_polygon(
    coords: np.ndarray,
    margin: int,
    mode: str = "exact",
) -> np.ndarray:
    """Aplica margem ao polígono usando Shapely buffer (mitre join_style).

    Args:
        coords: Coordenadas do polígono (N, 2) float64.
        margin: Número de pixels de margem.
        mode: "exact" (sem mudança), "outside" (expandir), "inside" (contrair).

    Returns:
        Coordenadas do polígono com margem aplicada.
    """
    if margin <= 0 or mode == "exact":
        return coords

    try:
        poly = Polygon(coords)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            return coords

        if mode == "outside":
            poly_margin = poly.buffer(margin, join_style=2)
        elif mode == "inside":
            poly_margin = poly.buffer(-margin, join_style=2)
        else:
            return coords

        if poly_margin.is_empty or not poly_margin.is_valid:
            return coords

        if poly_margin.geom_type == "MultiPolygon":
            poly_margin = max(poly_margin.geoms, key=lambda p: p.area)

        return np.array(poly_margin.exterior.coords[:-1], dtype=np.float64)

    except Exception:
        return coords


def get_margin_config(
    phase: str,
    edge_margin: int | None = None,
    edge_mode: str | None = None,
) -> tuple[int, str]:
    """Obtém configuração de margem do config ou argumentos CLI.

    Args:
        phase: "phase2" ou "phase4".
        edge_margin: Valor CLI (sobrescreve config).
        edge_mode: Valor CLI (sobrescreve config).

    Returns:
        Tupla (margin, mode).
    """
    from mil.config import get

    prefix = "tissue_detector" if phase == "phase2" else "cropper"

    margin = edge_margin if edge_margin is not None else get(f"{prefix}.edge_margin", 0)
    mode = edge_mode if edge_mode is not None else get(f"{prefix}.edge_mode", "exact")

    return margin, mode
