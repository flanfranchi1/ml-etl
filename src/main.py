import config
from dataclasses import fields
import logging
from data_modeling import Credentials


def create_logging():
    logger.setLevel(logging.DEBUG)
    console_log_handler: logging.Handler = logging.StreamHandler()
    log_formater: logging.Formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_log_handler.setFormatter(log_formater)
    logger.addHandler(console_log_handler)


def load_credentials_data(values: dict[str, str | None]) -> Credentials | None:
    target_fields: list[str] = [f.name for f in fields(Credentials)]
    target_values: dict[str, str] = {
        k.lower(): v
        for (k, v) in values.items()
        if k.lower() in target_fields and v != None
    }
    try:
        creds: Credentials = Credentials(**target_values)
    except Exception as e:
        logger.error("Unable to retrieve data from .env: %s", e)
        return None
    else:
        return creds


if __name__ == "__main__":
    logger: logging.Logger = logging.getLogger(name="meli-data-ingestion")
    create_logging()
credentials_data: Credentials = load_credentials_data(config.environment_settings)
