from __future__ import annotations

import csv
from pathlib import Path


MBPS_PER_GBPS = 1000.0


def read_intel_pcm_metrics(path: str | Path) -> dict[str, list[float]]:
    """Read Intel pcm-memory CSV samples and return GB/s series.

    Intel PCM writes two header rows.  The first labels socket groups and the
    second labels columns.  The final ``Read``, ``Write``, and ``Memory``
    columns are system-wide totals; the parser prefers those over per-socket
    values and falls back to summing per-socket columns when needed.
    """
    result = {
        "memory_bw_gbps": [],
        "read_bw_gbps": [],
        "write_bw_gbps": [],
    }
    csv_path = Path(path)
    if not csv_path.exists():
        return result

    headers: list[str] | None = None
    try:
        with csv_path.open(newline="", encoding="utf-8", errors="replace") as handle:
            for raw_row in csv.reader(handle):
                row = [str(item).strip().lstrip("\ufeff") for item in raw_row]
                if _is_pcm_header(row):
                    headers = [_normalize_header(item) for item in row]
                    continue
                if headers is None or len(row) < len(headers):
                    continue
                values = _sample_values(headers, row)
                for key, value in values.items():
                    if value is not None:
                        result[key].append(round(value / MBPS_PER_GBPS, 6))
    except (OSError, csv.Error):
        return result
    return result


def _is_pcm_header(row: list[str]) -> bool:
    if len(row) < 3:
        return False
    normalized = [_normalize_header(item) for item in row]
    return (
        normalized[0] == "Date"
        and normalized[1] == "Time"
        and any(item in {"Memory", "Memory (MB/s)"} for item in normalized)
    )


def _normalize_header(value: str) -> str:
    return " ".join(str(value).strip().split())


def _numeric(value: str) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _values_for_header(headers: list[str], row: list[str], header: str) -> list[float]:
    values: list[float] = []
    for index, name in enumerate(headers):
        if name != header or index >= len(row):
            continue
        value = _numeric(row[index])
        if value is not None:
            values.append(value)
    return values


def _last_value(headers: list[str], row: list[str], header: str) -> float | None:
    values = _values_for_header(headers, row, header)
    return values[-1] if values else None


def _sample_values(headers: list[str], row: list[str]) -> dict[str, float | None]:
    memory = _last_value(headers, row, "Memory")
    if memory is None:
        memory_values = _values_for_header(headers, row, "Memory (MB/s)")
        memory = sum(memory_values) if memory_values else None

    read = _last_value(headers, row, "Read")
    if read is None:
        read_values = _values_for_header(headers, row, "Mem Read (MB/s)")
        read = sum(read_values) if read_values else None

    write = _last_value(headers, row, "Write")
    if write is None:
        write_values = _values_for_header(headers, row, "Mem Write (MB/s)")
        write = sum(write_values) if write_values else None

    return {
        "memory_bw_gbps": memory,
        "read_bw_gbps": read,
        "write_bw_gbps": write,
    }
