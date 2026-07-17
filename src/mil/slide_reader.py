import io
import logging
import os

import cv2
import numpy as np
from PIL import Image

from mil.config import get

logger = logging.getLogger(__name__)


def _thumbnail_from_array(arr: np.ndarray, size: int) -> tuple[np.ndarray, tuple[int, int]]:
    orig_h, orig_w = arr.shape[:2]
    scale = min(size / orig_w, size / orig_h)
    if scale < 1:
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        arr = cv2.resize(arr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return arr, (orig_w, orig_h)


def _decode_jpeg_tiff(path: str, size: int) -> tuple[np.ndarray, tuple[int, int]] | None:
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:4] != b"\x49\x49\x2a\x00":
        return None
    ifd_offset = int.from_bytes(raw[4:8], "little")
    if ifd_offset != 8:
        return None
    if len(raw) < 10 or raw[8:10] != b"\xff\xd8":
        return None
    jpeg_data = raw[8:]
    eoi = jpeg_data.find(b"\xff\xd9")
    if eoi > 0:
        single_jpeg = jpeg_data[:eoi + 2]
    else:
        single_jpeg = jpeg_data
    arr = cv2.imdecode(np.frombuffer(single_jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if arr is not None:
        thumb, orig = _thumbnail_from_array(arr, size)
        return thumb, orig
    try:
        buf = io.BytesIO(single_jpeg)
        img = Image.open(buf)
        img.load()
        orig = img.size
        img.thumbnail((size, size), Image.LANCZOS)
        thumb = np.array(img.convert("RGB"))[:, :, ::-1]
        return thumb, orig
    except Exception:
        pass
    return None


def validate_tiff_before_read(path: str) -> dict | None:
    """Valida TIFF antes de tentar ler.

    Args:
        path: Caminho do arquivo TIFF.

    Returns:
        TiffAnalysis.to_dict() se disponível, None caso contrário.
    """
    try:
        from mil.tiff_detector import analyze_tiff, TiffFormat
        analysis = analyze_tiff(path, deep=False, calculate_checksum=False)
        
        # Formato híbrido TIFF-JPEG pode ser lido, mesmo com "corrupção" no header
        if analysis.format == TiffFormat.TIFF_JPEG_HYBRID:
            return None
        
        if analysis.has_critical_corruption:
            return analysis.to_dict()
        return None
    except ImportError:
        return None


def read_thumbnail(
    path: str,
    size: int | None = None,
    skip_validation: bool = False,
) -> tuple[np.ndarray, tuple[int, int]] | None:
    """Lê thumbnail de um arquivo de imagem.

    Args:
        path: Caminho do arquivo.
        size: Tamanho desejado do thumbnail.
        skip_validation: Se True, pula validação TIFF.

    Returns:
        Tupla (thumbnail, dimensoes_originais) ou None.
    """
    if size is None:
        size = get("reader.thumbnail_size", 1024)

    max_pixels = get("reader.pil_max_image_pixels", 500_000_000)
    Image.MAX_IMAGE_PIXELS = max_pixels

    file_size = os.path.getsize(path)
    if file_size == 0:
        logger.warning("Arquivo vazio (0 bytes): %s", path)
        return None

    # Validação TIFF prévia (opcional)
    tiff_analysis = None
    if not skip_validation and path.lower().endswith(('.tif', '.tiff')):
        tiff_analysis = validate_tiff_before_read(path)
        if tiff_analysis and tiff_analysis.get("has_critical_corruption"):
            logger.warning(
                "TIFF com corrupção crítica detectada: %s (%s)",
                path,
                tiff_analysis.get("error_message", "desconhecido"),
            )
            return None

    try:
        img = Image.open(path)
        orig = img.size
        img.thumbnail((size, size), Image.LANCZOS)
        thumb = np.array(img.convert("RGB"))[:, :, ::-1]
        return thumb, orig
    except Exception as e:
        logger.debug("PIL falhou em %s: %s", path, e)
    
    # Tentar formato híbrido TIFF-JPEG (header TIFF + dados JPEG no offset 8)
    result = _decode_jpeg_tiff(path, size)
    if result is not None:
        return result
    
    logger.warning("Formato de imagem nao reconhecido ou corrompido: %s", path)
    return None


def get_tiff_info(path: str) -> dict | None:
    """Obtém informações detalhadas de um TIFF.

    Args:
        path: Caminho do arquivo.

    Returns:
        TiffAnalysis.to_dict() ou None.
    """
    if not path.lower().endswith(('.tif', '.tiff')):
        return None

    try:
        from mil.tiff_detector import analyze_tiff
        analysis = analyze_tiff(path, deep=False, calculate_checksum=False)
        return analysis.to_dict()
    except ImportError:
        return None
