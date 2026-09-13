import pandas as pd

from equity_microstructure.data.loaders import (
    load_taq,
)


def test_load_taq_filters_date_and_symbol(tmp_path):

    path = tmp_path / "taq.csv"

    df = pd.DataFrame(
        {
            "date": [
                "01/01/2013",
                "02/01/2013",
                "03/01/2013",
            ],
            "symbol": [
                "AAPL",
                "MSFT",
                "AAPL",
            ],
            "MID_1pm": [
                500.0,
                300.0,
                501.0,
            ],
        }
    )

    df.to_csv(path, index=False)

    result = load_taq(
        path=path,
        symbols=["AAPL"],
        start_date="2013-01-02",
        end_date="2013-01-03",
    )

    assert len(result) == 1
    assert result.iloc[0]["symbol"] == "AAPL"
    assert result.iloc[0]["MID_1pm"] == 501.0