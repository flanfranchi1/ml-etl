from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

import config
from data_modeling import Credentials


class MercadoLibreClientHandler:
    def __init__(self, cred: Credentials) -> None:
        self.creds = cred

    def __post_init__(self) -> None:
        self.access_token: str|None = self.creds.access_token
        self.access_token_expiration_date: datetime|None =

    def get_access_token(self) -> None:
        response = httpx.post(
            url=config.OAUT_TOKEN_ENDPOINT,
            headers={
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "client_id": self.creds.client_id,
                "client_secret": self.creds.secret_key,
                "code": self.creds.refresh_token
            },
        )
        payload: dict[str, Any] = response.json()
        self.access_token_expiration_date :datetime = datetime.now(UTC) + timedelta(seconds=payload["expires_in"])
        self.access_token: str= payload["access_token"] 

    def search_item(self, product: str, page_size: int, offset: int) -> dict[str, Any]:
        response: httpx.Response = httpx.get(
            config.SEARCH_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "accept": "application/json",
            },
            params={
                "q": product,
                "condition": "new",
                "limit": page_size,
                "offset": offset,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def access_token_hactivation(self) -> None:
        is_filled: bool = selfaccess_token != None
        is_valid: bool = self.access_token_expiration_date - timedelta(minutes=10) > datetime.now(UTC)
        if is_filled and is_valid:

