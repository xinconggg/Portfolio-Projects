from __future__ import annotations

from pathlib import Path

from equity_microstructure.data.inventory.inventory import (
    FileInventory,
    get_file_inventory,
)


def profile_dataset_file(
    path: Path,
    dataset: str,
) -> FileInventory:
    """
    Create a basic inventory record for a dataset file.
    """

    return get_file_inventory(
        path,
        dataset=dataset,
    )