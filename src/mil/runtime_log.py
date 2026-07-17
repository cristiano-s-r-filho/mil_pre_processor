"""Runtime logging separado para análise posterior.

Salva logs de execução em formato estruturado (JSON Lines) para:
- Arquivo TIFF sendo processado
- Informações de trabalho (stain, paciente, seções)
- Warnings de processamento
- Erros de processamento

Cada linha é um JSON válido para facilitar parsing posterior.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

RUNTIME_LOG_DIR = "_runtime_logs"


class RuntimeLogger:
    """Logger de runtime para análise posterior."""

    def __init__(self, log_root: str, run_id: str):
        """Inicializa o logger de runtime.

        Args:
            log_root: Diretório raiz dos logs.
            run_id: ID da execução (timestamp_alelo).
        """
        self.log_dir = os.path.join(log_root, RUNTIME_LOG_DIR)
        os.makedirs(self.log_dir, exist_ok=True)

        self.run_id = run_id
        self.start_time = datetime.now(tz=timezone.utc)

        # Arquivos de log separados
        self._file_log = self._open_log("files.jsonl")
        self._warning_log = self._open_log("warnings.jsonl")
        self._error_log = self._open_log("errors.jsonl")
        self._summary_log = self._open_log("summary.jsonl")

        # Contadores
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "warnings": 0,
            "errors": 0,
            "stains": {"HE": 0, "PAS": 0},
            "patients": set(),
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()
        return False

    def _open_log(self, filename: str):
        """Abre arquivo de log para append."""
        path = os.path.join(self.log_dir, f"{self.run_id}_{filename}")
        return open(path, "a", encoding="utf-8")

    def _write_log(self, log_file, data: dict[str, Any]) -> None:
        """Escreve uma linha JSON no log."""
        data["timestamp"] = datetime.now(tz=timezone.utc).isoformat()
        log_file.write(json.dumps(data, ensure_ascii=False) + "\n")
        log_file.flush()

    def log_file_start(
        self,
        filename: str,
        patient: str | None = None,
        image: str | None = None,
        alelo: str | None = None,
    ) -> None:
        """Registra início do processamento de um arquivo.

        Args:
            filename: Nome do arquivo TIFF.
            patient: ID do paciente.
            image: Número da imagem.
            alelo: Nome do alelo.
        """
        self.stats["total_files"] += 1
        if patient:
            self.stats["patients"].add(patient)

        self._write_log(self._file_log, {
            "event": "file_start",
            "filename": filename,
            "patient": patient,
            "image": image,
            "alelo": alelo,
        })

    def log_file_ok(
        self,
        filename: str,
        stain: str,
        sections: int,
        has_multiple: bool,
        patient: str | None = None,
        image: str | None = None,
        alelo: str | None = None,
        processing_time_ms: float | None = None,
        file_size_mb: float | None = None,
        width: int | None = None,
        height: int | None = None,
        tiff_analysis: dict | None = None,
    ) -> None:
        """Registra processamento bem-sucedido.

        Args:
            filename: Nome do arquivo TIFF.
            stain: Tipo de stain (HE/PAS).
            sections: Número de seções detectadas.
            has_multiple: Se há múltiplas seções.
            patient: ID do paciente.
            image: Número da imagem.
            alelo: Nome do alelo.
            processing_time_ms: Tempo de processamento em milissegundos.
            file_size_mb: Tamanho do arquivo em MB.
            width: Largura da imagem em pixels.
            height: Altura da imagem em pixels.
            tiff_analysis: Análise TIFF (TiffAnalysis.to_dict()) se disponível.
        """
        self.stats["processed_files"] += 1
        self.stats["stains"][stain] = self.stats["stains"].get(stain, 0) + 1

        data = {
            "event": "file_ok",
            "filename": filename,
            "patient": patient,
            "image": image,
            "stain": stain,
            "sections": sections,
            "has_multiple": has_multiple,
            "alelo": alelo,
        }

        if processing_time_ms is not None:
            data["processing_time_ms"] = round(processing_time_ms, 2)
        if file_size_mb is not None:
            data["file_size_mb"] = round(file_size_mb, 2)
        if width is not None:
            data["width"] = width
        if height is not None:
            data["height"] = height
        if tiff_analysis is not None:
            data["tiff_analysis"] = tiff_analysis

        self._write_log(self._file_log, data)

    def log_warning(
        self,
        message: str,
        filename: str | None = None,
        patient: str | None = None,
        image: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Registra um warning.

        Args:
            message: Mensagem de warning.
            filename: Arquivo relacionado.
            patient: ID do paciente.
            image: Número da imagem.
            details: Detalhes adicionais.
        """
        self.stats["warnings"] += 1

        data = {
            "event": "warning",
            "message": message,
            "filename": filename,
            "patient": patient,
            "image": image,
        }
        if details:
            data["details"] = details

        self._write_log(self._warning_log, data)

        # Também log no Python logging padrão
        logger.warning(message)

    def log_skipped(
        self,
        reason: str,
        filename: str | None = None,
        patient: str | None = None,
        image: str | None = None,
        tiff_analysis: dict | None = None,
        skip_category: str | None = None,
    ) -> None:
        """Registra um arquivo pulado (formato não suportado, etc).

        Args:
            reason: Motivo do skip.
            filename: Arquivo relacionado.
            patient: ID do paciente.
            image: Número da imagem.
            tiff_analysis: Análise TIFF (TiffAnalysis.to_dict()) se disponível.
            skip_category: Categoria do skip (ex: "unsupported_format", "corrupted").
        """
        self.stats["errors"] += 1  # Contar como erro para estatísticas

        data = {
            "event": "skipped",
            "reason": reason,
            "filename": filename,
            "patient": patient,
            "image": image,
        }
        if tiff_analysis is not None:
            data["tiff_analysis"] = tiff_analysis
        if skip_category is not None:
            data["skip_category"] = skip_category

        self._write_log(self._error_log, data)

        # Também log no Python logging padrão
        logger.warning("SKIPPED: %s - %s", filename, reason)

    def log_error(
        self,
        message: str,
        filename: str | None = None,
        patient: str | None = None,
        image: str | None = None,
        exception: Exception | None = None,
        details: dict | None = None,
        tiff_analysis: dict | None = None,
        corruption_type: str | None = None,
        error_category: str | None = None,
    ) -> None:
        """Registra um erro.

        Args:
            message: Mensagem de erro.
            filename: Arquivo relacionado.
            patient: ID do paciente.
            image: Número da imagem.
            exception: Exceção capturada.
            details: Detalhes adicionais.
            tiff_analysis: Análise TIFF (TiffAnalysis.to_dict()) se disponível.
            corruption_type: Tipo de corrupção (CorruptionType.value) se disponível.
            error_category: Categoria do erro (ex: "tiff", "processing", "memory").
        """
        self.stats["errors"] += 1

        data = {
            "event": "error",
            "message": message,
            "filename": filename,
            "patient": patient,
            "image": image,
        }
        if exception:
            data["exception"] = str(exception)
            data["exception_type"] = type(exception).__name__
            import traceback
            data["exception_traceback"] = traceback.format_exc()
        if details:
            data["details"] = details
        if tiff_analysis is not None:
            data["tiff_analysis"] = tiff_analysis
        if corruption_type is not None:
            data["corruption_type"] = corruption_type
        if error_category is not None:
            data["error_category"] = error_category

        self._write_log(self._error_log, data)

        # Também log no Python logging padrão
        logger.error(message)

    def log_phase_start(self, phase: str, detail: str = "") -> None:
        """Registra início de uma fase.

        Args:
            phase: Nome da fase (ex: "phase1", "phase2").
            detail: Detalhes adicionais.
        """
        self._write_log(self._summary_log, {
            "event": "phase_start",
            "phase": phase,
            "detail": detail,
        })

    def log_phase_end(self, phase: str, duration: float) -> None:
        """Registra fim de uma fase.

        Args:
            phase: Nome da fase.
            duration: Duração em segundos.
        """
        self._write_log(self._summary_log, {
            "event": "phase_end",
            "phase": phase,
            "duration_seconds": round(duration, 3),
        })

    def finish(self) -> str:
        """Finaliza o logger e salva resumo.

        Returns:
            Caminho do diretório de logs.
        """
        end_time = datetime.now(tz=timezone.utc)
        duration = (end_time - self.start_time).total_seconds()

        # Salvar resumo final
        self._write_log(self._summary_log, {
            "event": "run_complete",
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration, 3),
            "total_files": self.stats["total_files"],
            "processed_files": self.stats["processed_files"],
            "warnings": self.stats["warnings"],
            "errors": self.stats["errors"],
            "stains": self.stats["stains"],
            "patients_count": len(self.stats["patients"]),
        })

        # Fechar arquivos (ignorar erros se ja fechados)
        for f in [self._file_log, self._warning_log, self._error_log, self._summary_log]:
            try:
                if not f.closed:
                    f.close()
            except Exception:
                pass

        return self.log_dir

    def get_stats(self) -> dict:
        """Retorna estatísticas atuais."""
        return {
            "total_files": self.stats["total_files"],
            "processed_files": self.stats["processed_files"],
            "warnings": self.stats["warnings"],
            "errors": self.stats["errors"],
            "stains": dict(self.stats["stains"]),
            "patients_count": len(self.stats["patients"]),
        }


def load_runtime_logs(log_root: str, run_id: str) -> dict:
    """Carrega logs de runtime de uma execução.

    Args:
        log_root: Diretório raiz dos logs.
        run_id: ID da execução.

    Returns:
        Dicionário com todos os logs.
    """
    log_dir = os.path.join(log_root, RUNTIME_LOG_DIR)

    result = {
        "files": [],
        "warnings": [],
        "errors": [],
        "summary": [],
    }

    for log_type in ["files", "warnings", "errors", "summary"]:
        path = os.path.join(log_dir, f"{run_id}_{log_type}.jsonl")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        result[log_type].append(json.loads(line))

    return result


def list_runtime_logs(log_root: str) -> list[str]:
    """Lista IDs de execuções com logs de runtime.

    Args:
        log_root: Diretório raiz dos logs.

    Returns:
        Lista de run_ids.
    """
    log_dir = os.path.join(log_root, RUNTIME_LOG_DIR)
    if not os.path.isdir(log_dir):
        return []

    run_ids = set()
    for filename in os.listdir(log_dir):
        if filename.endswith("_summary.jsonl"):
            run_id = filename.replace("_summary.jsonl", "")
            run_ids.add(run_id)

    return sorted(run_ids)
