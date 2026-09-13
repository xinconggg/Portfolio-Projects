import pandas as pd

from equity_microstructure.data.validate import (
    validate_dataframe,
    validate_required_columns,
)


def test_validate_required_columns():
    df = pd.DataFrame(
        {
            "date": ["06/04/1993"],
            "symbol": ["AAPL"],
        }
    )

    missing = validate_required_columns(
        df,
        ["date", "symbol", "CPrc"],
    )

    assert missing == ["CPrc"]


def test_validate_dataframe():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["1993-04-06"]
            ),
            "symbol": ["AAPL"],
        }
    )

    result = validate_dataframe(
        df,
        required_columns=[
            "date",
            "symbol",
        ],
        date_column="date",
    )

    assert result["rows"] == 1
    assert result["columns"] == 2
    assert result["missing_required_columns"] == []

    assert result["date"]["missing"] == 0
    assert result["symbol"]["unique"] == 1