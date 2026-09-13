from pathlib import Path

from equity_microstructure.data.discovery import discover_files
from equity_microstructure.data.inventory import (
    write_file_inventory,
)


def test_discover_files(tmp_path: Path):
    taq_dir = tmp_path / "TAQ"
    taq_dir.mkdir()

    file_one = taq_dir / "taq_2005.csv"
    file_one.write_text(
        "date,symbol\n2005-01-03,AAPL\n",
        encoding="utf-8",
    )

    records = discover_files(
        root=tmp_path,
        project_root=tmp_path,
    )

    assert len(records) == 1
    assert records[0].dataset == "TAQ"
    assert records[0].inferred_year == 2005
    assert records[0].file_type == "csv"


def test_write_inventory(tmp_path: Path):
    source_dir = tmp_path / "TAQ"
    source_dir.mkdir()

    source_file = source_dir / "taq_2010.csv"

    source_file.write_text(
        "date,symbol\n2010-01-04,IBM\n",
        encoding="utf-8",
    )

    output = tmp_path / "inventory.csv"

    count = write_file_inventory(
        root=tmp_path,
        output_path=output,
        project_root=tmp_path,
    )

    assert count == 1
    assert output.exists()

    contents = output.read_text(
        encoding="utf-8"
    )

    assert "taq_2010.csv" in contents
    assert "TAQ" in contents