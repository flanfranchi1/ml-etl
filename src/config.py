from dataclasses import fields
from pathlib import Path

import dotenv

from src.data_modeling import Credentials

TARGET_MODEL: str = "Samsung Galaxy A17"
PAGINATION_SIZE: int = 50
APPLICATION_ROOT_FOLDER: Path = Path().cwd()
DOT_ENV_FILE: Path = Path(APPLICATION_ROOT_FOLDER).joinpath(".env")
LOG_PATH: Path = APPLICATION_ROOT_FOLDER.joinpath("logs")
URL_BASE: str = "https://api.mercadolibre.com"
OAUT_TOKEN_ENDPOINT: str = URL_BASE + "/oauth/token"
COUNTRY_BASE_URL: str = URL_BASE + "/sites/MLA"
SEARCH_ENDPOINT: str = COUNTRY_BASE_URL + "/search"
CURRENCY_ENDPOINT: str = "/currencies"
CURRENCY_EXCHANGE_ENDPOINT: str = CURRENCY_ENDPOINT + "/conversions"
ITENS_ENDPOINT: str = URL_BASE + "/items"
environment_settings: dict[str, str | None] = dotenv.dotenv_values(DOT_ENV_FILE)


def load_credentials_data(values: dict[str, str | None]) -> Credentials:
    target_fields: list[str] = [f.name for f in fields(Credentials)]
    target_values: dict[str, str] = {
        k.lower(): v
        for (k, v) in values.items()
        if k.lower() in target_fields and v != None
    }
    return Credentials(**target_values)


current_credentials: Credentials = load_credentials_data(environment_settings)
