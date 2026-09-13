"""Project configuration management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_ROOT = PROJECT_ROOT / "config"
CONFIG_FILE = CONFIG_ROOT / "data_config.yaml"

DATA_ROOT = PROJECT_ROOT / "data"
RAW_DATA_ROOT = DATA_ROOT / "raw"
PROCESSED_DATA_ROOT = DATA_ROOT / "processed"
METADATA_ROOT = DATA_ROOT / "metadata"
VALIDATION_ROOT = DATA_ROOT / "validation"

TAQ_DIR = RAW_DATA_ROOT / "taq"
TAQM_DIR = RAW_DATA_ROOT / "taqm"
CRSP_DIR = RAW_DATA_ROOT / "crsp"

TAQ_FILE = TAQ_DIR / "taq.csv"
TAQM_FILE = TAQM_DIR / "taqm.csv"

DATASET_FILES = {
    "taq": TAQ_FILE,
    "taqm": TAQM_FILE,
}

DATASET_LAYOUT = {
    "taq": "single_file_multi_year",
    "taqm": "single_file_multi_year",
    "crsp": "unknown",
}

@dataclass(frozen=True)
class ResearchPeriod:
    """Research sample period."""

    start: date
    end: date


@dataclass(frozen=True)
class MicrostructureRegime:
    """Microstructure data regime."""

    start_year: int
    end_year: int


@dataclass(frozen=True)
class DataPaths:
    """Locations of source datasets."""

    crsp: Path | None
    taq: Path | None
    taqm: Path | None


@dataclass(frozen=True)
class OutputPaths:
    """Locations of generated project outputs."""

    metadata: Path
    validation: Path
    interim: Path
    processed: Path
    reports: Path


@dataclass(frozen=True)
class Settings:
    """Complete project configuration."""

    project_name: str
    project_version: str

    research_period: ResearchPeriod

    taq_regime: MicrostructureRegime
    taqm_regime: MicrostructureRegime

    data: DataPaths
    outputs: OutputPaths

def _resolve_optional_path(
    value: str,
    project_root: Path,
) -> Path | None:
    """Resolve an optional configured path."""

    if not value:
        return None

    path = Path(value)

    if not path.is_absolute():
        path = project_root / path

    return path.resolve()

def _load_yaml(path: Path) -> dict:
    """Load the YAML configuration file."""

    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise TypeError(
            f"Configuration file must contain a YAML mapping: {path}"
        )

    return config

def load_settings(
    config_file: Path = CONFIG_FILE,
) -> Settings:
    """Load project settings from YAML."""

    config = _load_yaml(config_file)

    research_period = config["research_period"]
    regimes = config["microstructure_regimes"]
    data = config["data"]
    outputs = config["outputs"]

    return Settings(
        project_name=config["project"]["name"],
        project_version=config["project"]["version"],
        research_period=ResearchPeriod(
            start=date.fromisoformat(research_period["start"]),
            end=date.fromisoformat(research_period["end"]),
        ),
        taq_regime=MicrostructureRegime(
            start_year=regimes["taq"]["start_year"],
            end_year=regimes["taq"]["end_year"],
        ),
        taqm_regime=MicrostructureRegime(
            start_year=regimes["taqm"]["start_year"],
            end_year=regimes["taqm"]["end_year"],
        ),
        data=DataPaths(
            crsp=_resolve_optional_path(
                data["crsp"]["path"],
                PROJECT_ROOT,
            ),
            taq=_resolve_optional_path(
                data["taq"]["path"],
                PROJECT_ROOT,
            ),
            taqm=_resolve_optional_path(
                data["taqm"]["path"],
                PROJECT_ROOT,
            ),
        ),
        outputs=OutputPaths(
            metadata=(
                PROJECT_ROOT / outputs["metadata"]
            ).resolve(),
            validation=(
                PROJECT_ROOT / outputs["validation"]
            ).resolve(),
            interim=(
                PROJECT_ROOT / outputs["interim"]
            ).resolve(),
            processed=(
                PROJECT_ROOT / outputs["processed"]
            ).resolve(),
            reports=(
                PROJECT_ROOT / outputs["reports"]
            ).resolve(),
        ),
    )


settings = load_settings()

