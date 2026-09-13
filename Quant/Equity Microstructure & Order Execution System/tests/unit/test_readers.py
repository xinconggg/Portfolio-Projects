from pathlib import Path

import pandas as pd

from equity_microstructure.data.readers import read_sample


def test_read_csv_sample(tmp_path: Path):
    path = tmp_path / "sample.csv"

    pd.DataFrame(
        {
            "date": ["2005-01-03", "2005-01-04"],
            "symbol": ["AAPL", "IBM"],
        }
    ).to_csv(path, index=False)

    result = read_sample(
        path,
        nrows=1,
    )

    assert len(result) == 1
    assert list(result.columns) == [
        "date",
        "symbol",
    ]