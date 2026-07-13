import cv2
import numpy as np

from mil.config import get


def classify(thumb_bgr: np.ndarray) -> str:
    hsv = cv2.cvtColor(thumb_bgr, cv2.COLOR_BGR2HSV)
    h, s, _ = cv2.split(hsv)

    fundo_min = get("stain_classifier.fundo_saturacao_min", 20)
    hue_min = get("stain_classifier.magenta_hue_min", 145)
    hue_max = get("stain_classifier.magenta_hue_max", 175)

    tissue_mask = s > fundo_min
    if tissue_mask.sum() == 0:
        return "HE"

    tissue_h = h[tissue_mask]
    tissue_s = s[tissue_mask]

    magenta_mask = (tissue_h >= hue_min) & (tissue_h <= hue_max)
    magenta_density = magenta_mask.sum() / tissue_mask.sum()

    mean_saturation = float(tissue_s.mean())

    if magenta_density > 0.15 or mean_saturation > 60:
        return "PAS"
    return "HE"
