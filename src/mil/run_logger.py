import json
import logging
import os
from datetime import datetime, timezone

LOG_DIR = "_logs"
RUNS_FILE = "runs.json"

logger = logging.getLogger(__name__)


def _load_runs(log_dir: str) -> list:
    path = os.path.join(log_dir, RUNS_FILE)
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return []


def _save_runs(log_dir: str, runs: list) -> None:
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, RUNS_FILE)
    with open(path, "w") as f:
        json.dump(runs, f, indent=2)


def next_run_id(alelo: str) -> str:
    now = datetime.now(tz=timezone.utc)
    return f"{now.strftime('%Y%m%d_%H%M%S')}_{alelo}"


def create_run(run_id: str, alelo: str, log_root: str) -> dict:
    return {
        "run_id": run_id,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "alelo": alelo,
        "total": 0,
        "ok": 0,
        "errors": 0,
        "cortados": 0,
        "files": [],
    }


def log_file(
    run: dict,
    filename: str,
    status: str,
    reason: str | None = None,
    patient: str | None = None,
    image: str | None = None,
    stain: str | None = None,
    sections: int | None = None,
    has_multiple: bool | None = None,
) -> None:
    entry = {
        "filename": filename,
        "status": status,
        "reason": reason,
        "patient": patient,
        "image": image,
        "stain": stain,
        "sections": sections,
        "has_multiple": has_multiple,
    }
    run["files"].append(entry)
    run["total"] += 1
    if status == "ok":
        run["ok"] += 1
        if has_multiple:
            run["cortados"] += 1
    else:
        run["errors"] += 1


def finish_run(run: dict, log_root: str) -> str:
    log_dir = os.path.join(log_root, LOG_DIR)
    runs = _load_runs(log_dir)
    runs.append(run)
    _save_runs(log_dir, runs)
    return os.path.join(log_dir, RUNS_FILE)


def print_report(run: dict, extensive: bool = False) -> None:
    from mil.report import report_summary, report_extensive
    if extensive:
        report_extensive(run)
    else:
        report_summary(run)


def list_runs(log_root: str) -> list[dict]:
    log_dir = os.path.join(log_root, LOG_DIR)
    return _load_runs(log_dir)
