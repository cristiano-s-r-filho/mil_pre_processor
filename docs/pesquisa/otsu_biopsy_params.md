# Otsu Thresholding for Biopsy Tissue Detection

## Method
1. Convert thumbnail to grayscale
2. Apply Otsu threshold (inverted): separates tissue (dark) from background (white)
3. Morphological closing: consolidates tubular lumens and Bowman's space
4. Filter by minimum area: removes dust/debris

## Parameters (`_constants.py`)
- `CLOSING_KERNEL_SIZE = (50, 50)` → elliptical kernel, ~5% of 1024px thumbnail
- `AREA_MIN_PX = 500` → minimum connected component area

## Rationale
- Kidney biopsy fragments appear as dark tissue regions on white/light background
- Closing bridges small gaps within tissue (e.g., tubular lumens)
- 50px kernel at 1024px scale ≈ large enough for glomerular structures
- Area filter removes staining artifacts and dust

## Edge cases handled
- Black/empty image: detected region >90% of thumbnail → discarded
- Single connected region: `N0` (not cut)
- Multiple disconnected regions: `S0` (cut) with one polygon per region
