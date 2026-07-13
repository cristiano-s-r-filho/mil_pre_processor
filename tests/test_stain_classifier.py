import numpy as np
import pytest

from mil.phase1_stain_classifier import classify


def _make_thumb(hue_mean: float, sat_mean: float) -> np.ndarray:
    h, w = 100, 100
    hsv = np.zeros((h, w, 3), dtype=np.uint8)
    hsv[:, :, 0] = int(hue_mean)
    hsv[:, :, 1] = int(sat_mean)
    hsv[:, :, 2] = 200
    import cv2
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def test_he_low_saturation():
    thumb = _make_thumb(hue_mean=30, sat_mean=30)
    assert classify(thumb) == "HE"


def test_pas_high_magenta():
    thumb = _make_thumb(hue_mean=160, sat_mean=80)
    assert classify(thumb) == "PAS"


def test_pas_high_saturation():
    thumb = _make_thumb(hue_mean=30, sat_mean=120)
    assert classify(thumb) == "PAS"


def test_all_background():
    hsv = np.zeros((50, 50, 3), dtype=np.uint8)
    hsv[:, :, 2] = 255
    import cv2
    thumb = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    assert classify(thumb) == "HE"
