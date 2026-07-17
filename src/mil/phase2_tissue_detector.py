import cv2
import numpy as np
from shapely.geometry import Polygon

from mil.config import get
from mil.margin import apply_margin_to_mask, get_margin_config


def detect(
    thumb_rgb: np.ndarray,
    stain: str = "HE",
    orig_size: tuple[int, int] | None = None,
    edge_margin: int | None = None,
    edge_mode: str | None = None,
) -> tuple[bool, list[Polygon]]:
    """Detecta polígonos de tecido na thumbnail.

    Args:
        thumb_rgb: Thumbnail RGB (H, W, 3) uint8.
        stain: "HE" ou "PAS".
        orig_size: Tamanho original (width, height) para escala.
        edge_margin: Margem de borda (sobrescreve config).
        edge_mode: Modo de borda (sobrescreve config).

    Returns:
        Tupla (has_multiple, polygons).
    """
    if stain == "PAS":
        mask = _pas_saturation_mask(thumb_rgb)
    else:
        mask = _he_pinkness_mask(thumb_rgb)

    mask = _morph_cleanup(mask)

    margin, mode = get_margin_config("phase2", edge_margin, edge_mode)
    mask = apply_margin_to_mask(mask, margin, mode)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    thumb_h, thumb_w = thumb_rgb.shape[:2]
    total_thumb_px = thumb_w * thumb_h

    area_min = get("tissue_detector.area_min_px", 500)

    polygons = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < area_min or area > 0.90 * total_thumb_px:
            continue

        epsilon = 0.005 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        if len(approx) < 3:
            continue

        poly = Polygon(approx.squeeze(1))
        if not (poly.is_valid and not poly.is_empty):
            continue

        if orig_size is not None:
            orig_w, orig_h = orig_size
            scale_x = orig_w / thumb_w
            scale_y = orig_h / thumb_h
            poly = _scale_polygon(poly, scale_x, scale_y)

        polygons.append(poly)

    has_multiple = len(polygons) > 1
    return has_multiple, polygons


def _he_pinkness_mask(rgb: np.ndarray) -> np.ndarray:
    """Schreiber et al. (2024) - 'Pinkness' para H&E."""
    img = rgb.astype(np.float32) / 255.0
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]

    r_minus_g = np.maximum(r - g, 0)
    b_minus_g = np.maximum(b - g, 0)
    tissue_repr = r_minus_g * b_minus_g

    tissue_uint8 = (tissue_repr * 255).astype(np.uint8)
    _, mask = cv2.threshold(tissue_uint8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return mask


def _pas_saturation_mask(rgb: np.ndarray) -> np.ndarray:
    """CLAM-style: saturacao HSV para PAS (magenta)."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    sat_blur = cv2.medianBlur(sat, 7)
    _, mask = cv2.threshold(sat_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return mask


def _morph_cleanup(mask: np.ndarray) -> np.ndarray:
    """Limpeza morfologica adaptativa."""
    h, w = mask.shape[:2]
    close_k = max(3, min(h, w) // 200)
    if close_k % 2 == 0:
        close_k += 1
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_k, close_k))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)

    open_k = max(3, min(h, w) // 400)
    if open_k % 2 == 0:
        open_k += 1
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_k, open_k))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)

    area_min = get("tissue_detector.area_min_px", 500)
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    min_area = max(area_min, (h * w) // 10000)
    for i in range(1, n_labels):
        if stats[i, cv2.CC_STAT_AREA] < min_area:
            mask[labels == i] = 0

    return mask


def _scale_polygon(poly: Polygon, sx: float, sy: float) -> Polygon:
    coords = list(poly.exterior.coords)
    scaled = [(x * sx, y * sy) for x, y in coords]
    return Polygon(scaled)
