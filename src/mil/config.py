"""Carrega configuracao de config.yaml / config.local.yaml."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_CONFIG: dict[str, Any] | None = None

_DEFAULTS = {
    "paths": {
        "project_root": "",
        "dataset_root": "",
        "dados_processados_root": "",
        "dados_para_patching_root": "",
    },
    "alelos_validos": ["0alelos", "1alelo", "2alelos"],
    "reader": {
        "thumbnail_size": 1024,
        "pil_max_image_pixels": 500_000_000,
    },
    "stain_classifier": {
        "fundo_saturacao_min": 20,
        "magenta_hue_min": 145,
        "magenta_hue_max": 175,
    },
    "tissue_detector": {
        "area_min_px": 500,
    },
    "builder": {
        "padrao_saida_final": "ID{patient}_{image}_{stain}_{status}.tif",
    },
    "cropper": {
        "s0_pattern": r"^ID(?P<patient>\d+)_(?P<image>\d+)_(?P<stain>HE|PAS)_S0\.tif$",
        "n0_pattern": r"^ID(?P<patient>\d+)_(?P<image>\d+)_(?P<stain>HE|PAS)_N0\.tif$",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _resolve_path(path_str: str) -> str:
    """Resolve caminho relativo para absoluto usando project_root."""
    if not path_str:
        return path_str
    p = Path(path_str)
    if p.is_absolute():
        return str(p)
    # Compatibilidade cross-platform: verificar se comeca com drive letter (Windows)
    if len(path_str) >= 2 and path_str[1] == ":":
        return path_str
    project_root = _CONFIG.get("paths", {}).get("project_root", "")
    if project_root:
        return str(Path(project_root) / p)
    return str(p.resolve())


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    if config_path is None:
        root = Path(__file__).resolve().parent.parent.parent
        local = root / "config.local.yaml"
        default = root / "config.yaml"
        if local.is_file():
            config_path = local
        elif default.is_file():
            config_path = default
        else:
            logger.warning("Nenhum config.yaml encontrado, usando padroes.")
            _CONFIG = _DEFAULTS.copy()
            return _CONFIG

    config_path = Path(config_path)
    if config_path.is_file():
        with open(config_path) as f:
            user_cfg = yaml.safe_load(f) or {}
        _CONFIG = _deep_merge(_DEFAULTS, user_cfg)
        logger.info("Configuracao carregada de: %s", config_path)
    else:
        logger.warning("Arquivo %s nao encontrado, usando padroes.", config_path)
        _CONFIG = _DEFAULTS.copy()

    # Resolver caminhos relativos para absolutos
    paths_cfg = _CONFIG.get("paths", {})
    for key in ["dataset_root", "dados_processados_root", "dados_para_patching_root"]:
        val = paths_cfg.get(key, "")
        if val:
            paths_cfg[key] = _resolve_path(val)

    return _CONFIG


def get(key: str, default: Any = None) -> Any:
    cfg = load_config()
    keys = key.split(".")
    val = cfg
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return default
        if val is None:
            return default
    return val
