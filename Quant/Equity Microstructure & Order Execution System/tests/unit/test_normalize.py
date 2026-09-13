import pandas as pd

from equity_microstructure.data.normalize import (
    normalize_taq,
    normalize_taqm,
)


def test_normalize_taq_date_uses_day_first():
    df = pd.DataFrame(
        {
            "date": ["06/04/1993"],
            "symbol": [" aapl "],
        }
    )

    result = normalize_taq(df)

    assert result.loc[0, "date"] == pd.Timestamp(
        "1993-04-06"
    )

    assert result.loc[0, "symbol"] == "AAPL"


def test_normalize_taqm_date_uses_day_first():
    df = pd.DataFrame(
        {
            "DATE": ["02/01/2013"],
            "symbol": [" aapl "],
            "SYM_ROOT": [" AAPL "],
        }
    )

    result = normalize_taqm(df)

    assert result.loc[0, "DATE"] == pd.Timestamp(
        "2013-01-02"
    )

    assert result.loc[0, "symbol"] == "AAPL"
    assert result.loc[0, "SYM_ROOT"] == "AAPL"


def test_normalize_taq_preserves_columns():
    df = pd.DataFrame(
        {
            "date": ["06/04/1993"],
            "symbol": ["AAPL"],
            "MID_1pm": [49.375],
        }
    )

    result = normalize_taq(df)

    assert list(result.columns) == [
        "date",
        "symbol",
        "MID_1pm",
    ]


def test_normalize_taqm_preserves_source_columns():
    df = pd.DataFrame(
        {
            "DATE": ["02/01/2013"],
            "symbol": ["AAPL"],
            "CPrc": [549.03],
        }
    )

    result = normalize_taqm(df)

    assert "CPrc" in result.columns