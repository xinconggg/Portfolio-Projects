from pathlib import Path

from equity_microstructure.data.discovery import (
    classify_dataset,
    infer_file_type,
    infer_year,
    is_compressed,
)


def test_classify_taq():
    path = Path("D:/research/TAQ/taq_2005.csv")
    assert classify_dataset(path) == "TAQ"


def test_classify_taqm():
    path = Path("D:/research/TAQM/taqm_2015.csv")
    assert classify_dataset(path) == "TAQM"


def test_classify_crsp_delisting():
    path = Path("D:/research/CRSP/crsp_delisting.csv")
    assert classify_dataset(path) == "CRSP Delisting"


def test_classify_unknown():
    path = Path("D:/research/random_data.csv")
    assert classify_dataset(path) == "Unknown"


def test_infer_year():
    path = Path("TAQ_2007.csv")
    assert infer_year(path) == 2007


def test_infer_year_missing():
    path = Path("TAQ_latest.csv")
    assert infer_year(path) is None


def test_file_type_csv():
    path = Path("data.csv")
    assert infer_file_type(path) == "csv"


def test_file_type_csv_gz():
    path = Path("data.csv.gz")
    assert infer_file_type(path) == "csv.gz"


def test_compressed():
    assert is_compressed(Path("data.csv.gz")) is True


def test_uncompressed():
    assert is_compressed(Path("data.csv")) is False