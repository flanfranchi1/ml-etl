import csv
import logging
from datetime import UTC, datetime

import config
from api import MercadoLibreClientHandler
from data_management import DatabaseHandler
from data_modeling import ProductsQueryRawOutput
from transformations import get_product_ids


def create_logging():
    logger.setLevel(logging.DEBUG)
    console_log_handler: logging.Handler = logging.StreamHandler()
    log_formater: logging.Formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_log_handler.setFormatter(log_formater)
    logger.addHandler(console_log_handler)


def extraction():
    csm: config.CredentialStoreManager = config.CredentialStoreManager(
        config.DOT_ENV_FILE
    )
    ml_client: MercadoLibreClientHandler = MercadoLibreClientHandler(csm)
    ml_client.ensure_access_token()
    for page in ml_client.paginated_query(
        url=config.SEARCH_ENDPOINT,
        pagination=config.PAGINATION_SIZE,
        offset=0,
        max_results=100,
        site_id="MLA",
        status="active",
        q=config.TARGET_MODEL,
        condition="new",
    ):
        try:
            page.update({"job_run": job_run, "endpoint": config.SEARCH_ENDPOINT})
            output = ProductsQueryRawOutput(**page)
            dbh.insert(output)
        except Exception as e:
            logger.error("Can't complete all requests: %s", e)


def extraction_itens(ids: set[str]):
    csm: config.CredentialStoreManager = config.CredentialStoreManager(
        config.DOT_ENV_FILE
    )
    ml_client: MercadoLibreClientHandler = MercadoLibreClientHandler(csm)
    ml_client.ensure_access_token()
    for page in ml_client.paginated_query(
        url=config.ITENS_ENDPOINT,
        pagination=config.PAGINATION_SIZE,
        # offset=0,
        keywords=config.TARGET_MODEL,
        # max_results=100,
        # site_id="MLA",
        # condition="new",
    ):
        try:
            page.update({"job_run": job_run, "endpoint": config.SEARCH_ENDPOINT})
            output = ProductsQueryRawOutput(**page)
            dbh.insert(output)
        except Exception as e:
            logger.error("Can't complete all requests: %s", e)


def transformation() -> set[str]:
    data: set[str] = set()
    for raw_data in dbh.retrieve_data(ProductsQueryRawOutput):
        data.update(get_product_ids(raw_data))
    return data


if __name__ == "__main__":
    job_run: datetime = datetime.now(UTC)
    logger: logging.Logger = logging.getLogger(name="meli-data-ingestion")
    create_logging()
    logger.info("starting ETL process identified with job_run: %s", job_run)
    dbh = DatabaseHandler(config.DATABASE_LOCATION)
    dbh.setup()
    # extraction()
    ids = transformation()
    extraction_itens(ids)
