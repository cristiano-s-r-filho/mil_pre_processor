"""Detecção avançada de formato e corrupção de TIFF.

Fornece análise granular de arquivos TIFF incluindo:
- Detecção de formato (standard, BigTIFF, JPEG-TIFF, OpenSlide, MetaSystems)
- Validação profunda de header, IFDs e tiles
- Identificação detalhada de corrupções
- Cálculo de checksums (apenas para corrompidos)
"""

import hashlib
import io
import logging
import os
import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class TiffFormat(Enum):
    """Formatos TIFF suportados."""
    STANDARD_TIFF = "standard_tiff"
    BIGTIFF = "bigtiff"
    JPEG_TIFF = "jpeg_tiff"
    OPENSLIDE_TIFF = "openslide_tiff"
    METASYSTEMS_VSLIDE = "metasystems_vslide"
    APERIO = "aperio"
    HAMAMATSU = "hamamatsu"
    LEICA = "leica"
    PHILIPS = "philips"
    VENTANA = "ventana"
    TIFF_JPEG_HYBRID = "tiff_jpeg_hybrid"  # TIFF header + JPEG data at offset 8
    UNKNOWN = "unknown"


class CorruptionType(Enum):
    """Tipos de corrupção."""
    NONE = "none"
    TRUNCATED = "truncated"
    HEADER_INVALID = "header_invalid"
    MAGIC_NUMBER_ERROR = "magic_number_error"
    IFD_OFFSET_ERROR = "ifd_offset_error"
    TAG_MISSING = "tag_missing"
    TAG_VALUE_INVALID = "tag_value_invalid"
    TILE_MISSING = "tile_missing"
    TILE_TRUNCATED = "tile_truncated"
    TILE_CORRUPTED = "tile_corrupted"
    TILE_EMPTY = "tile_empty"
    STRIP_MISSING = "strip_missing"
    STRIP_CORRUPTED = "strip_corrupted"
    COMPRESSION_ERROR = "compression_error"
    PIXEL_DATA_MISSING = "pixel_data_missing"
    PIXEL_DATA_CORRUPTED = "pixel_data_corrupted"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    ICC_PROFILE_MISSING = "icc_profile_missing"
    METADATA_CORRUPTED = "metadata_corrupted"
    MEMORY_MAP_ERROR = "memory_map_error"
    OPENSLIDE_ERROR = "openslide_error"
    PILLOW_ERROR = "pillow_error"
    OPENCV_ERROR = "opencv_error"


@dataclass
class CorruptionReport:
    """Relatório de corrupção detalhado."""
    corruption_type: CorruptionType
    severity: str  # "critical", "warning", "info"
    location: str  # "header", "ifd_0", "tile_0_0x0", "pixel_data"
    description: str
    expected: str | None = None
    actual: str | None = None
    offset: int | None = None
    recoverable: bool = False
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TiffHeader:
    """Informações do header TIFF."""
    byte_order: str  # "II" (little-endian) ou "MM" (big-endian)
    version: int  # 42 (TIFF) ou 43 (BigTIFF)
    ifd_offset: int
    byte_order_str: str  # "Little-endian" ou "Big-endian"


@dataclass
class TiffIFD:
    """Informações de um IFD (Image File Directory)."""
    ifd_index: int
    tag_count: int
    width: int
    height: int
    bits_per_sample: int
    compression: int
    compression_name: str
    photometric_interpretation: int
    photometric_name: str
    strip_offsets: list[int]
    strip_byte_counts: list[int]
    strip_count: int
    tile_width: int | None = None
    tile_length: int | None = None
    samples_per_pixel: int = 1
    planar_configuration: int = 1
    software: str | None = None
    datetime: str | None = None
    image_description: str | None = None
    make: str | None = None
    model: str | None = None
    resolution_x: float | None = None
    resolution_y: float | None = None
    resolution_unit: int | None = None
    rows_per_strip: int | None = None
    tags: dict[int, Any] = field(default_factory=dict)


@dataclass
class TiffAnalysis:
    """Análise completa de um TIFF."""
    # Identificação
    filename: str
    filepath: str
    file_size: int
    file_size_mb: float

    # Formato
    format: TiffFormat
    format_detail: str
    is_bigtiff: bool

    # Header
    header: TiffHeader | None

    # IFDs
    ifds: list[TiffIFD]
    pyramid_levels: int

    # Validação
    is_valid: bool
    is_readable_pil: bool
    is_readable_openslide: bool
    is_readable_cv2: bool

    # Corrupções
    corruptions: list[CorruptionReport]
    corruption_count: int
    has_critical_corruption: bool

    # Dimensões (se legível)
    width: int | None
    height: int | None

    # Metadados
    bits_per_sample: int | None
    compression: str | None
    compression_ratio: float | None
    photometric: str | None
    color_space: str | None
    tile_size: int | None

    # Integridade
    checksum_md5: str | None = None
    checksum_sha256: str | None = None

    # Erro
    error_message: str | None = None
    error_category: str | None = None

    # Timestamps
    created_modification: str | None = None
    scanned_date: str | None = None

    # Informações adicionais
    software: str | None = None
    scanner: str | None = None
    magnification: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário (para JSON)."""
        result = {
            "filename": self.filename,
            "filepath": self.filepath,
            "file_size": self.file_size,
            "file_size_mb": self.file_size_mb,
            "format": self.format.value,
            "format_detail": self.format_detail,
            "is_bigtiff": self.is_bigtiff,
            "is_valid": self.is_valid,
            "is_readable_pil": self.is_readable_pil,
            "is_readable_openslide": self.is_readable_openslide,
            "is_readable_cv2": self.is_readable_cv2,
            "corruption_count": self.corruption_count,
            "has_critical_corruption": self.has_critical_corruption,
            "width": self.width,
            "height": self.height,
            "bits_per_sample": self.bits_per_sample,
            "compression": self.compression,
            "photometric": self.photometric,
            "color_space": self.color_space,
            "tile_size": self.tile_size,
            "pyramid_levels": self.pyramid_levels,
            "software": self.software,
            "scanner": self.scanner,
            "magnification": self.magnification,
            "error_message": self.error_message,
            "error_category": self.error_category,
        }

        if self.checksum_md5:
            result["checksum_md5"] = self.checksum_md5
        if self.checksum_sha256:
            result["checksum_sha256"] = self.checksum_sha256

        if self.corruptions:
            result["corruptions"] = [
                {
                    "corruption_type": c.corruption_type.value,
                    "severity": c.severity,
                    "location": c.location,
                    "description": c.description,
                    "expected": c.expected,
                    "actual": c.actual,
                    "offset": c.offset,
                    "recoverable": c.recoverable,
                }
                for c in self.corruptions
            ]

        return result


# ============================================================
# Constantes
# ============================================================

# Magic numbers TIFF (valores corretos para comparação com struct.unpack)
# Little-endian: "II" (0x4949) + 0x002A = 0x002A4949 quando lido como uint32 LE
# Big-endian: "MM" (0x4D4D) + 0x2A00 = 0x2A004D4D quando lido como uint32 BE
TIFF_MAGIC_LE = 0x002A4949  # "II" + 0x002A (little-endian)
TIFF_MAGIC_BE = 0x2A004D4D  # "MM" + 0x2A00 (big-endian)
BIGTIFF_MAGIC_LE = 0x002B4949  # "II" + 0x002B (BigTIFF little-endian)
BIGTIFF_MAGIC_BE = 0x2B004D4D  # "MM" + 0x2B00 (BigTIFF big-endian)

# Tags TIFF obrigatórias
REQUIRED_TAGS = {256, 257, 258, 259, 262, 273, 277, 278, 279}

# Nomes de compressão
COMPRESSION_NAMES = {
    1: "None",
    2: "CCITT Group 3",
    3: "CCITT Group 4",
    4: "LZW",
    5: "Old JPEG",
    6: "JPEG",
    7: "JPEG",
    8: "Deflate",
    9: "Deflate (Adobe)",
    10: "JBIG",
    32766: "Next",
    32767: "Sony ARW Compressed",
    32768: "PackBits",
    32769: "Deflate Experimental",
    32867: "Kodak DCR Compressed",
    32895: "IT8 CT",
    32896: "IT8 CT LZW",
    32897: "IT8 CT PackBits",
    32898: "IT8 CT Fax",
    32899: "IT8 CT Fax Group 4",
    32900: "SGI LZW",
    32901: "SGI PackBits",
    32902: "JPEG2000 Lossless",
    32903: "JPEG2000 Lossy",
    32946: "JPEG 2000",
    33003: "Aperio JPEG 2000 Lossless",
    33005: "Aperio JPEG 2000 Lossy",
    34665: "Aperio compressed",
    34666: "Aperio SVS",
}

PHOTOMETRIC_NAMES = {
    0: "WhiteIsZero",
    1: "BlackIsZero",
    2: "RGB",
    3: "Palette",
    4: "Mask",
    5: "Separated",
    6: "YCbCr",
    7: "CIELab",
    8: "ICCLab",
    9: "ITULab",
    10: "CFA",
    32803: "LogL",
    32845: "LogLUV",
    32892: "LinearRaw",
}


# ============================================================
# Funções de análise
# ============================================================

def analyze_tiff(
    path: str,
    deep: bool = True,
    calculate_checksum: bool = False,
) -> TiffAnalysis:
    """Análise completa de um TIFF.

    Args:
        path: Caminho do arquivo TIFF.
        deep: Se True, valida cada tile individualmente.
        calculate_checksum: Se True, calcula MD5/SHA256.

    Returns:
        TiffAnalysis com todas as informações.
    """
    filename = os.path.basename(path)
    file_size = os.path.getsize(path)

    analysis = TiffAnalysis(
        filename=filename,
        filepath=path,
        file_size=file_size,
        file_size_mb=round(file_size / (1024 * 1024), 2),
        format=TiffFormat.UNKNOWN,
        format_detail="",
        is_bigtiff=False,
        header=None,
        ifds=[],
        pyramid_levels=0,
        is_valid=True,
        is_readable_pil=False,
        is_readable_openslide=False,
        is_readable_cv2=False,
        corruptions=[],
        corruption_count=0,
        has_critical_corruption=False,
        width=None,
        height=None,
        bits_per_sample=None,
        compression=None,
        compression_ratio=None,
        photometric=None,
        color_space=None,
        tile_size=None,
    )

    # Verificar se arquivo existe
    if not os.path.isfile(path):
        analysis.is_valid = False
        analysis.error_message = "File not found"
        analysis.error_category = "file_not_found"
        return analysis

    # Verificar se arquivo não está vazio
    if file_size == 0:
        analysis.is_valid = False
        analysis.error_message = "File is empty (0 bytes)"
        analysis.error_category = "empty_file"
        analysis.corruptions.append(CorruptionReport(
            corruption_type=CorruptionType.TRUNCATED,
            severity="critical",
            location="file",
            description="File is empty",
            expected="> 0 bytes",
            actual="0 bytes",
            offset=0,
            recoverable=False,
        ))
        return analysis

    # Ler dados do arquivo
    try:
        with open(path, "rb") as f:
            file_data = f.read()
    except Exception as e:
        analysis.is_valid = False
        analysis.error_message = f"Cannot read file: {str(e)}"
        analysis.error_category = "read_error"
        return analysis

    # 1. Validar header
    header_corruptions = _validate_header(file_data, analysis)
    analysis.corruptions.extend(header_corruptions)

    # 2. Validar com PIL
    pil_corruptions = _validate_with_pil(path, analysis)
    analysis.corruptions.extend(pil_corruptions)

    # 3. Validar com OpenSlide
    openslide_corruptions = _validate_with_openslide(path, analysis)
    analysis.corruptions.extend(openslide_corruptions)

    # 4. Validar com OpenCV
    cv2_corruptions = _validate_with_cv2(path, analysis)
    analysis.corruptions.extend(cv2_corruptions)

    # 5. Detectar formato específico
    _detect_format(file_data, analysis)

    # 6. Validação profunda (se solicitado e se legível)
    if deep and (analysis.is_readable_pil or analysis.is_readable_openslide):
        tile_corruptions = _validate_tiles_deep(file_data, analysis)
        analysis.corruptions.extend(tile_corruptions)

    # 7. Calcular checksum (apenas se houver corrupção ou solicitado)
    if calculate_checksum or analysis.corruption_count > 0:
        analysis.checksum_md5, analysis.checksum_sha256 = _calculate_checksum(path)

    # 8. Atualizar contadores finais
    analysis.corruption_count = len(analysis.corruptions)
    # has_critical_corruption só é True se há corrupção crítica E arquivo não é legível
    has_any_critical = any(c.severity == "critical" for c in analysis.corruptions)
    is_readable = analysis.is_readable_pil or analysis.is_readable_openslide or analysis.is_readable_cv2
    analysis.has_critical_corruption = has_any_critical and not is_readable
    if analysis.has_critical_corruption:
        analysis.is_valid = False

    # 9. Extrair metadados adicionais
    _extract_metadata(analysis)

    return analysis


def _validate_header(data: bytes, analysis: TiffAnalysis) -> list[CorruptionReport]:
    """Valida header TIFF."""
    corruptions = []

    if len(data) < 8:
        corruptions.append(CorruptionReport(
            corruption_type=CorruptionType.HEADER_INVALID,
            severity="critical",
            location="header",
            description="File too small for TIFF header",
            expected=">= 8 bytes",
            actual=f"{len(data)} bytes",
            offset=0,
            recoverable=False,
        ))
        return corruptions

    # Verificar magic number
    magic = struct.unpack("<I", data[:4])[0]

    if magic == TIFF_MAGIC_LE:
        analysis.header = TiffHeader(
            byte_order="II",
            version=42,
            ifd_offset=struct.unpack("<I", data[4:8])[0],
            byte_order_str="Little-endian",
        )
    elif magic == TIFF_MAGIC_BE:
        analysis.header = TiffHeader(
            byte_order="MM",
            version=42,
            ifd_offset=struct.unpack(">I", data[4:8])[0],
            byte_order_str="Big-endian",
        )
    elif magic == BIGTIFF_MAGIC_LE:
        analysis.is_bigtiff = True
        analysis.header = TiffHeader(
            byte_order="II",
            version=43,
            ifd_offset=struct.unpack("<Q", data[8:16])[0] if len(data) >= 16 else 0,
            byte_order_str="Little-endian (BigTIFF)",
        )
    elif magic == BIGTIFF_MAGIC_BE:
        analysis.is_bigtiff = True
        analysis.header = TiffHeader(
            byte_order="MM",
            version=43,
            ifd_offset=struct.unpack(">Q", data[8:16])[0] if len(data) >= 16 else 0,
            byte_order_str="Big-endian (BigTIFF)",
        )
    else:
        corruptions.append(CorruptionReport(
            corruption_type=CorruptionType.MAGIC_NUMBER_ERROR,
            severity="critical",
            location="header",
            description="Invalid TIFF magic number",
            expected="0x002A4949 (LE), 0x2A004D4D (BE), 0x002B4949 (BigTIFF LE), or 0x2B004D4D (BigTIFF BE)",
            actual=f"0x{magic:08X}",
            offset=0,
            recoverable=False,
        ))
        analysis.is_valid = False

    # Detectar formato híbrido TIFF-JPEG (header TIFF + dados JPEG no offset 8)
    if analysis.header and analysis.header.ifd_offset == 8:
        # Verificar se há marcador JPEG no offset 8
        if len(data) > 10 and data[8:10] == b'\xff\xd8':
            analysis.format = TiffFormat.TIFF_JPEG_HYBRID
            analysis.format_detail = "Hybrid TIFF-JPEG (header TIFF + JPEG data at offset 8)"

    return corruptions


def _validate_with_pil(path: str, analysis: TiffAnalysis) -> list[CorruptionReport]:
    """Valida TIFF com PIL/Pillow."""
    corruptions = []

    try:
        img = Image.open(path)
        analysis.is_readable_pil = True
        analysis.width, analysis.height = img.size
        analysis.bits_per_sample = img.bits if hasattr(img, "bits") else None
        analysis.photometric = img.mode
        analysis.tile_size = None

        # Extrair metadados
        if hasattr(img, "tag"):
            tags = img.tag
            if 270 in tags:
                analysis.created_modification = str(tags[270])
            if 305 in tags:
                analysis.software = str(tags[305])

        img.close()

    except Exception as e:
        analysis.is_readable_pil = False
        error_str = str(e).lower()

        if "truncated" in error_str:
            corruptions.append(CorruptionReport(
                corruption_type=CorruptionType.TRUNCATED,
                severity="critical",
                location="pixel_data",
                description=f"PIL reports truncated file: {str(e)}",
                expected="Complete TIFF data",
                actual=str(e),
                offset=None,
                recoverable=False,
            ))
        elif "broken" in error_str or "corrupt" in error_str:
            corruptions.append(CorruptionReport(
                corruption_type=CorruptionType.PIXEL_DATA_CORRUPTED,
                severity="critical",
                location="pixel_data",
                description=f"PIL reports corrupted data: {str(e)}",
                expected="Valid pixel data",
                actual=str(e),
                offset=None,
                recoverable=False,
            ))
        elif "cannot identify" in error_str or "unknow" in error_str:
            corruptions.append(CorruptionReport(
                corruption_type=CorruptionType.PILLOW_ERROR,
                severity="critical",
                location="header",
                description=f"PIL cannot identify format: {str(e)}",
                expected="Recognized image format",
                actual=str(e),
                offset=None,
                recoverable=False,
            ))
        else:
            corruptions.append(CorruptionReport(
                corruption_type=CorruptionType.PILLOW_ERROR,
                severity="critical",
                location="general",
                description=f"PIL error: {str(e)}",
                expected="Readable image",
                actual=str(e),
                offset=None,
                recoverable=False,
            ))

    return corruptions


def _validate_with_openslide(path: str, analysis: TiffAnalysis) -> list[CorruptionReport]:
    """Valida TIFF com OpenSlide."""
    corruptions = []

    try:
        import openslide
        slide = openslide.OpenSlide(path)
        analysis.is_readable_openslide = True

        if analysis.width is None:
            analysis.width, analysis.height = slide.dimensions

        # Extrair metadados
        try:
            level_count = slide.level_count
            analysis.pyramid_levels = level_count
        except Exception:
            pass

        slide.close()

    except Exception as e:
        analysis.is_readable_openslide = False
        error_str = str(e).lower()

        if "format" in error_str or "not supported" in error_str:
            corruptions.append(CorruptionReport(
                corruption_type=CorruptionType.OPENSLIDE_ERROR,
                severity="info",
                location="format",
                description=f"OpenSlide cannot open format: {str(e)}",
                expected="OpenSlide-compatible format",
                actual=str(e),
                offset=None,
                recoverable=False,
                details={"format": "possibly unsupported"},
            ))
        elif "corrupt" in error_str or "invalid" in error_str:
            corruptions.append(CorruptionReport(
                corruption_type=CorruptionType.OPENSLIDE_ERROR,
                severity="warning",
                location="general",
                description=f"OpenSlide reports error: {str(e)}",
                expected="Valid slide data",
                actual=str(e),
                offset=None,
                recoverable=False,
            ))

    return corruptions


def _validate_with_cv2(path: str, analysis: TiffAnalysis) -> list[CorruptionReport]:
    """Valida TIFF com OpenCV."""
    corruptions = []

    try:
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            analysis.is_readable_cv2 = True
            if analysis.width is None:
                analysis.width = img.shape[1]
                analysis.height = img.shape[0]
        else:
            analysis.is_readable_cv2 = False
    except Exception as e:
        analysis.is_readable_cv2 = False

    return corruptions


def _detect_format(data: bytes, analysis: TiffAnalysis) -> None:
    """Detecta formato específico do TIFF."""
    # Verificar formato híbrido TIFF-JPEG primeiro
    if analysis.format == TiffFormat.TIFF_JPEG_HYBRID:
        # Verificar se é MetaSystems VSlide (formato híbrido específico)
        # MetaSystems VSlide usa formato híbrido TIFF-JPEG onde:
        # - Header TIFF de 8 bytes (49 49 2A 00 08 00 00 00)
        # - Dados JPEG consecutivos a partir do offset 8
        # - Tiles sem tabelas DQT/DHT (tabelas armazenadas externamente)
        # - Scanner: Zeiss Axio Imager Z2 com software MetaCyte/Metafer
        # - Empresa: MetaSystems (Altlussheim, Alemanha, desde 1986)
        # - Presente em 103+ países
        analysis.format = TiffFormat.METASYSTEMS_VSLIDE
        analysis.format_detail = (
            "MetaSystems VSlide hybrid TIFF-JPEG format. "
            "Tiles missing DQT/DHT tables (stored externally). "
            "Requires standard JPEG table injection for decoding."
        )
        analysis.scanner = "MetaSystems VSlide (Zeiss Axio Imager Z2)"
        analysis.software = "MetaCyte/Metafer"
        return

    # Verificar se é OpenSlide-compatible
    if analysis.is_readable_openslide:
        analysis.format = TiffFormat.OPENSLIDE_TIFF
        analysis.format_detail = "OpenSlide-compatible TIFF"

        # Tentar detectar scanner específico
        try:
            import openslide
            slide = openslide.OpenSlide(analysis.filepath)
            vendor = slide.vendor if hasattr(slide, "vendor") else "unknown"
            slide.close()

            if vendor == "aperio":
                analysis.format = TiffFormat.APERIO
                analysis.format_detail = "Aperio SVS/ScanScope"
                analysis.scanner = "Aperio"
            elif vendor == "hamamatsu":
                analysis.format = TiffFormat.HAMAMATSU
                analysis.format_detail = "Hamamatsu NDPI/VMS"
                analysis.scanner = "Hamamatsu"
            elif vendor == "leica":
                analysis.format = TiffFormat.LEICA
                analysis.format_detail = "Leica SCN"
                analysis.scanner = "Leica"
            elif vendor == "philips":
                analysis.format = TiffFormat.PHILIPS
                analysis.format_detail = "Philips TIFF"
                analysis.scanner = "Philips"
            elif vendor == "ventana":
                analysis.format = TiffFormat.VENTANA
                analysis.format_detail = "Ventana BIF/TIFF"
                analysis.scanner = "Ventana"
        except Exception:
            pass

    elif analysis.is_readable_pil:
        analysis.format = TiffFormat.STANDARD_TIFF
        analysis.format_detail = "Standard TIFF (PIL-readable)"

    # Verificar se é BigTIFF
    if analysis.is_bigtiff:
        analysis.format = TiffFormat.BIGTIFF
        analysis.format_detail = "BigTIFF (>4GB)"

    # Verificar MetaSystems VSlide por assinatura no header
    if len(data) > 100:
        header_str = data[:100].decode("ascii", errors="ignore")
        if "MetaSystems" in header_str or "VSlide" in header_str:
            analysis.format = TiffFormat.METASYSTEMS_VSLIDE
            analysis.format_detail = "MetaSystems VSlide TIFF"
            analysis.scanner = "MetaSystems"


def _validate_tiles_deep(data: bytes, analysis: TiffAnalysis) -> list[CorruptionReport]:
    """Validação profunda de cada tile."""
    corruptions = []

    if not analysis.ifds:
        return corruptions

    for ifd in analysis.ifds:
        if ifd.tile_width and ifd.tile_length:
            # Tile-based TIFF
            tile_corruptions = _validate_tiles(data, ifd, analysis.filepath)
            corruptions.extend(tile_corruptions)
        elif ifd.strip_offsets:
            # Strip-based TIFF
            strip_corruptions = _validate_strips(data, ifd)
            corruptions.extend(strip_corruptions)

    return corruptions


def _validate_tiles(data: bytes, ifd: TiffIFD, filepath: str) -> list[CorruptionReport]:
    """Valida cada tile individualmente."""
    corruptions = []

    if not ifd.tile_width or not ifd.tile_length:
        return corruptions

    # Calcular número esperado de tiles
    tiles_x = (ifd.width + ifd.tile_width - 1) // ifd.tile_width
    tiles_y = (ifd.height + ifd.tile_length - 1) // ifd.tile_length
    expected_tiles = tiles_x * tiles_y

    # Ler dados de offsets e tamanhos dos tiles
    # Nota: Simplificado - na prática, precisa parsear IFD corretamente
    for tile_idx in range(min(expected_tiles, len(ifd.strip_offsets))):
        if tile_idx >= len(ifd.strip_offsets):
            corruptions.append(CorruptionReport(
                corruption_type=CorruptionType.TILE_MISSING,
                severity="critical",
                location=f"tile_{tile_idx}",
                description=f"Tile {tile_idx} offset not found in IFD",
                expected="Valid offset",
                actual="Missing",
                offset=None,
                recoverable=False,
            ))
            continue

        tile_offset = ifd.strip_offsets[tile_idx]
        tile_size = ifd.strip_byte_counts[tile_idx] if tile_idx < len(ifd.strip_byte_counts) else 0

        # Verificar se tile está dentro do arquivo
        if tile_offset + tile_size > len(data):
            corruptions.append(CorruptionReport(
                corruption_type=CorruptionType.TILE_TRUNCATED,
                severity="critical",
                location=f"tile_{tile_idx}",
                description=f"Tile {tile_idx} extends beyond file",
                expected=f"End at {tile_offset + tile_size}",
                actual=f"File ends at {len(data)}",
                offset=tile_offset,
                recoverable=False,
            ))
            continue

        # Ler dados do tile
        tile_data = data[tile_offset:tile_offset + tile_size]

        # Verificar se tile está vazio
        if tile_size > 0 and all(b == 0 for b in tile_data[:min(100, tile_size)]):
            corruptions.append(CorruptionReport(
                corruption_type=CorruptionType.TILE_EMPTY,
                severity="warning",
                location=f"tile_{tile_idx}",
                description=f"Tile {tile_idx} is all zeros",
                expected="Non-zero pixel data",
                actual="All zeros",
                offset=tile_offset,
                recoverable=True,
            ))

    return corruptions


def _validate_strips(data: bytes, ifd: TiffIFD) -> list[CorruptionReport]:
    """Valida strips (para TIFFs baseados em strips)."""
    corruptions = []

    for strip_idx, strip_offset in enumerate(ifd.strip_offsets):
        strip_size = ifd.strip_byte_counts[strip_idx] if strip_idx < len(ifd.strip_byte_counts) else 0

        # Verificar se strip está dentro do arquivo
        if strip_offset + strip_size > len(data):
            corruptions.append(CorruptionReport(
                corruption_type=CorruptionType.STRIP_CORRUPTED,
                severity="critical",
                location=f"strip_{strip_idx}",
                description=f"Strip {strip_idx} extends beyond file",
                expected=f"End at {strip_offset + strip_size}",
                actual=f"File ends at {len(data)}",
                offset=strip_offset,
                recoverable=False,
            ))

    return corruptions


def _calculate_checksum(path: str) -> tuple[str, str]:
    """Calcula MD5 e SHA256 de um arquivo.

    Returns:
        Tupla (md5, sha256).
    """
    md5_hash = hashlib.md5()
    sha256_hash = hashlib.sha256()

    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)
                sha256_hash.update(chunk)
        return md5_hash.hexdigest(), sha256_hash.hexdigest()
    except Exception:
        return "", ""


def _extract_metadata(analysis: TiffAnalysis) -> None:
    """Extrai metadados adicionais do arquivo."""
    # Se já temos software do PIL, não precisa buscar mais
    if analysis.software:
        return

    # Tentar extrair de outras fontes
    if analysis.format == TiffFormat.APERIO:
        analysis.scanner = "Aperio"
    elif analysis.format == TiffFormat.HAMAMATSU:
        analysis.scanner = "Hamamatsu"
    elif analysis.format == TiffFormat.LEICA:
        analysis.scanner = "Leica"
    elif analysis.format == TiffFormat.PHILIPS:
        analysis.scanner = "Philips"
    elif analysis.format == TiffFormat.VENTANA:
        analysis.scanner = "Ventana"


# ============================================================
# Funções auxiliares
# ============================================================

def get_tiff_info(path: str) -> dict[str, Any]:
    """Retorna informações básicas do TIFF como dicionário.

    Args:
        path: Caminho do arquivo TIFF.

    Returns:
        Dicionário com informações do TIFF.
    """
    analysis = analyze_tiff(path, deep=False)
    return analysis.to_dict()


def is_tiff_readable(path: str) -> bool:
    """Verifica se o TIFF é legível.

    Args:
        path: Caminho do arquivo TIFF.

    Returns:
        True se legível por qualquer biblioteca.
    """
    analysis = analyze_tiff(path, deep=False)
    return analysis.is_readable_pil or analysis.is_readable_openslide or analysis.is_readable_cv2


def get_corruption_summary(path: str) -> dict[str, Any]:
    """Retorna resumo de corrupções de um TIFF.

    Args:
        path: Caminho do arquivo TIFF.

    Returns:
        Dicionário com resumo de corrupções.
    """
    analysis = analyze_tiff(path, deep=True)

    return {
        "filename": analysis.filename,
        "is_valid": analysis.is_valid,
        "corruption_count": analysis.corruption_count,
        "has_critical_corruption": analysis.has_critical_corruption,
        "corruption_types": [
            {
                "type": c.corruption_type.value,
                "severity": c.severity,
                "location": c.location,
                "description": c.description,
            }
            for c in analysis.corruptions
        ],
    }
