import os
import tempfile
from dataclasses import asdict, fields, replace
from pathlib import Path

import dotenv

from data_modeling import Credentials


class CredentialStoreManager:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.credentials: Credentials = Credentials(
            access_token=None,
            access_token_expiration_date=None,
            client_id=None,
            secret_key=None,
            refresh_token=None,
            refresh_token_expiration_date=None,
        )
        self.target_fields: list[str] = [
            field.name for field in fields(self.credentials)
        ]

    def load_credentials_data(self) -> None:
        env_values = dotenv.dotenv_values(self.file_path)

        target_values = {
            key.lower(): value
            for key, value in env_values.items()
            if key.lower() in self.target_fields and value is not None
        }
        self.credentials = replace(self.credentials, **target_values)

    def update_keys(self, **kwargs: str) -> bool:
        updated_cred: Credentials = replace(self.credentials, **kwargs)
        if not self._save_to_file(creds=updated_cred, file_path=self.file_path):
            return False

        self.credentials = updated_cred
        return True

    def _save_to_file(self, creds: Credentials, file_path: Path) -> bool:
        fd, temp_name = tempfile.mkstemp(
            dir=file_path.parent, prefix=f".{file_path.name}.", suffix=".tmp"
        )

        temp_file: Path = Path(temp_name)

        os.close(fd)

        payload: dict[str, str] = {
            k: v for (k, v) in asdict(creds).items() if v is not None
        }

        try:
            for key, value in payload.items():
                success, _, _ = dotenv.set_key(
                    key_to_set=key,
                    value_to_set=value,
                    dotenv_path=temp_file,
                    quote_mode="always",
                )

                if not success:
                    raise OSError(f"Unable to persist key {key}.")

            if not self._check_integrity(written_file=temp_file, new_creds=creds):
                return False

            os.replace(temp_file, file_path)
            return True
        finally:
            temp_file.unlink(missing_ok=True)

    def _check_integrity(self, written_file: Path, new_creds: Credentials) -> bool:
        written_cred_dict: dict[str, str | None] = dotenv.dotenv_values(written_file)
        new_cred_dict: dict[str, str] = {
            k: v for (k, v) in asdict(new_creds).items() if v is not None
        }
        return written_cred_dict == new_cred_dict


ACCESS_TOKEN_REFRESH_ANTICIPATION_IN_MINUTES: int = 10
TARGET_MODEL: str = "smartphone Samsung Galaxy A16 5g"
PAGINATION_SIZE: int = 50
MAX_RESULTS: int = 100
DOMAIN_ID: str = "MLA-CELLPHONES"
APPLICATION_ROOT_FOLDER: Path = Path().cwd()
DATABASE_LOCATION = APPLICATION_ROOT_FOLDER.joinpath("data/database.db")
DOT_ENV_FILE: Path = Path(APPLICATION_ROOT_FOLDER).joinpath(".env")
LOG_PATH: Path = APPLICATION_ROOT_FOLDER.joinpath("logs")
URL_BASE: str = "https://api.mercadolibre.com"
OAUT_TOKEN_ENDPOINT: str = URL_BASE + "/oauth/token"
COUNTRY_BASE_URL: str = URL_BASE + "/sites/MLA"
SEARCH_ENDPOINT: str = COUNTRY_BASE_URL + "/search"
CATALOG_SEARCH_ENDPOINT: str = URL_BASE + "/products/search"
PRODUCT_DETAILS: str = URL_BASE + "/products"
CURRENCY_ENDPOINT: str = URL_BASE + "/currencies"
CURRENCY_EXCHANGE_ENDPOINT: str = CURRENCY_ENDPOINT + "/conversions"
ITENS_ENDPOINT: str = URL_BASE + "/items"
