import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, ClassVar, get_args, get_origin, get_type_hints

from sqlalchemy import create_engine, inspect, text

from api import MercadoLibreClientHandler
from data_management import DatabaseHandler
from data_modeling import CatalogProduct, ProductsQueryRawOutput
from main import extract_catalog_data


def catalog_details(product_id: str, name: str) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for field_name, field_type in get_type_hints(CatalogProduct).items():
        if get_origin(field_type) is ClassVar:
            continue
        if field_name in {"id", "catalog_product_id"}:
            details[field_name] = product_id
        elif field_name == "name":
            details[field_name] = name
        elif type(None) in get_args(field_type):
            details[field_name] = None
        elif get_origin(field_type) is list:
            details[field_name] = []
        elif get_origin(field_type) is dict:
            details[field_name] = {}
        elif field_type is datetime:
            details[field_name] = datetime.now(UTC)
        else:
            details[field_name] = "sample"
    return details


class StubMercadoLibreClient(MercadoLibreClientHandler):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str | int]]] = []
        self.products = [
            {"id": "MLA-1"},
            {"id": "MLA-2"},
            {"id": "MLA-1"},
        ]

    def get_data(self, url: str, **kwargs: str | int) -> dict[str, Any]:
        self.calls.append((url, kwargs))
        if url.endswith("/products/search"):
            offset = int(kwargs["offset"])
            limit = int(kwargs["limit"])
            return {
                "paging": {"total": len(self.products)},
                "results": self.products[offset : offset + limit],
            }

        product_id = url.rsplit("/", maxsplit=1)[-1]
        details = catalog_details(product_id, f"Name {product_id}")
        details.pop("buy_box_winner")
        details.pop("parent_id")
        return details


class CatalogDatabaseTests(unittest.TestCase):
    def test_setup_adds_domain_id_to_existing_database_without_losing_rows(self) -> None:
        with TemporaryDirectory() as directory:
            database_path = Path(directory) / "legacy.sqlite"
            engine = create_engine(f"sqlite:///{database_path}")
            try:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            "CREATE TABLE bronze_products ("
                            "id INTEGER PRIMARY KEY, "
                            "job_run DATETIME NOT NULL, "
                            "endpoint VARCHAR NOT NULL, "
                            "keywords VARCHAR, "
                            "results JSON NOT NULL, "
                            "paging JSON NOT NULL, "
                            "query_type VARCHAR)"
                        )
                    )
                    connection.execute(
                        text(
                            "INSERT INTO bronze_products "
                            "(job_run, endpoint, keywords, results, paging, query_type) "
                            "VALUES (:job_run, :endpoint, :keywords, :results, "
                            ":paging, :query_type)"
                        ),
                        {
                            "job_run": "2026-01-01 00:00:00",
                            "endpoint": "/products/search",
                            "keywords": "legacy",
                            "results": "[]",
                            "paging": "{}",
                            "query_type": "catalog_product",
                        },
                    )
            finally:
                engine.dispose()

            handler = DatabaseHandler(database_path)
            try:
                handler.setup()
                handler.setup()
                columns = {
                    column["name"]
                    for column in inspect(handler.engine).get_columns("bronze_products")
                }
                self.assertIn("domain_id", columns)
                rows = list(handler.retrieve_data(ProductsQueryRawOutput))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["keywords"], "legacy")
                self.assertIsNone(rows[0]["domain_id"])

                raw_output = ProductsQueryRawOutput(
                    job_run=datetime(2026, 1, 2, tzinfo=UTC),
                    endpoint="/products/search",
                    keywords="new",
                    results=[],
                    paging={"total": 0},
                    query_type="catalog_product",
                    domain_id="MLA-CELLPHONES",
                )
                handler.insert(raw_output)
                handler.insert(raw_output)
                rows = list(handler.retrieve_data(ProductsQueryRawOutput))
                self.assertEqual(len(rows), 3)
                self.assertEqual(
                    [row["domain_id"] for row in rows[1:]],
                    ["MLA-CELLPHONES", "MLA-CELLPHONES"],
                )
            finally:
                handler.close()

    def test_existing_catalog_table_is_extended_and_upserted(self) -> None:
        with TemporaryDirectory() as directory:
            database_path = Path(directory) / "legacy.sqlite"
            engine = create_engine(f"sqlite:///{database_path}")
            try:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            "CREATE TABLE bronze_product_details "
                            "(id VARCHAR PRIMARY KEY)"
                        )
                    )
                    connection.execute(
                        text(
                            "INSERT INTO bronze_product_details (id) VALUES ('MLA-1')"
                        )
                    )
            finally:
                engine.dispose()

            handler = DatabaseHandler(database_path)
            try:
                handler.create_table(CatalogProduct)
                columns = {
                    column["name"]
                    for column in inspect(handler.engine).get_columns(
                        CatalogProduct.entity_name
                    )
                }
                self.assertIn("job_run", columns)

                first = catalog_details("MLA-1", "old name")
                first["job_run"] = datetime(2026, 1, 1, tzinfo=UTC)
                updated = {**first, "name": "updated name"}
                handler.insert(CatalogProduct(**first))
                handler.insert(CatalogProduct(**updated))

                rows = list(handler.retrieve_data(CatalogProduct))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["name"], "updated name")
                self.assertEqual(
                    rows[0]["job_run"], first["job_run"].replace(tzinfo=None)
                )
            finally:
                handler.close()

    def test_catalog_extraction_paginates_and_fetches_each_unique_detail_once(self) -> None:
        with TemporaryDirectory() as directory:
            handler = DatabaseHandler(Path(directory) / "etl.sqlite")
            client = StubMercadoLibreClient()
            job_run = datetime.now(UTC)
            try:
                handler.setup()
                product_ids = extract_catalog_data(
                    handler,
                    client,
                    job_run,
                    pagination_size=2,
                    max_results=3,
                )

                search_calls = [
                    params for url, params in client.calls if url.endswith("/products/search")
                ]
                detail_calls = [
                    url for url, _ in client.calls if not url.endswith("/products/search")
                ]
                raw_rows = list(handler.retrieve_data(ProductsQueryRawOutput))
                detail_rows = list(handler.retrieve_data(CatalogProduct))

                self.assertEqual(product_ids, {"MLA-1", "MLA-2"})
                self.assertEqual(
                    [(call["offset"], call["limit"]) for call in search_calls],
                    [(0, 2), (2, 1)],
                )
                self.assertEqual(
                    detail_calls,
                    [
                        "https://api.mercadolibre.com/products/MLA-1",
                        "https://api.mercadolibre.com/products/MLA-2",
                    ],
                )
                self.assertEqual(len(raw_rows), 2)
                self.assertEqual(len(detail_rows), 2)
                naive_job_run = job_run.replace(tzinfo=None)
                self.assertTrue(
                    all(row["job_run"] == naive_job_run for row in raw_rows)
                )
                self.assertTrue(
                    all(row["job_run"] == naive_job_run for row in detail_rows)
                )
            finally:
                handler.close()


if __name__ == "__main__":
    unittest.main()
