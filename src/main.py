import logging
from datetime import UTC, datetime
from typing import Any

import config
from api import MercadoLibreClientHandler
from data_management import DatabaseHandler
from data_modeling import CatalogProduct, ProductsQueryRawOutput
from transformations import get_product_ids

logger = logging.getLogger("meli-data-ingestion")


def create_logging() -> None:
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        logger.addHandler(console_handler)


def extract_catalog_data(
    dbh: DatabaseHandler,
    ml_client: MercadoLibreClientHandler,
    job_run: datetime,
    *,
    target_model: str = config.TARGET_MODEL,
    domain_id: str = config.DOMAIN_ID,
    pagination_size: int = config.PAGINATION_SIZE,
    max_results: int = config.MAX_RESULTS,
) -> set[str]:
    dbh.create_table(CatalogProduct)
    product_ids: set[str] = set()

    pages = ml_client.paginated_query(
        url=config.CATALOG_SEARCH_ENDPOINT,
        pagination=pagination_size,
        max_results=max_results,
        site_id="MLA",
        status="active",
        domain_id=domain_id,
        q=target_model,
        condition="new",
    )
    for page in pages:
        raw_output = ProductsQueryRawOutput(
            job_run=job_run,
            endpoint=config.CATALOG_SEARCH_ENDPOINT,
            keywords=target_model,
            results=page["results"],
            paging=page["paging"],
            query_type="catalog_product",
            domain_id=domain_id,
        )
        dbh.insert(raw_output)
        product_ids.update(get_product_ids(page))

    for product_id in sorted(product_ids):
        details: dict[str, Any] = ml_client.get_data(
            url=f"{config.PRODUCT_DETAILS}/{product_id}",
        )
        dbh.insert(CatalogProduct.from_api_response(details, job_run))

    logger.info(
        "Persisted catalog search and details for %d products",
        len(product_ids),
    )
    return product_ids


def extraction(dbh: DatabaseHandler, job_run: datetime) -> set[str]:
    credential_manager = config.CredentialStoreManager(config.DOT_ENV_FILE)
    ml_client = MercadoLibreClientHandler(credential_manager)
    ml_client.ensure_access_token()
    return extract_catalog_data(dbh, ml_client, job_run)


def transformation(dbh: DatabaseHandler) -> set[str]:
    product_ids: set[str] = set()
    for raw_data in dbh.retrieve_data(ProductsQueryRawOutput):
        product_ids.update(get_product_ids(raw_data))
    return product_ids


def main() -> None:
    create_logging()
    job_run = datetime.now(UTC)
    logger.info("Starting ETL process with job_run: %s", job_run)

    dbh = DatabaseHandler(config.DATABASE_LOCATION)
    try:
        dbh.setup()
        extraction(dbh, job_run)
    finally:
        dbh.close()


if __name__ == "__main__":
    main()
