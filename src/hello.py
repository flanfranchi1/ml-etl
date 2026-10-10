import logging
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

import config
from data_modeling import Credentials

class TokenServices:
    def __init__(self, credentials:Credentials) -> None:
        self._credentials = credentials

    def __getattr__(self, name:str):
        return getattr(self._credentials, name)

    def get_valid_access_token(self, get_func:Callable[[...], httpx.Response]) -> None:
        expiration_date: datetime = datetime.fromisoformat(self.access_token_expiration_date)
        if expiration_date >= datetime.now(UTC) + timedelta(minutes=10):
            try:
                response = get_func()
            except Exception as e:
                logging.error("Unable to refresh token: %s", e)
                return
            else:
                response_json: dict[str, Any] = response.
                token_lifetime: int = int(response_json['xpires_in'])
                new_expiration_date: datetime = datetime.now(UTC) + timedelta(seconds=token_lifetime)
def api_token_get() -> dict[str, str]:
    """As described by the current documentation this is a mandatory process for subsequent requests"""
    response = httpx.post(
        url=config.OAUT_TOKEN_ENDPOINT,
        headers={
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "client_credentials",
            "client_id": ,
            "client_secret": config.SECRET_KEY,
        },
    )
    return response.json()


def api_search_product(access_token: str) -> dict[str, Any]:
    response: httpx.Response = httpx.get(
        config.SEARCH_ENDPOINT,
        headers={
            "Authorization": f"Bearer {access_token}",
            "accept": "application/json",
        },
        params={
            "q": config.TARGET_MODEL,
            "condition": "new",
            "limit": 50,
            "offset": 0,
        },
        timeout=30,
    )
    print("Status:", response.status_code)
    print("Resposta:", response.text[:2000])
    response.raise_for_status()
    return response.json()


def test_api(access_token: str) -> None:
    response = httpx.get(
        "https://api.mercadolibre.com/currencies/ARS",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        timeout=20.0,
    )

    print("Status:", response.status_code)
    print("Resposta:", response.text[:500])


def main():
    logger: logging.Logger = logging.getLogger(name="meli-data-ingestion")
    logger.setLevel(logging.DEBUG)
    console_log_handler: logging.Handler = logging.StreamHandler()
    log_formater: logging.Formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_log_handler.setFormatter(log_formater)
    logger.addHandler(console_log_handler)
    logger.info("Starting a brand new run")
    initial_header: dict[str, str] = api_token_get()
    # search_results: dict[str, Any] = api_search_product(initial_header["user_id"])
    # print(search_results)
    test_api(initial_header["user_id"])


def load_params(values:dict[str, str|None]) -> IdentityManager:
    target_fields: list[str] = [f.name for f in fields(IdentityManager)]
    target_values: dict[str,str] = {k.lower(): v for (k,v) in values.items() if k.lower() in target_fields and v != None}
    
if __name__ == "__main__":
    current_date: datetime = datetime.now(tz=UTC)
    try:

    main()
