from __future__ import annotations

from equity_microstructure.config import DATASET_FILES
from equity_microstructure.data.inventory.inventory import (
    get_file_inventory,
)


def main() -> None:
    """Run basic inventory over configured datasets."""

    for dataset, path in DATASET_FILES.items():
        print("=" * 80)
        print(f"Dataset: {dataset}")
        print(f"Path:    {path}")
        print("=" * 80)

        if not path.exists():
            print("STATUS: FILE NOT FOUND")
            print()
            continue

        inventory = get_file_inventory(
            path,
            dataset=dataset,
        )

        print(f"Filename:    {inventory.filename}")
        print(f"Extension:   {inventory.extension}")
        print(f"Size:        {inventory.size_mb:,.2f} MB")
        print(f"Columns:     {inventory.n_columns}")

        print("\nColumn names:")
        for i, column in enumerate(inventory.columns, start=1):
            print(f"{i:>3}. {column}")

        print()


if __name__ == "__main__":
    main()