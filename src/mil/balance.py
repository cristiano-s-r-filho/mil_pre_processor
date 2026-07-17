"""Análise de balanceamento entre alelos e stains.

Fornece análise detalhada de distribuição de imagens e seções
entre alelos (0alelos, 1alelo, 2alelos) e tipos de stain (HE, PAS).
"""

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AleloBalance:
    """Análise de balanceamento para um alelo."""
    alelo: str
    total_images: int
    total_sections: int
    total_patients: int

    # Distribuição por stain
    he_images: int
    pas_images: int
    he_sections: int
    pas_sections: int

    # Métricas de balanceamento
    percentage_of_total_images: float
    percentage_of_total_sections: float
    ratio_to_average_images: float
    ratio_to_average_sections: float

    # Seções por imagem
    sections_per_image_avg: float
    sections_per_image_max: int
    sections_per_image_min: int

    # Status
    is_balanced: bool
    imbalance_level: str  # "ok", "warning", "critical"
    imbalance_details: str

    # Pacientes
    patients_processed: int
    patients_with_errors: int
    processing_rate: float

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário (para JSON)."""
        return {
            "alelo": self.alelo,
            "total_images": self.total_images,
            "total_sections": self.total_sections,
            "total_patients": self.total_patients,
            "he_images": self.he_images,
            "pas_images": self.pas_images,
            "he_sections": self.he_sections,
            "pas_sections": self.pas_sections,
            "percentage_of_total_images": round(self.percentage_of_total_images, 2),
            "percentage_of_total_sections": round(self.percentage_of_total_sections, 2),
            "ratio_to_average_images": round(self.ratio_to_average_images, 2),
            "ratio_to_average_sections": round(self.ratio_to_average_sections, 2),
            "sections_per_image_avg": round(self.sections_per_image_avg, 2),
            "sections_per_image_max": self.sections_per_image_max,
            "sections_per_image_min": self.sections_per_image_min,
            "is_balanced": self.is_balanced,
            "imbalance_level": self.imbalance_level,
            "imbalance_details": self.imbalance_details,
            "patients_processed": self.patients_processed,
            "patients_with_errors": self.patients_with_errors,
            "processing_rate": round(self.processing_rate, 2),
        }


@dataclass
class StainBalance:
    """Análise de balanceamento para um stain."""
    stain: str
    total_images: int
    total_sections: int

    # Métricas
    percentage_of_total_images: float
    percentage_of_total_sections: float

    # Por alelo
    images_per_alelo: dict[str, int]
    sections_per_alelo: dict[str, int]

    # Status
    is_balanced: bool
    imbalance_level: str
    imbalance_details: str

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário (para JSON)."""
        return {
            "stain": self.stain,
            "total_images": self.total_images,
            "total_sections": self.total_sections,
            "percentage_of_total_images": round(self.percentage_of_total_images, 2),
            "percentage_of_total_sections": round(self.percentage_of_total_sections, 2),
            "images_per_alelo": self.images_per_alelo,
            "sections_per_alelo": self.sections_per_alelo,
            "is_balanced": self.is_balanced,
            "imbalance_level": self.imbalance_level,
            "imbalance_details": self.imbalance_details,
        }


@dataclass
class PatientReport:
    """Relatório detalhado por paciente."""
    patient_id: str
    total_images: int
    processed_images: int
    error_images: int

    # Por stain
    he_images: int
    pas_images: int
    he_sections: int
    pas_sections: int

    # Por alelo
    alelo: str

    # Seções
    total_sections: int
    sections_per_image_avg: float
    sections_per_image_max: int
    sections_per_image_min: int

    # Corrupção
    corrupted_images: int
    corruption_types: dict[str, int]

    # Prontos para patching
    images_s0: int
    images_n0: int
    total_polygons: int

    # Status
    processing_status: str  # "complete", "partial", "failed"

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário (para JSON)."""
        return {
            "patient_id": self.patient_id,
            "total_images": self.total_images,
            "processed_images": self.processed_images,
            "error_images": self.error_images,
            "he_images": self.he_images,
            "pas_images": self.pas_images,
            "he_sections": self.he_sections,
            "pas_sections": self.pas_sections,
            "alelo": self.alelo,
            "total_sections": self.total_sections,
            "sections_per_image_avg": round(self.sections_per_image_avg, 2),
            "sections_per_image_max": self.sections_per_image_max,
            "sections_per_image_min": self.sections_per_image_min,
            "corrupted_images": self.corrupted_images,
            "corruption_types": self.corruption_types,
            "images_s0": self.images_s0,
            "images_n0": self.images_n0,
            "total_polygons": self.total_polygons,
            "processing_status": self.processing_status,
        }


@dataclass
class BalanceReport:
    """Relatório completo de balanceamento."""
    # Totais gerais
    total_images: int
    total_sections: int
    total_patients: int

    # Por alelo
    alelos: dict[str, AleloBalance]

    # Por stain
    stains: dict[str, StainBalance]

    # Por paciente
    patients: list[PatientReport]

    # Métricas gerais
    expected_images_per_alelo: float
    expected_sections_per_alelo: float
    std_deviation_images: float
    std_deviation_sections: float
    coefficient_of_variation_images: float
    coefficient_of_variation_sections: float

    # Balanceamento de alelos
    alelo_imbalance_detected: bool
    alelo_imbalance_severity: str  # "none", "warning", "critical"
    alelo_imbalance_details: str
    alelo_recommendation: str

    # Balanceamento de stains
    stain_imbalance_detected: bool
    stain_imbalance_severity: str
    stain_imbalance_details: str
    stain_recommendation: str

    # Resumo de processamento
    processing_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário (para JSON)."""
        return {
            "total_images": self.total_images,
            "total_sections": self.total_sections,
            "total_patients": self.total_patients,
            "alelos": {k: v.to_dict() for k, v in self.alelos.items()},
            "stains": {k: v.to_dict() for k, v in self.stains.items()},
            "patients": [p.to_dict() for p in self.patients],
            "expected_images_per_alelo": round(self.expected_images_per_alelo, 2),
            "expected_sections_per_alelo": round(self.expected_sections_per_alelo, 2),
            "std_deviation_images": round(self.std_deviation_images, 2),
            "std_deviation_sections": round(self.std_deviation_sections, 2),
            "coefficient_of_variation_images": round(self.coefficient_of_variation_images, 2),
            "coefficient_of_variation_sections": round(self.coefficient_of_variation_sections, 2),
            "alelo_imbalance_detected": self.alelo_imbalance_detected,
            "alelo_imbalance_severity": self.alelo_imbalance_severity,
            "alelo_imbalance_details": self.alelo_imbalance_details,
            "alelo_recommendation": self.alelo_recommendation,
            "stain_imbalance_detected": self.stain_imbalance_detected,
            "stain_imbalance_severity": self.stain_imbalance_severity,
            "stain_imbalance_details": self.stain_imbalance_details,
            "stain_recommendation": self.stain_recommendation,
            "processing_summary": self.processing_summary,
        }


def generate_balance_report(
    runtime_logs: dict,
    alelos_validos: list[str],
) -> BalanceReport:
    """Gera relatório completo de balanceamento.

    Args:
        runtime_logs: Logs de runtime carregados.
        alelos_validos: Lista de alelos válidos.

    Returns:
        BalanceReport com análise completa.
    """
    files_log = runtime_logs.get("files", [])
    errors_log = runtime_logs.get("errors", [])

    # Agrupar por alelo
    alelo_data: dict[str, dict[str, Any]] = {}
    for alelo in alelos_validos:
        alelo_data[alelo] = {
            "images": 0,
            "sections": 0,
            "patients": set(),
            "he_images": 0,
            "pas_images": 0,
            "he_sections": 0,
            "pas_sections": 0,
            "processed": 0,
            "errors": 0,
            "sections_list": [],
        }

    # Processar logs
    for entry in files_log:
        event = entry.get("event")
        filename = entry.get("filename", "")
        patient = entry.get("patient", "")

        # Determinar alelo:优先使用 entry.get("alelo"), fallback para filename
        alelo = entry.get("alelo")
        if not alelo or alelo not in alelos_validos:
            alelo = _extract_alelo_from_filename(filename, alelos_validos)
        if alelo is None:
            continue

        if event == "file_start":
            alelo_data[alelo]["images"] += 1
            if patient:
                alelo_data[alelo]["patients"].add(patient)

        elif event == "file_ok":
            stain = entry.get("stain", "")
            sections = entry.get("sections", 0)

            alelo_data[alelo]["processed"] += 1
            alelo_data[alelo]["sections"] += sections
            alelo_data[alelo]["sections_list"].append(sections)

            if stain == "HE":
                alelo_data[alelo]["he_images"] += 1
                alelo_data[alelo]["he_sections"] += sections
            elif stain == "PAS":
                alelo_data[alelo]["pas_images"] += 1
                alelo_data[alelo]["pas_sections"] += sections

    # Processar erros
    for entry in errors_log:
        filename = entry.get("filename", "")
        alelo = entry.get("alelo")
        if not alelo or alelo not in alelos_validos:
            alelo = _extract_alelo_from_filename(filename, alelos_validos)
        if alelo:
            alelo_data[alelo]["errors"] += 1

    # Calcular totais
    total_images = sum(d["images"] for d in alelo_data.values())
    total_sections = sum(d["sections"] for d in alelo_data.values())
    total_patients = len(set().union(*[d["patients"] for d in alelo_data.values()]))

    # Calcular métricas esperadas
    num_alelos = len(alelos_validos) if alelos_validos else 1
    expected_images = total_images / num_alelos if num_alelos > 0 else 0
    expected_sections = total_sections / num_alelos if num_alelos > 0 else 0

    # Criar AleloBalance para cada alelo
    alelo_balances: dict[str, AleloBalance] = {}
    image_counts = []
    section_counts = []

    for alelo, data in alelo_data.items():
        image_counts.append(data["images"])
        section_counts.append(data["sections"])

        # Calcular seções por imagem
        sections_list = data["sections_list"]
        sections_avg = sum(sections_list) / len(sections_list) if sections_list else 0
        sections_max = max(sections_list) if sections_list else 0
        sections_min = min(sections_list) if sections_list else 0

        # Calcular percentuais
        pct_images = (data["images"] / total_images * 100) if total_images > 0 else 0
        pct_sections = (data["sections"] / total_sections * 100) if total_sections > 0 else 0

        # Calcular razão em relação à média
        ratio_images = (data["images"] / expected_images) if expected_images > 0 else 0
        ratio_sections = (data["sections"] / expected_sections) if expected_sections > 0 else 0

        # Determinar nível de desbalanceamento
        deviation = abs(pct_images - (100 / num_alelos))
        if deviation > 50:
            imbalance_level = "critical"
            imbalance_details = f"Desvio de {deviation:.1f}% do esperado"
        elif deviation > 20:
            imbalance_level = "warning"
            imbalance_details = f"Desvio de {deviation:.1f}% do esperado"
        else:
            imbalance_level = "ok"
            imbalance_details = "Dentro do esperado"

        # Calcular taxa de processamento
        processing_rate = (data["processed"] / data["images"] * 100) if data["images"] > 0 else 0

        alelo_balances[alelo] = AleloBalance(
            alelo=alelo,
            total_images=data["images"],
            total_sections=data["sections"],
            total_patients=len(data["patients"]),
            he_images=data["he_images"],
            pas_images=data["pas_images"],
            he_sections=data["he_sections"],
            pas_sections=data["pas_sections"],
            percentage_of_total_images=pct_images,
            percentage_of_total_sections=pct_sections,
            ratio_to_average_images=ratio_images,
            ratio_to_average_sections=ratio_sections,
            sections_per_image_avg=sections_avg,
            sections_per_image_max=sections_max,
            sections_per_image_min=sections_min,
            is_balanced=imbalance_level == "ok",
            imbalance_level=imbalance_level,
            imbalance_details=imbalance_details,
            patients_processed=data["processed"],
            patients_with_errors=data["errors"],
            processing_rate=processing_rate,
        )

    # Calcular desvio padrão e coeficiente de variação
    std_images = _calculate_std(image_counts)
    std_sections = _calculate_std(section_counts)
    cv_images = (std_images / expected_images) if expected_images > 0 else 0
    cv_sections = (std_sections / expected_sections) if expected_sections > 0 else 0

    # Determinar desbalanceamento geral de alelos
    alelo_imbalance_detected = any(
        b.imbalance_level in ("warning", "critical") for b in alelo_balances.values()
    )
    alelo_imbalance_severity = "none"
    alelo_imbalance_details = ""
    alelo_recommendation = ""

    if any(b.imbalance_level == "critical" for b in alelo_balances.values()):
        alelo_imbalance_severity = "critical"
        critical_alelos = [b.alelo for b in alelo_balances.values() if b.imbalance_level == "critical"]
        alelo_imbalance_details = (
            f"Desbalanceamento crítico detectado: {', '.join(critical_alelos)}. "
            f"Desvio padrão: {std_images:.1f} imagens (CV: {cv_images:.2f})"
        )
        alelo_recommendation = (
            "Verificar se todos os arquivos de cada alelo foram processados corretamente. "
            "Considerar reprocessar alelos com poucos dados."
        )
    elif alelo_imbalance_detected:
        alelo_imbalance_severity = "warning"
        alelo_imbalance_details = (
            f"Desbalanceamento moderado detectado. "
            f"Desvio padrão: {std_images:.1f} imagens (CV: {cv_images:.2f})"
        )
        alelo_recommendation = "Monitorar distribuição e considerar reprocessamento se necessário."

    # Criar StainBalance
    stain_balances = _generate_stain_balance(alelo_balances, total_images, total_sections)

    # Determinar desbalanceamento de stains
    stain_imbalance_detected = any(
        s.imbalance_level in ("warning", "critical") for s in stain_balances.values()
    )
    stain_imbalance_severity = "none"
    stain_imbalance_details = ""
    stain_recommendation = ""

    if stain_imbalance_detected:
        dominant_stains = [s.stain for s in stain_balances.values() if s.percentage_of_total_images > 70]
        if dominant_stains:
            stain_imbalance_severity = "warning"
            stain_imbalance_details = (
                f"Dominância de stain {dominant_stains[0]} detectada. "
                f"Verificar se distribuição é esperada."
            )
            stain_recommendation = "Considerar se dominância é devido à natureza dos dados ou a problemas de processamento."

    # Criar PatientReports
    patient_reports = _generate_patient_reports(runtime_logs, alelo_balances)

    # Resumo de processamento
    processing_summary = {
        "total_images": total_images,
        "processed_images": sum(d["processed"] for d in alelo_data.values()),
        "error_images": sum(d["errors"] for d in alelo_data.values()),
        "processing_rate": (
            sum(d["processed"] for d in alelo_data.values()) / total_images * 100
            if total_images > 0 else 0
        ),
    }

    return BalanceReport(
        total_images=total_images,
        total_sections=total_sections,
        total_patients=total_patients,
        alelos=alelo_balances,
        stains=stain_balances,
        patients=patient_reports,
        expected_images_per_alelo=expected_images,
        expected_sections_per_alelo=expected_sections,
        std_deviation_images=std_images,
        std_deviation_sections=std_sections,
        coefficient_of_variation_images=cv_images,
        coefficient_of_variation_sections=cv_sections,
        alelo_imbalance_detected=alelo_imbalance_detected,
        alelo_imbalance_severity=alelo_imbalance_severity,
        alelo_imbalance_details=alelo_imbalance_details,
        alelo_recommendation=alelo_recommendation,
        stain_imbalance_detected=stain_imbalance_detected,
        stain_imbalance_severity=stain_imbalance_severity,
        stain_imbalance_details=stain_imbalance_details,
        stain_recommendation=stain_recommendation,
        processing_summary=processing_summary,
    )


def _extract_alelo_from_filename(filename: str, alelos_validos: list[str]) -> str | None:
    """Extrai o alelo de um nome de arquivo.

    Args:
        filename: Nome do arquivo.
        alelos_validos: Lista de alelos válidos.

    Returns:
        Nome do alelo ou None.
    """
    filename_lower = filename.lower()
    for alelo in alelos_validos:
        if alelo.lower() in filename_lower:
            return alelo

    # Tentar extrair de caminhos
    # Exemplo: "0alelos/ID1224/..."
    for alelo in alelos_validos:
        if alelo.lower() + "/" in filename_lower or alelo.lower() + "\\" in filename_lower:
            return alelo

    return None


def _calculate_std(values: list[float]) -> float:
    """Calcula desvio padrão."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def _generate_stain_balance(
    alelo_balances: dict[str, AleloBalance],
    total_images: int,
    total_sections: int,
) -> dict[str, StainBalance]:
    """Gera balanceamento por stain."""
    stain_data: dict[str, dict[str, Any]] = {
        "HE": {"images": 0, "sections": 0, "per_alelo": {}},
        "PAS": {"images": 0, "sections": 0, "per_alelo": {}},
    }

    for alelo, balance in alelo_balances.items():
        stain_data["HE"]["images"] += balance.he_images
        stain_data["HE"]["sections"] += balance.he_sections
        stain_data["HE"]["per_alelo"][alelo] = balance.he_images

        stain_data["PAS"]["images"] += balance.pas_images
        stain_data["PAS"]["sections"] += balance.pas_sections
        stain_data["PAS"]["per_alelo"][alelo] = balance.pas_images

    stain_balances: dict[str, StainBalance] = {}

    for stain, data in stain_data.items():
        pct_images = (data["images"] / total_images * 100) if total_images > 0 else 0
        pct_sections = (data["sections"] / total_sections * 100) if total_sections > 0 else 0

        # Determinar nível de desbalanceamento
        if pct_images > 70 or pct_images < 30:
            imbalance_level = "warning"
            imbalance_details = f"Stain {stain} representa {pct_images:.1f}% das imagens"
        else:
            imbalance_level = "ok"
            imbalance_details = "Distribuição equilibrada"

        stain_balances[stain] = StainBalance(
            stain=stain,
            total_images=data["images"],
            total_sections=data["sections"],
            percentage_of_total_images=pct_images,
            percentage_of_total_sections=pct_sections,
            images_per_alelo=data["per_alelo"],
            sections_per_alelo={k: v for k, v in data["per_alelo"].items()},
            is_balanced=imbalance_level == "ok",
            imbalance_level=imbalance_level,
            imbalance_details=imbalance_details,
        )

    return stain_balances


def _generate_patient_reports(
    runtime_logs: dict,
    alelo_balances: dict[str, AleloBalance],
) -> list[PatientReport]:
    """Gera relatórios por paciente."""
    files_log = runtime_logs.get("files", [])
    errors_log = runtime_logs.get("errors", [])

    # Agrupar por paciente
    patient_data: dict[str, dict[str, Any]] = {}

    for entry in files_log:
        event = entry.get("event")
        patient = entry.get("patient")
        if not patient:
            continue

        if patient not in patient_data:
            patient_data[patient] = {
                "total": 0,
                "processed": 0,
                "errors": 0,
                "he_images": 0,
                "pas_images": 0,
                "he_sections": 0,
                "pas_sections": 0,
                "sections": [],
                "corrupted": 0,
                "corruption_types": {},
                "s0": 0,
                "n0": 0,
                "polygons": 0,
                "alelo": entry.get("alelo", ""),
            }

        if not patient_data[patient]["alelo"]:
            patient_data[patient]["alelo"] = entry.get("alelo", "")

        if event == "file_start":
            patient_data[patient]["total"] += 1

        elif event == "file_ok":
            stain = entry.get("stain", "")
            sections = entry.get("sections", 0)
            has_multiple = entry.get("has_multiple", False)

            patient_data[patient]["processed"] += 1
            patient_data[patient]["sections"].append(sections)
            patient_data[patient]["polygons"] += sections

            if stain == "HE":
                patient_data[patient]["he_images"] += 1
                patient_data[patient]["he_sections"] += sections
            elif stain == "PAS":
                patient_data[patient]["pas_images"] += 1
                patient_data[patient]["pas_sections"] += sections

            if has_multiple:
                patient_data[patient]["s0"] += 1
            else:
                patient_data[patient]["n0"] += 1

    # Processar erros
    for entry in errors_log:
        patient = entry.get("patient")
        if patient and patient in patient_data:
            patient_data[patient]["errors"] += 1
            patient_data[patient]["corrupted"] += 1

            error_msg = entry.get("message", "unknown")
            corruption_type = entry.get("error_category", "unknown")
            patient_data[patient]["corruption_types"][corruption_type] = (
                patient_data[patient]["corruption_types"].get(corruption_type, 0) + 1
            )

    # Criar PatientReport para cada paciente
    patient_reports = []

    for patient_id, data in patient_data.items():
        sections_list = data["sections"]
        sections_avg = sum(sections_list) / len(sections_list) if sections_list else 0
        sections_max = max(sections_list) if sections_list else 0
        sections_min = min(sections_list) if sections_list else 0

        # Determinar status
        if data["processed"] == data["total"]:
            status = "complete"
        elif data["processed"] > 0:
            status = "partial"
        else:
            status = "failed"

        alelo = data["alelo"] or "unknown"

        patient_reports.append(PatientReport(
            patient_id=patient_id,
            total_images=data["total"],
            processed_images=data["processed"],
            error_images=data["errors"],
            he_images=data["he_images"],
            pas_images=data["pas_images"],
            he_sections=data["he_sections"],
            pas_sections=data["pas_sections"],
            alelo=alelo,
            total_sections=sum(sections_list),
            sections_per_image_avg=sections_avg,
            sections_per_image_max=sections_max,
            sections_per_image_min=sections_min,
            corrupted_images=data["corrupted"],
            corruption_types=data["corruption_types"],
            images_s0=data["s0"],
            images_n0=data["n0"],
            total_polygons=data["polygons"],
            processing_status=status,
        ))

    # Ordenar por ID do paciente
    patient_reports.sort(key=lambda p: p.patient_id)

    return patient_reports
