"""Shared helpers for report-facing evaluation payloads."""

from __future__ import annotations


def build_ablation_payload(results: dict[str, dict], *, n_records: int) -> dict[str, object]:
    return {
        "config_order": ["Baseline", "+ Taxonomy", "+ UQ", "Full Pipeline"],
        "metrics": results,
        "n_records": n_records,
    }
