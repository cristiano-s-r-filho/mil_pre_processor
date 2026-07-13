import numpy as np
import pytest

from mil.phase2_tissue_detector import detect


def _make_tissue_thumb(h: int, w: int, n_components: int, val: int = 40):
    arr = np.full((h, w, 3), 220, dtype=np.uint8)
    gap = w // (n_components + 1)
    for i in range(n_components):
        cx = (i + 1) * gap
        cy = h // 2
        rr, cc = np.ogrid[:h, :w]
        mask = ((rr - cy) / (h * 0.15)) ** 2 + ((cc - cx) / (w * 0.05)) ** 2 <= 1
        arr[mask] = val
    return arr


def test_single_section():
    thumb = _make_tissue_thumb(300, 500, 1)
    has_mult, polys = detect(thumb)
    assert has_mult is False
    assert len(polys) == 1


def test_multiple_sections():
    thumb = _make_tissue_thumb(600, 1200, 3)
    has_mult, polys = detect(thumb)
    assert has_mult is True
    assert len(polys) >= 2


def test_no_tissue():
    thumb = np.full((100, 100, 3), 220, dtype=np.uint8)
    has_mult, polys = detect(thumb)
    assert has_mult is False
    assert len(polys) == 0
