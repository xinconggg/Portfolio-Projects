from pathlib import Path

from equity_microstructure.data.inventory.crsp import (
    write_crsp_inventory,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_CRSP_DIR = PROJECT_ROOT / "data" / "raw" / "crsp"

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
    / "crsp_inventory.csv"
)


def main() -> None:
    inventory = write_crsp_inventory(
        raw_crsp_dir=RAW_CRSP_DIR,
        output_path=OUTPUT_PATH,
    )

    print(f"CRSP files inventoried: {len(inventory)}")
    print(f"Output: {OUTPUT_PATH}")
    print()
    print(
        inventory[
            [
                "filename",
                "size_mb",
                "n_columns",
                "role",
                "date_candidates",
                "identifier_candidates",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()