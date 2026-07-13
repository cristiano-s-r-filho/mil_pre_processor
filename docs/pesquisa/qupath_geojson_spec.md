# QuPath GeoJSON Format Specification

## References
- QuPath accepts GeoJSON files dragged directly onto the viewer
- Supported format: FeatureCollection with Polygon geometry
- Coordinates in the original image's pixel coordinate system

## Implementation (`phase3_dataset_builder.py`)

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "class": "tissue_section"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[x1, y1], [x2, y2], ...]]
      }
    }
  ]
}
```

## Coordinate scaling
- Polygons are detected at thumbnail resolution (1024px)
- Coordinates are scaled to original image resolution using:
  - `scale_x = orig_width / thumb_width`
  - `scale_y = orig_height / thumb_height`
- This ensures the annotations align correctly when loaded into QuPath

## Notes
- One Feature per detected tissue fragment
- Default class name: "tissue_section" (editable in QuPath)
- Polygon simplification: cv2.approxPolyDP with epsilon=2.0
