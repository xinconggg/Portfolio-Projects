from pathlib import Path

from equity_microstructure.data.schema import (
    inspect_schema,
    save_schema,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DATA = PROJECT_ROOT / "data" / "raw"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"


def main() -> None:

    datasets = {
        "taq": RAW_DATA / "taq" / "taq.csv",
        "taqm": RAW_DATA / "taqm" / "taqm.csv",
    }

    for name, path in datasets.items():

        if not path.exists():
            print(f"Skipping {name}: file not found.")
            continue

        print(f"Building schema: {name}")

        schema = inspect_schema(
            path,
            sample_rows=1000,
        )

        output_path = (
            MANIFEST_DIR
            / f"schema_{name}.json"
        )

        save_schema(
            schema,
            output_path,
        )

        print(f"Written: {output_path}")


if __name__ == "__main__":
    main()