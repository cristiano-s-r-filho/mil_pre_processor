import json
import tempfile
from pathlib import Path

from mil.phase3_dataset_builder import build, parse_filename


def test_parse_filename_ok():
    assert parse_filename("ID123_4.tif") == ("123", "4")
    assert parse_filename("ID9999_12.tif") == ("9999", "12")


def test_parse_filename_invalid():
    assert parse_filename("foo.tif") is None
    assert parse_filename("ID123.tif") is None
    assert parse_filename("") is None


def test_build_single(tmp_path: Path):
    src = tmp_path / "ID1_1.tif"
    src.write_text("fake-tif-data")
    dst = tmp_path / "output"

    result = build(str(src), str(dst), "1alelo", "1", "1", "HE", False, [])

    expected = dst / "1alelo" / "ID1" / "nao_cortadas" / "ID1_1_HE_N0.tif"
    assert result == str(expected)
    assert expected.exists()
    assert expected.read_text() == "fake-tif-data"


def test_build_multiple_geojson(tmp_path: Path):
    from shapely.geometry import Polygon
    src = tmp_path / "ID1_1.tif"
    src.write_text("fake-tif-data")
    dst = tmp_path / "output"

    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    result = build(str(src), str(dst), "1alelo", "1", "1", "PAS", True, [poly])

    tif_path = dst / "1alelo" / "ID1" / "cortadas" / "ID1_1_PAS_S0.tif"
    geojson_path = tif_path.with_suffix(".geojson")
    assert tif_path.exists()
    assert geojson_path.exists()

    with open(geojson_path) as f:
        data = json.load(f)
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    assert data["features"][0]["geometry"]["type"] == "Polygon"
