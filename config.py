from pathlib import Path

from dotenv import get_key

TARGET_MODEL: str = "Samsung Galaxy A17"
PAGINATION_SIZE: int = 50
APPLICATION_ROOT_FOLDER: Path = Path().cwd()

URL_BASE: str = "https://api.mercadolibre.com"
CURRENCY_ENDPOINT: str = "/currencies"
CURRENCY_EXCHANGE_ENDPOINT: str = CURRENCY_ENDPOINT + "/conversions"
ITENS_ENDPOINT:str = 

APPLICATION_ID: str | None = get_key(dotenv_path=APPLICATION_ROOT_FOLDER, key_to_get="MELI_ID")
SECRET_KEY: str | None = get_key(dotenv_path=APPLICATION_ROOT_FOLDER, key_to_get="MELI_CLAVE")
