"""Utilities for discovering local research data files."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".csv",
    ".txt",
    ".dat",
    ".tsv",
    ".parquet",
    ".sas7bdat",
    ".gz",
    ".zip",
}


@dataclass(frozen=True)
class FileRecord:
    """Metadata describing one discovered file."""

    path: str
    relative_path: str
    filename: str
    extension: str
    parent_directory: str

    size_bytes: int
    modified_timestamp: str

    dataset: str

    compressed: bool
    file_type: str

    # Filename/path-based inference only.
    # These are NOT authoritative data coverage fields.
    inferred_year: int | None

    hash_type: str | None = None
    hash_value: str | None = None


def classify_dataset(path: Path) -> str:
    """Classify a file using conservative path and filename clues.

    The classifier uses directory and filename information only.
    Schema-based confirmation will occur later.
    """

    parts = [
        part.lower()
        for part in path.parts
    ]

    filename = path.name.lower()

    text = " ".join(parts)

    # TAQM must be checked before TAQ because
    # 'taqm' contains the string 'taq'.
    if "taqm" in text or "taqm" in filename:
        return "TAQM"

    if "taq" in text or "taq" in filename:
        return "TAQ"

    if "crsp" in text or "crsp" in filename:

        if any(
            term in text
            for term in ["delist", "delisting"]
        ):
            return "CRSP Delisting"

        if any(
            term in text
            for term in ["distribution", "dist"]
        ):
            return "CRSP Distribution"

        if (
            "share" in text
            and ("out" in text or "outstanding" in text)
        ):
            return "CRSP Share Outstanding"

        if "name" in text or "names" in text:
            return "CRSP Names"

        if "monthly" in text:
            return "CRSP Monthly Stock"

        if "daily" in text:
            return "CRSP Daily Stock"

        if "index" in text:
            return "CRSP Market Index"

        return "CRSP"

    return "Unknown"


def infer_year(path: Path) -> int | None:
    """Infer a four-digit year from a filename or path."""

    matches = re.findall(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", str(path))

    if not matches:
        return None

    years = [int(year) for year in matches]

    valid_years = [
        year
        for year in years
        if 1900 <= year <= 2100
    ]

    if not valid_years:
        return None

    return valid_years[-1]


def get_extension(path: Path) -> str:
    """Return the logical file extension."""

    name = path.name.lower()

    compound_extensions = (
        ".csv.gz",
        ".txt.gz",
        ".tsv.gz",
        ".dat.gz",
    )

    for extension in compound_extensions:
        if name.endswith(extension):
            return extension

    return path.suffix.lower()


def is_compressed(path: Path) -> bool:
    """Determine whether a file appears to be compressed."""

    compressed_extensions = {
        ".gz",
        ".zip",
        ".bz2",
        ".xz",
    }

    return path.suffix.lower() in compressed_extensions


def infer_file_type(path: Path) -> str:
    """Infer the broad physical file format."""

    name = path.name.lower()

    if name.endswith(".csv.gz"):
        return "csv.gz"

    if name.endswith(".txt.gz"):
        return "txt.gz"

    if name.endswith(".tsv.gz"):
        return "tsv.gz"

    if name.endswith(".dat.gz"):
        return "dat.gz"

    if name.endswith(".csv"):
        return "csv"

    if name.endswith(".txt"):
        return "text"

    if name.endswith(".dat"):
        return "text"

    if name.endswith(".tsv"):
        return "tsv"

    if name.endswith(".parquet"):
        return "parquet"

    if name.endswith(".sas7bdat"):
        return "sas7bdat"

    if name.endswith(".zip"):
        return "zip"

    if name.endswith(".gz"):
        return "gzip"

    return "unknown"


def calculate_partial_hash(
    path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    """Calculate a SHA-256 hash using the beginning and end of a file.

    This avoids reading an enormous file in full.
    """

    file_size = path.stat().st_size

    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        if file_size <= 2 * chunk_size:
            sha256.update(file.read())
        else:
            sha256.update(file.read(chunk_size))

            file.seek(-chunk_size, 2)
            sha256.update(file.read(chunk_size))

    return sha256.hexdigest()


def discover_files(
    root: Path,
    project_root: Path | None = None,
    calculate_hash: bool = False,
) -> list[FileRecord]:
    """Recursively discover files below a root directory."""

    if not root.exists():
        raise FileNotFoundError(
            f"Discovery root does not exist: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Discovery root is not a directory: {root}"
        )

    if project_root is None:
        project_root = root

    records: list[FileRecord] = []

    for path in sorted(root.rglob("*")):

        if not path.is_file():
            continue

        extension = get_extension(path)

        if extension not in SUPPORTED_EXTENSIONS:
            continue

        stat = path.stat()

        relative_path = path.relative_to(project_root)

        hash_type = None
        hash_value = None

        if calculate_hash:
            hash_type = "partial_sha256"
            hash_value = calculate_partial_hash(path)

        records.append(
            FileRecord(
                path=str(path.resolve()),
                relative_path=str(relative_path),
                filename=path.name,
                extension=extension,
                parent_directory=str(path.parent),
                size_bytes=stat.st_size,
                modified_timestamp=datetime.fromtimestamp(
                stat.st_mtime,
                tz=UTC,
                    ).isoformat(),

                dataset=classify_dataset(path),
                inferred_year=infer_year(path),

                compressed=is_compressed(path),
                file_type=infer_file_type(path),

                hash_type=hash_type,
                hash_value=hash_value,
            )
        )

    return records


def records_to_dicts(
    records: list[FileRecord],
) -> list[dict]:
    """Convert file records into serializable dictionaries."""

    return [asdict(record) for record in records]