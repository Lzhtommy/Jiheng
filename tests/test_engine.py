from app.engine import diagnosis, debate, screen


def test_screen_interprets_numeric_conditions():
    filters, results = screen("PE<25 且 ROE>15% 且现金流为正")
    assert filters["pe_max"] == 25
    assert filters["roe_min"] == 15
    assert results
    assert all(item.pe_ttm <= 25 and item.roe >= 15 for item in results)


def test_diagnosis_contains_traceable_evidence():
    report = diagnosis("300750")
    assert report is not None
    assert report["evidence"]
    assert all("id" in item for item in report["evidence"])
    assert report["data_notice"].startswith("当前为")


def test_debate_is_balanced_and_has_falsification_checks():
    report = debate("600519")
    assert report is not None
    assert report["bull"]
    assert report["bear"]
    assert report["falsify"]

