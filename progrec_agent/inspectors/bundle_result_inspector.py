from __future__ import annotations


def show_bundle_summary(result_ref_payload: dict[str, object]) -> dict[str, object]:
    payload = dict(result_ref_payload.get("payload") or {})
    return dict(payload.get("final_recommendation") or payload.get("skill5_result") or {})


def export_report(result_ref_payload: dict[str, object]) -> dict[str, object]:
    payload = dict(result_ref_payload.get("payload") or {})
    report_path = str(payload.get("report_path") or "")
    return {
        "report_path": report_path,
        "available": bool(report_path),
    }
