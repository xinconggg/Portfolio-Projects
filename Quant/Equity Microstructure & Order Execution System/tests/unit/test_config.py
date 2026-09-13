from datetime import date

from equity_microstructure.config import (
    CONFIG_FILE,
    DATA_ROOT,
    METADATA_ROOT,
    PROCESSED_DATA_ROOT,
    PROJECT_ROOT,
    RAW_DATA_ROOT,
    VALIDATION_ROOT,
    settings,
)


def test_project_root_exists():
    assert PROJECT_ROOT.exists()
    assert PROJECT_ROOT.is_dir()


def test_config_file_exists():
    assert CONFIG_FILE.exists()
    assert CONFIG_FILE.is_file()


def test_data_root_is_under_project_root():
    assert DATA_ROOT.parent == PROJECT_ROOT


def test_raw_data_root_is_under_data_root():
    assert RAW_DATA_ROOT.parent == DATA_ROOT


def test_processed_data_root_is_under_data_root():
    assert PROCESSED_DATA_ROOT.parent == DATA_ROOT


def test_metadata_root_is_under_data_root():
    assert METADATA_ROOT.parent == DATA_ROOT


def test_validation_root_is_under_data_root():
    assert VALIDATION_ROOT.parent == DATA_ROOT


def test_research_period():
    assert settings.research_period.start == date(1993, 1, 1)
    assert settings.research_period.end == date(2018, 12, 31)


def test_taq_regime():
    assert settings.taq_regime.start_year == 1993
    assert settings.taq_regime.end_year == 2012


def test_taqm_regime():
    assert settings.taqm_regime.start_year == 2013
    assert settings.taqm_regime.end_year == 2018


def test_source_paths_are_configured():
    assert settings.data.crsp is not None
    assert settings.data.taq is not None
    assert settings.data.taqm is not None


def test_output_paths():
    assert settings.outputs.metadata == (
        PROJECT_ROOT / "data" / "metadata"
    ).resolve()

    assert settings.outputs.validation == (
        PROJECT_ROOT / "data" / "validation"
    ).resolve()

    assert settings.outputs.interim == (
        PROJECT_ROOT / "data" / "interim"
    ).resolve()

    assert settings.outputs.processed == (
        PROJECT_ROOT / "data" / "processed"
    ).resolve()

    assert settings.outputs.reports == (
        PROJECT_ROOT / "reports"
    ).resolve()