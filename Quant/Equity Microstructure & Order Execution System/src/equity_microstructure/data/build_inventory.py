from pathlib import Path

from equity_microstructure.data.inventory import (
    inspect_dataset,
    save_inventory,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DATA = PROJECT_ROOT / "data" / "raw"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"


def main() -> None:
    datasets = {
        "taq": RAW_DATA / "taq" / "taq.csv",
        "taqm": RAW_DATA / "taqm" / "taqm.csv",
        "crsp": RAW_DATA / "crsp" / "crsp.csv",
    }

    inventory = []

    for name, path in datasets.items():
        print(f"Inspecting: {name}")
        print(f"Path:      {path}")

        result = inspect_dataset(
            name=name,
            path=path,
            sample_rows=5,
        )

        inventory.append(result)

        if result.exists:
            print(f"Size GB:   {result.size_gb}")
            print(f"Columns:   {result.n_columns}")
        else:
            print("Status:    NOT FOUND")

        print()

    output_path = MANIFEST_DIR / "data_inventory.json"

    save_inventory(
        inventory,
        output_path,
    )

    print(f"Inventory written to: {output_path}")


if __name__ == "__main__":
    main()