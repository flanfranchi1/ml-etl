import json
from collections.abc import Mapping
from typing import Any, cast


def get_product_ids(data: dict[str, list[dict[str, Any]]]) -> set[str]:
    target_data = data["results"]
    products_id: set[str] = {d["id"] for d in target_data}
    return products_id
