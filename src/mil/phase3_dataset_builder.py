import json
import logging
import os
import re
import shutil

from shapely.geometry import Polygon, mapping

logger = logging.getLogger(__name__)

FILENAME_PATTERN = re.compile(r"^ID(?P<patient>\d+)_(?P<image>\d+)\.tif$")


def parse_filename(filename: str) -> tuple[str, str] | None:
    m = FILENAME_PATTERN.match(filename)
    if m is None:
        return None
    return m.group("patient"), m.group("image")


def _make_output_name(patient: str, image: str, stain: str, status: str) -> str:
    return f"ID{patient}_{image}_{stain}_{status}.tif"


def build(
    src_path: str,
    dst_root: str,
    alelo: str,
    patient: str,
    image: str,
    stain: str,
    has_multiple: bool,
    polygons: list[Polygon],
) -> str | None:
    status = "S0" if has_multiple else "N0"
    subdir = "cortadas" if has_multiple else "nao_cortadas"
    out_name = _make_output_name(patient, image, stain, status)

    dst_dir = os.path.join(dst_root, alelo, f"ID{patient}", subdir)
    os.makedirs(dst_dir, exist_ok=True)

    dst_path = os.path.join(dst_dir, out_name)

    # Verificar se o arquivo já existe para evitar duplicatas
    if os.path.exists(dst_path):
        logger.info("Arquivo já existe (pulando): %s", dst_path)
        return dst_path

    # Verificar se existe como S0 (quando deveria ser N0) ou vice-versa
    # Se existir em ambas as pastas, remover a anterior
    other_status = "N0" if has_multiple else "S0"
    other_subdir = "nao_cortadas" if has_multiple else "cortadas"
    other_out_name = _make_output_name(patient, image, stain, other_status)
    other_dst_dir = os.path.join(dst_root, alelo, f"ID{patient}", other_subdir)
    other_dst_path = os.path.join(other_dst_dir, other_out_name)

    if os.path.exists(other_dst_path):
        logger.warning(
            "Removendo duplicata: %s (arquivo existe em ambas as pastas)",
            other_dst_path,
        )
        os.remove(other_dst_path)
        # Remover GeoJSON associado se existir
        other_geojson = other_dst_path.replace(".tif", ".geojson")
        if os.path.exists(other_geojson):
            os.remove(other_geojson)

    shutil.copy2(src_path, dst_path)
    logger.info("Copiado: %s -> %s", src_path, dst_path)

    if has_multiple and polygons:
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"class": "tissue_section"},
                    "geometry": mapping(poly),
                }
                for poly in polygons
            ],
        }
        geojson_path = dst_path.replace(".tif", ".geojson")
        with open(geojson_path, "w") as f:
            json.dump(geojson, f, indent=2)
        logger.info("GeoJSON criado: %s", geojson_path)

    return dst_path
