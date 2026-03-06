import run_test_validation as rtv


def main():
    rows = rtv.collect_all()
    assert rows, "No turbine rows loaded."

    # 1) Criterion 1 strict 120.00 h logic.
    c1_label = rtv.criterion1_label()
    assert "120" in c1_label, f"Criterion 1 label mismatch: {c1_label}"
    assert abs(rtv.CRIT1_HOURS - 120.0) < 1e-9, f"Unexpected Criterion 1 threshold: {rtv.CRIT1_HOURS}"
    for r in rows:
        assert abs(r["total_h"] - 120.0) < 1e-6, (
            f"{r['turbine']} RT window is not 120.00 h: {r['total_h']}"
        )
        assert abs(r["hours_120"] - r["total_h"]) < 1e-6, (
            f"{r['turbine']} coverage mismatch: {r['hours_120']} vs {r['total_h']}"
        )
        assert r["hours_120"] >= rtv.CRIT1_HOURS - 1e-6, (
            f"{r['turbine']} fails Criterion 1 unexpectedly: {r['hours_120']} < {rtv.CRIT1_HOURS}"
        )

    # 2) Conclusion minima should come from computed table values.
    c2_min = rtv.min_metric(rows, "hours_wind_range")
    assert c2_min is not None, "No minimum found for Criterion 2."

    # 3) Annex 1 narrative must not claim normal operation for E4 if warning is 100%.
    e4 = next(r for r in rows if r["turbine"] == "E4")
    annex1_text = rtv.annex1_narrative(rows).lower()
    if e4["warning_h"] >= e4["total_h"] - 1e-6:
        assert "normal operation" not in annex1_text, (
            "Annex 1 narrative incorrectly claims normal operation for E4."
        )

    # 4) Annex 4 threshold is fixed at 12 m/s.
    assert abs(rtv.ANNEX4_P98_WS_MS - 12.0) < 1e-9, "Annex 4 threshold is not 12 m/s."

    # 5) OK time cannot exceed RT window and convention is consistent.
    for r in rows:
        assert r["ok_h"] <= r["total_h"] + 1e-6, (
            f"{r['turbine']} ok_h exceeds RT window: {r['ok_h']} > {r['total_h']}"
        )

    print("All RT sanity checks passed.")


if __name__ == "__main__":
    main()
