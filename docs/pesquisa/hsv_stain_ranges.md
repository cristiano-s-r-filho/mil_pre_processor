# HSV Ranges for Stain Classification (HE vs PAS)

## References
- H&E: Hematoxylin stains nuclei blue/purple (Hue ~200-300), Eosin stains cytoplasm pink (Hue ~330-360/0-20)
- PAS: Periodic Acid-Schiff stains magenta (Hue ~300-330), strong overall saturation

## Implementation (`_constants.py`)
- `MAGENTA_HUE_MIN = 145` → 145 in OpenCV HSV (H range 0-180) = 290 in standard Hue (0-360)
- `MAGENTA_HUE_MAX = 175` → 350 in standard Hue, capturing deep pink/magenta
- `FUNDO_SATURACAO_MIN = 20` → filters white background (low saturation)
- Threshold: `magenta_density > 0.15` or `mean_saturation > 60` → PAS

## Observations from 1alelo dataset
- Most kidney biopsy samples classified as PAS (expected for renal pathology)
- Some slides classified as HE (e.g., ID83_25, ID95_3, ID95_6)

## Notes
- OpenCV uses H range 0-180 (÷2 of standard 0-360)
- Values chosen empirically; may need tuning per staining protocol
