import pandas as pd
from app.engines import type_detector, missing_detector, duplicate_detector, outlier_detector
from app.engines.text_normalizer import normalize_email, trim, classify_email
from app.engines.numeric_detector import parse_numeric_token
from app.services.quality_service import compute_score
from app.services.validation_service import evaluate
from app.services.cleaning_service import apply_op


def test_email_normalization():
    assert normalize_email(" JUAN@EXAMPLE.COM ") == "juan@example.com"
    assert classify_email("bad@@x") == "invalid"


def test_trim_idempotent():
    assert trim(trim("  Juan  Pérez  ")) == trim("  Juan  Pérez  ")


def test_numeric_parsing():
    v, _ = parse_numeric_token("$1,200.50")
    assert abs(v - 1200.50) < 1e-6


def test_missing_detection():
    df = pd.DataFrame({"a": ["x", "N/A", "", "  ", None]})
    r = missing_detector.analyze(df)
    assert r.metrics["missing_cells"] >= 4


def test_duplicates_do_not_mutate():
    df = pd.DataFrame({"a": [1, 1, 2]})
    before = df.copy()
    duplicate_detector.analyze(df)
    pd.testing.assert_frame_equal(df, before)


def test_outlier_flags_but_no_remove():
    df = pd.DataFrame({"n": list(range(20)) + [1000]})
    r = outlier_detector.analyze(df)
    assert r.metrics["n"]["outliers"] >= 1
    assert len(df) == 21


def test_score_changes_when_fixed():
    df = pd.DataFrame({"email": ["a@x.com"] * 90 + ["bad"] * 10, "x": range(100)})
    from app.services.profiling_service import profile_dataframe
    p1 = profile_dataframe(df)
    s1 = compute_score(p1, len(df))["overall"]
    df2, _ = apply_op(df, "normalize_email", "email", {})
    df2.loc[df2["email"] == "bad", "email"] = "fixed@x.com"
    p2 = profile_dataframe(df2)
    s2 = compute_score(p2, len(df2))["overall"]
    assert s2 >= s1


def test_validation_no_mutation():
    df = pd.DataFrame({"age": [20, -1, 200]})
    before = df.copy(deep=True)
    res = evaluate(df, [{"column": "age", "operator": "between", "value": [0, 120], "name": "t", "severity": "HIGH"}])
    assert res[0]["failed"] == 2
    pd.testing.assert_frame_equal(df, before)
