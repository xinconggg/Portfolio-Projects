from pathlib import Path
import gzip
import hashlib
import os
import zipfile

import pandas as pd


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_TAQ_DIR = PROJECT_ROOT / "data" / "raw" / "taq"
PROCESSED_TAQ_DIR = PROJECT_ROOT / "data" / "processed" / "taq"

OUTPUT_FILE = PROCESSED_TAQ_DIR / "taq_file_inventory.csv"


# =============================================================================
# CONFIGURATION
# =============================================================================

TABULAR_EXTENSIONS = {
    ".csv",
    ".txt",
    ".tsv",
    ".dat",
    ".parquet",
    ".gz",
    ".zip",
}


# =============================================================================
# HELPERS
# =============================================================================

def format_bytes(nbytes):
    if nbytes is None:
        return None

    units = ["B", "KB", "MB", "GB", "TB"]

    value = float(nbytes)

    for unit in units:
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024

    return f"{value:.2f} PB"


def detect_compression(path):
    suffixes = [suffix.lower() for suffix in path.suffixes]

    if ".gz" in suffixes:
        return "gzip"

    if ".zip" in suffixes:
        return "zip"

    return None


def detect_file_type(path):
    suffixes = [suffix.lower() for suffix in path.suffixes]

    if ".parquet" in suffixes:
        return "parquet"

    if ".csv" in suffixes:
        return "csv"

    if ".tsv" in suffixes:
        return "tsv"

    if ".txt" in suffixes:
        return "text"

    if ".dat" in suffixes:
        return "data"

    if ".gz" in suffixes:
        return "compressed"

    if ".zip" in suffixes:
        return "archive"

    return path.suffix.lower().lstrip(".") or "unknown"


def is_candidate_file(path):
    if not path.is_file():
        return False

    suffixes = {suffix.lower() for suffix in path.suffixes}

    return bool(suffixes & TABULAR_EXTENSIONS)


def estimate_text_row_count(path, chunk_size=1024 * 1024):
    """
    Approximate physical line count without loading the file into memory.
    Used only as an inventory diagnostic.

    This is intentionally not treated as the authoritative record count
    because headers, multiline records, and source-specific formatting may
    affect the result.
    """

    try:
        if path.suffix.lower() == ".gz":
            opener = gzip.open
        else:
            opener = open

        line_count = 0

        with opener(path, "rb") as handle:
            while True:
                chunk = handle.read(chunk_size)

                if not chunk:
                    break

                line_count += chunk.count(b"\n")

        return line_count

    except Exception:
        return None


def inspect_zip(path):
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()

            return {
                "archive_member_count": len(members),
                "archive_members": ";".join(
                    member.filename for member in members[:100]
                ),
            }

    except Exception:
        return {
            "archive_member_count": None,
            "archive_members": None,
        }


def lightweight_read_test(path):
    """
    Verify that a file can be opened/read without loading the entire dataset.
    """

    try:

        if path.suffix.lower() == ".parquet":

            import pyarrow.parquet as pq

            parquet_file = pq.ParquetFile(path)

            return {
                "readable": True,
                "read_test_rows": parquet_file.metadata.num_rows,
                "read_error": None,
            }

        if path.suffix.lower() == ".zip":

            with zipfile.ZipFile(path) as archive:
                archive.testzip()

            return {
                "readable": True,
                "read_test_rows": None,
                "read_error": None,
            }

        if path.suffix.lower() == ".gz":

            with gzip.open(path, "rb") as handle:
                handle.read(1024)

            return {
                "readable": True,
                "read_test_rows": None,
                "read_error": None,
            }

        with open(path, "rb") as handle:
            handle.read(1024)

        return {
            "readable": True,
            "read_test_rows": None,
            "read_error": None,
        }

    except Exception as exc:

        return {
            "readable": False,
            "read_test_rows": None,
            "read_error": repr(exc),
        }


# =============================================================================
# MAIN INVENTORY
# =============================================================================

def build_inventory():

    if not RAW_TAQ_DIR.exists():

        raise FileNotFoundError(
            f"TAQ raw directory does not exist:\n{RAW_TAQ_DIR}\n\n"
            "Create/populate the raw TAQ directory or update RAW_TAQ_DIR "
            "after confirming the actual project data architecture."
        )

    files = sorted(
        path
        for path in RAW_TAQ_DIR.rglob("*")
        if is_candidate_file(path)
    )

    print("=" * 80)
    print("TAQ / TAQM FILE INVENTORY")
    print("=" * 80)

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Raw TAQ directory: {RAW_TAQ_DIR}")
    print(f"Candidate files found: {len(files)}")
    print()

    records = []

    for i, path in enumerate(files, start=1):

        print(f"[{i}/{len(files)}] {path}")

        stat = path.stat()

        compression = detect_compression(path)
        file_type = detect_file_type(path)

        read_result = lightweight_read_test(path)

        record = {
            "file_id": i,
            "filename": path.name,
            "relative_path": str(path.relative_to(PROJECT_ROOT)),
            "full_path": str(path.resolve()),
            "directory": str(path.parent.relative_to(PROJECT_ROOT)),
            "extension": path.suffix.lower(),
            "file_type": file_type,
            "compression": compression,
            "size_bytes": stat.st_size,
            "size_human": format_bytes(stat.st_size),
            "modified_timestamp": pd.Timestamp.fromtimestamp(
                stat.st_mtime
            ).isoformat(),
            "readable": read_result["readable"],
            "read_error": read_result["read_error"],
        }

        if file_type in {"csv", "text", "data", "tsv"}:
            record["approx_physical_lines"] = estimate_text_row_count(path)
        else:
            record["approx_physical_lines"] = None

        if file_type == "archive":
            record.update(inspect_zip(path))
        else:
            record["archive_member_count"] = None
            record["archive_members"] = None

        records.append(record)

    inventory = pd.DataFrame(records)

    PROCESSED_TAQ_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    inventory.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("=" * 80)
    print("INVENTORY COMPLETE")
    print("=" * 80)

    print(f"Files inventoried: {len(inventory)}")
    print(
        f"Readable files: "
        f"{inventory['readable'].sum() if len(inventory) else 0}"
    )
    print(
        f"Unreadable files: "
        f"{(~inventory['readable']).sum() if len(inventory) else 0}"
    )

    print()
    print(f"Output: {OUTPUT_FILE}")

    return inventory


if __name__ == "__main__":
    build_inventory()