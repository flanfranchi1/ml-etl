from collections.abc import Mapping
from typing import Any, cast


def get_product_ids(data: Mapping[str, Any]) -> set[str]:
    results_value: Any = data.get("results")
    if not isinstance(results_value, list):
        raise ValueError("catalog response must contain a list in 'results'")

    results = cast(list[Any], results_value)
    product_ids: set[str] = set()
    for result_value in results:
        if not isinstance(result_value, Mapping):
            raise ValueError("each catalog result must be an object")
        result_mapping = cast(Mapping[str, Any], result_value)
        product_id = result_mapping.get("id")
        if not isinstance(product_id, str):
            raise ValueError("each catalog result must contain a string 'id'")
        product_ids.add(product_id)
    return product_ids
