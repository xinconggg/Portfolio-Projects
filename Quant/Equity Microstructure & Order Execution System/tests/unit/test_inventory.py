from pathlib import Path

import pandas as pd

from equity_microstructure.data.inventory.inventory import (
    get_file_inventory,
)


def test_get_file_inventory(tmp_path: Path) -> None:
    """Inventory should correctly inspect a CSV file."""

    test_file = tmp_path / "test.csv"

    pd.DataFrame(
        {
            "date": ["01/01/2020", "02/01/2020"],
            "symbol": ["AAPL", "MSFT"],
            "price": [100.0, 200.0],
        }
    ).to_csv(test_file, index=False)

    result = get_file_inventory(
        test_file,
        dataset="test",
    )

    assert result.dataset == "test"
    assert result.filename == "test.csv"
    assert result.extension == ".csv"
    assert result.n_columns == 3
    assert result.columns == ["date", "symbol", "price"]
    assert result.size_bytes > 0