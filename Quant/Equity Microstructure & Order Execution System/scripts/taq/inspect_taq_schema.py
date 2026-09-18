from pathlib import Path
import gzip
import zipfile
import re

import pandas as pd


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TAQ_PROCESSED_DIR = (
    PROJECT_ROOT /
    "data" /
    "processed" /
    "taq"
)

INVENTORY_FILE = (
    TAQ_PROCESSED_DIR /
    "taq_file_inventory.csv"
)

SCHEMA_OUTPUT = (
    TAQ_PROCESSED_DIR /
    "taq_schema_inventory.csv"
)

SAMPLES_OUTPUT = (
    TAQ_PROCESSED_DIR /
    "taq_schema_samples.csv"
)


# =============================================================================
# CONFIGURATION
# =============================================================================

SAMPLE_ROWS = 1_000

CHUNK_SIZE = 100_000

MAX_SAMPLE_ROWS = 100


# =============================================================================
# HELPERS
# =============================================================================

def print_header(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def normalize_column_name(column):
    """
    Normalize a column name for internal classification only.

    Original source column names are preserved in all outputs.
    """

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(column).strip().lower(),
    ).strip("_")


def detect_separator(path):
    """
    Detect a likely delimiter for text-based files.

    Supported candidates:
        comma
        tab
        pipe
        semicolon

    The function intentionally remains conservative.
    """

    try:

        if path.suffix.lower() == ".gz":
            opener = gzip.open
        else:
            opener = open

        with opener(
            path,
            "rt",
            encoding="utf-8",
            errors="replace",
        ) as handle:

            first_line = handle.readline()

        candidates = [
            ",",
            "\t",
            "|",
            ";",
        ]

        counts = {
            delimiter: first_line.count(delimiter)
            for delimiter in candidates
        }

        best_delimiter = max(
            counts,
            key=counts.get,
        )

        if counts[best_delimiter] == 0:
            return ","

        return best_delimiter

    except Exception:
        return ","


def read_text_sample(path, nrows=SAMPLE_ROWS):
    """
    Read a representative sample from text-based TAQ files.
    """

    separator = detect_separator(path)

    print(
        f"Detected separator: {repr(separator)}"
    )

    return pd.read_csv(
        path,
        sep=separator,
        nrows=nrows,
        low_memory=False,
        compression="infer",
        on_bad_lines="warn",
    )


def read_parquet_sample(path, nrows=SAMPLE_ROWS):
    """
    Read a representative sample from a Parquet file.
    """

    import pyarrow.parquet as pq

    parquet_file = pq.ParquetFile(path)

    batches = parquet_file.iter_batches(
        batch_size=nrows
    )

    first_batch = next(
        batches,
        None,
    )

    if first_batch is None:
        return pd.DataFrame()

    return first_batch.to_pandas()


def read_zip_sample(path, nrows=SAMPLE_ROWS):
    """
    Inspect the first suitable tabular member of a ZIP archive.

    Archive structure is printed so the selected member is transparent.
    """

    with zipfile.ZipFile(path) as archive:

        members = [
            member
            for member in archive.infolist()
            if not member.is_dir()
        ]

        if not members:
            raise ValueError(
                f"ZIP archive contains no files: {path}"
            )

        print("ZIP members:")

        for member in members:
            print(
                f"  - {member.filename}"
            )

        preferred = [
            member
            for member in members
            if Path(
                member.filename
            ).suffix.lower()
            in {
                ".csv",
                ".txt",
                ".tsv",
                ".dat",
            }
        ]

        member = (
            preferred[0]
            if preferred
            else members[0]
        )

        print()
        print(
            f"Inspecting ZIP member: "
            f"{member.filename}"
        )

        with archive.open(member) as handle:

            return pd.read_csv(
                handle,
                nrows=nrows,
                low_memory=False,
                on_bad_lines="warn",
            )


def load_sample(path):
    """
    Determine file type and load a limited representative sample.
    """

    suffixes = [
        suffix.lower()
        for suffix in path.suffixes
    ]

    if ".zip" in suffixes:
        return read_zip_sample(path)

    if ".parquet" in suffixes:
        return read_parquet_sample(path)

    return read_text_sample(path)


# =============================================================================
# DATE / TIMESTAMP HELPERS
# =============================================================================

def looks_like_date_column(column_name):
    """
    Identify columns whose names suggest date information.
    """

    normalized = normalize_column_name(
        column_name
    )

    date_tokens = [
        "date",
        "tradedate",
        "quotedate",
        "trade_date",
        "quote_date",
        "caldt",
    ]

    return any(
        token in normalized
        for token in date_tokens
    )


def looks_like_timestamp_column(column_name):
    """
    Identify columns whose names suggest time/timestamp information.
    """

    normalized = normalize_column_name(
        column_name
    )

    timestamp_tokens = [
        "timestamp",
        "datetime",
        "time",
        "trdtime",
        "tradetime",
        "quotetime",
        "quote_time",
        "trade_time",
    ]

    return any(
        token in normalized
        for token in timestamp_tokens
    )


def safe_parse_datetime(series):
    """
    Parse a datetime-like Series without relying on pandas' ambiguous
    element-by-element format inference.

    Strategy:

    1. If the Series is already datetime-like, return it directly.
    2. Convert values to strings.
    3. Try pandas' ISO-compatible parser.
    4. Fall back to explicit common formats.
    5. Never modify the source Series.
    """

    if pd.api.types.is_datetime64_any_dtype(
        series
    ):
        return series

    non_null = series.dropna()

    if non_null.empty:
        return pd.Series(
            pd.NaT,
            index=series.index,
            dtype="datetime64[ns]",
        )

    # -------------------------------------------------------------------------
    # First attempt:
    # ISO-style parsing using format='mixed' where supported.
    # -------------------------------------------------------------------------

    try:

        parsed = pd.to_datetime(
            series,
            errors="coerce",
            format="mixed",
        )

        if parsed.notna().mean() >= 0.80:
            return parsed

    except (
        TypeError,
        ValueError,
    ):
        pass

    # -------------------------------------------------------------------------
    # Explicit common formats.
    # -------------------------------------------------------------------------

    string_series = (
        series
        .astype(str)
        .str.strip()
    )

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%H:%M:%S",
        "%H:%M:%S.%f",
    ]

    best = None
    best_rate = 0.0

    for fmt in formats:

        try:

            candidate = pd.to_datetime(
                string_series,
                format=fmt,
                errors="coerce",
            )

            rate = (
                candidate.notna().mean()
            )

            if rate > best_rate:

                best = candidate
                best_rate = rate

        except (
            TypeError,
            ValueError,
        ):
            continue

    if best is not None:
        return best

    # -------------------------------------------------------------------------
    # Final fallback.
    #
    # This path is intentionally isolated. It may still encounter ambiguous
    # values, but it is only used when explicit/common formats failed.
    # -------------------------------------------------------------------------

    try:

        return pd.to_datetime(
            string_series,
            errors="coerce",
            format="mixed",
        )

    except Exception:

        return pd.to_datetime(
            string_series,
            errors="coerce",
        )


def detect_possible_date(series):
    """
    Determine whether a column appears to contain dates/timestamps.

    This is diagnostic only.
    """

    name_signal = (
        looks_like_date_column(
            series.name
        )
        or
        looks_like_timestamp_column(
            series.name
        )
    )

    if not name_signal:
        return False

    try:

        parsed = safe_parse_datetime(
            series
        )

        valid_rate = (
            parsed.notna().mean()
        )

        return bool(
            valid_rate >= 0.80
        )

    except Exception:

        return False


def calculate_timestamp_precision(series):
    """
    Estimate timestamp precision.

    Important:
    pandas datetime64 values are internally stored in nanoseconds.

    Therefore:

        divisible by 1e9 -> second precision
        divisible by 1e6 -> millisecond precision
        divisible by 1e3 -> microsecond precision
        otherwise         -> nanosecond/finer

    This is diagnostic only.
    """

    try:

        parsed = safe_parse_datetime(
            series
        ).dropna()

        if len(parsed) == 0:
            return None

        values = (
            parsed.astype("int64")
        )

        # ---------------------------------------------------------------------
        # Correct order: coarse -> fine.
        # ---------------------------------------------------------------------

        if (values % 1_000_000_000 == 0).all():
            return "second_or_coarser"

        if (values % 1_000_000 == 0).all():
            return "millisecond"

        if (values % 1_000 == 0).all():
            return "microsecond"

        return "nanosecond_or_finer"

    except Exception:

        return None


# =============================================================================
# SEMANTIC ROLE INFERENCE
# =============================================================================

def infer_column_role(column_name):
    """
    Infer possible TAQ semantic roles from column names.

    This is diagnostic evidence only.

    It does NOT establish the economic meaning of a field.
    """

    normalized = normalize_column_name(
        column_name
    )

    role_keywords = {

        "security_identifier": [
            "symbol",
            "ticker",
            "cusip",
            "permno",
            "security",
            "issue",
            "identifier",
            "id",
        ],

        "date": [
            "date",
            "tradedate",
            "quotedate",
            "trade_date",
            "quote_date",
            "caldt",
        ],

        "timestamp": [
            "timestamp",
            "datetime",
            "time",
            "trdtime",
            "tradetime",
            "quotetime",
            "trade_time",
            "quote_time",
        ],

        "trade_price": [
            "trade_price",
            "sale_price",
            "trdprc",
            "tradeprice",
            "price",
        ],

        "trade_size": [
            "trade_size",
            "size",
            "volume",
            "shares",
            "qty",
            "quantity",
            "trdsiz",
        ],

        "bid": [
            "bid",
            "bid_price",
            "bidprice",
            "best_bid",
        ],

        "ask": [
            "ask",
            "ask_price",
            "askprice",
            "best_ask",
            "offer",
        ],

        "bid_size": [
            "bid_size",
            "bidsize",
            "bid_sz",
        ],

        "ask_size": [
            "ask_size",
            "asksize",
            "ask_sz",
        ],

        "exchange": [
            "exchange",
            "exch",
            "venue",
            "market",
        ],

        "condition": [
            "condition",
            "cond",
            "sale_condition",
            "quote_condition",
        ],

        "correction": [
            "correction",
            "correct",
            "corr",
        ],

        "cancellation": [
            "cancel",
            "cancellation",
            "cancelled",
        ],

        "sequence": [
            "sequence",
            "seq",
            "index",
        ],
    }

    matches = []

    for role, keywords in role_keywords.items():

        for keyword in keywords:

            if keyword in normalized:

                matches.append(role)

                break

    if not matches:
        return None

    return ";".join(
        sorted(
            set(matches)
        )
    )


# =============================================================================
# SAFE DIAGNOSTICS
# =============================================================================

def safe_unique_count(series):

    try:

        return int(
            series.nunique(
                dropna=True
            )
        )

    except Exception:

        return None


def safe_min(series):

    try:

        return series.min()

    except Exception:

        return None


def safe_max(series):

    try:

        return series.max()

    except Exception:

        return None


# =============================================================================
# LOAD INVENTORY
# =============================================================================

def load_inventory():

    if not INVENTORY_FILE.exists():

        raise FileNotFoundError(
            f"TAQ inventory file not found:\n"
            f"{INVENTORY_FILE}\n\n"
            "Run inventory_taq_data.py first."
        )

    inventory = pd.read_csv(
        INVENTORY_FILE
    )

    if inventory.empty:

        raise ValueError(
            "TAQ inventory is empty."
        )

    return inventory


# =============================================================================
# FILE SELECTION
# =============================================================================

def select_files(inventory):

    readable = inventory[
        inventory["readable"]
        .astype(str)
        .str.lower()
        .isin(
            [
                "true",
                "1",
                "yes",
            ]
        )
    ].copy()

    if readable.empty:

        raise RuntimeError(
            "No readable TAQ/TAQM files were found "
            "in the inventory."
        )

    return readable


# =============================================================================
# BUILD SCHEMA INVENTORY
# =============================================================================

def build_schema_inventory():

    print_header(
        "PHASE 5 — STEP 2: TAQ/TAQM SCHEMA INSPECTION"
    )

    inventory = load_inventory()

    print(
        f"Inventory rows: "
        f"{len(inventory):,}"
    )

    files = select_files(
        inventory
    )

    print(
        f"Readable files selected: "
        f"{len(files):,}"
    )

    schema_records = []
    sample_records = []

    # -------------------------------------------------------------------------
    # Iterate over every readable source file.
    # -------------------------------------------------------------------------

    for file_number, (_, file_row) in enumerate(
        files.iterrows(),
        start=1,
    ):

        file_path = Path(
            file_row["full_path"]
        )

        print()
        print("-" * 80)
        print(
            f"INSPECTING FILE "
            f"{file_number}/{len(files)}"
        )
        print("-" * 80)

        print(
            f"Filename: {file_path.name}"
        )

        print(
            f"Path:     {file_path}"
        )

        if not file_path.exists():

            print(
                "WARNING: file no longer exists."
            )

            continue

        # ---------------------------------------------------------------------
        # Load representative sample.
        # ---------------------------------------------------------------------

        try:

            sample = load_sample(
                file_path
            )

        except Exception as exc:

            print(
                "ERROR while reading sample:"
            )

            print(
                repr(exc)
            )

            try:

                relative_path = str(
                    file_path.relative_to(
                        PROJECT_ROOT
                    )
                )

            except ValueError:

                relative_path = str(
                    file_path
                )

            schema_records.append(
                {
                    "file": file_path.name,
                    "relative_path": relative_path,
                    "column": None,
                    "column_position": None,
                    "dtype": None,
                    "non_null_count": None,
                    "missing_count": None,
                    "missing_rate": None,
                    "unique_count": None,
                    "sample_min": None,
                    "sample_max": None,
                    "possible_date_or_timestamp": None,
                    "timestamp_precision": None,
                    "inferred_role": None,
                    "inspection_error": repr(exc),
                }
            )

            continue

        print()
        print(
            f"Sample rows loaded: "
            f"{len(sample):,}"
        )

        print(
            f"Columns found: "
            f"{len(sample.columns):,}"
        )

        print()
        print("Columns:")

        for position, column in enumerate(
            sample.columns,
            start=1,
        ):

            print(
                f"  {position:>3}. "
                f"{column}"
            )

        # ---------------------------------------------------------------------
        # Relative source path.
        # ---------------------------------------------------------------------

        try:

            relative_path = str(
                file_path.relative_to(
                    PROJECT_ROOT
                )
            )

        except ValueError:

            relative_path = str(
                file_path
            )

        # ---------------------------------------------------------------------
        # Representative sample output.
        # ---------------------------------------------------------------------

        sample_for_output = (
            sample
            .head(MAX_SAMPLE_ROWS)
            .copy()
        )

        sample_for_output.insert(
            0,
            "source_file",
            file_path.name,
        )

        sample_for_output.insert(
            1,
            "source_relative_path",
            relative_path,
        )

        sample_for_output.insert(
            2,
            "sample_row_number",
            range(
                1,
                len(sample_for_output) + 1,
            ),
        )

        sample_records.append(
            sample_for_output
        )

        # ---------------------------------------------------------------------
        # Column diagnostics.
        # ---------------------------------------------------------------------

        for position, column in enumerate(
            sample.columns,
            start=1,
        ):

            series = sample[column]

            missing_count = int(
                series.isna().sum()
            )

            non_null_count = int(
                series.notna().sum()
            )

            missing_rate = (
                missing_count / len(sample)
                if len(sample) > 0
                else None
            )

            possible_datetime = (
                detect_possible_date(
                    series
                )
            )

            timestamp_precision = None

            if possible_datetime:

                timestamp_precision = (
                    calculate_timestamp_precision(
                        series
                    )
                )

            schema_records.append(
                {
                    "file": file_path.name,

                    "relative_path": relative_path,

                    "column": str(
                        column
                    ),

                    "column_position": position,

                    "dtype": str(
                        series.dtype
                    ),

                    "non_null_count": (
                        non_null_count
                    ),

                    "missing_count": (
                        missing_count
                    ),

                    "missing_rate": (
                        missing_rate
                    ),

                    "unique_count": (
                        safe_unique_count(
                            series
                        )
                    ),

                    "sample_min": (
                        safe_min(
                            series
                        )
                    ),

                    "sample_max": (
                        safe_max(
                            series
                        )
                    ),

                    "possible_date_or_timestamp": (
                        possible_datetime
                    ),

                    "timestamp_precision": (
                        timestamp_precision
                    ),

                    "inferred_role": (
                        infer_column_role(
                            column
                        )
                    ),

                    "inspection_error": None,
                }
            )

    # =============================================================================
    # BUILD OUTPUT DATAFRAMES
    # =============================================================================

    schema = pd.DataFrame(
        schema_records
    )

    if sample_records:

        samples = pd.concat(
            sample_records,
            ignore_index=True,
        )

    else:

        samples = pd.DataFrame()

    # =============================================================================
    # OUTPUT DIRECTORY
    # =============================================================================

    TAQ_PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # =============================================================================
    # SAVE SCHEMA
    # =============================================================================

    schema.to_csv(
        SCHEMA_OUTPUT,
        index=False,
    )

    # =============================================================================
    # SAVE SAMPLES
    # =============================================================================

    samples.to_csv(
        SAMPLES_OUTPUT,
        index=False,
    )

    # =============================================================================
    # SUMMARY
    # =============================================================================

    print_header(
        "SCHEMA INSPECTION COMPLETE"
    )

    print(
        f"Files inspected: "
        f"{len(files):,}"
    )

    print(
        f"Schema rows: "
        f"{len(schema):,}"
    )

    if (
        not schema.empty
        and "column" in schema.columns
    ):

        print(
            f"Unique columns observed: "
            f"{schema['column'].nunique():,}"
        )

    print()

    if not schema.empty:

        print(
            "Potential semantic roles detected:"
        )

        role_counts = {}

        for value in (
            schema[
                "inferred_role"
            ]
            .dropna()
        ):

            for role in str(
                value
            ).split(";"):

                role_counts[role] = (
                    role_counts.get(
                        role,
                        0,
                    )
                    + 1
                )

        if role_counts:

            for role, count in sorted(
                role_counts.items()
            ):

                print(
                    f"  {role:<30} "
                    f"{count:,}"
                )

        else:

            print(
                "  None detected from "
                "column names."
            )

    print()

    print(
        f"Schema output:\n"
        f"{SCHEMA_OUTPUT}"
    )

    print(
        f"Sample output:\n"
        f"{SAMPLES_OUTPUT}"
    )

    return schema, samples


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":

    build_schema_inventory()