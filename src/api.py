import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import httpx

import config
from data_modeling import Credentials

logger = logging.getLogger(__name__)


class MercadoLibreClientHandler:
    def __init__(self, cred_mngr: config.CredentialStoreManager) -> None:
        cred_mngr.load_credentials_data()
        self.cred_mngr = cred_mngr
        self.credential: Credentials = cred_mngr.credentials

        self.access_token: str | None = self.credential.access_token
        self.refresh_token: str | None = self.credential.refresh_token

        self.access_token_expiration_date: datetime | None = None

        if self.credential.access_token_expiration_date:
            self.access_token_expiration_date = datetime.fromisoformat(
                self.credential.access_token_expiration_date
            )
            self.refresh_threshold: datetime = (
                self.access_token_expiration_date
                - timedelta(minutes=config.ACCESS_TOKEN_REFRESH_ANTICIPATION_IN_MINUTES)
            )

    def ensure_access_token(self) -> None:
        if (
            self.access_token is not None
            and self.access_token_expiration_date is not None
            and datetime.now(UTC) < self.refresh_threshold
        ):
            return

        self.refresh_access_token()

    def obtainning_access_token_from_code(self):
        response: httpx.Response = httpx.post(
            url=config.OAUT_TOKEN_ENDPOINT,
            headers={
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "client_id": self.credential.client_id,
                "client_secret": self.credential.secret_key,
                "code": self.credential.refresh_token,
                "redirect_uri": "https://felan.com.br",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload: dict[str, str] = response.json()
        self.access_token = payload["access_token"]
        expiration_in_seconds: int = int(payload["expires_in"])
        self.access_token_expiration_date = datetime.now(UTC) + timedelta(
            seconds=expiration_in_seconds
        )
        self.refresh_token = payload["refresh_token"]
        self.cred_mngr.update_keys(
            access_token=self.access_token,
            refresh_token=self.refresh_token,
            access_token_expiration_date=datetime.isoformat(
                self.access_token_expiration_date
            ),
        )

    def refresh_access_token(self) -> None:
        if not self.refresh_token:
            raise RuntimeError(
                "Missing refresh token. provide a new one on '%s'", config.DOT_ENV_FILE
            )

        response = httpx.post(
            url=config.OAUT_TOKEN_ENDPOINT,
            headers={
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "client_id": self.credential.client_id,
                "client_secret": self.credential.secret_key,
                "refresh_token": self.refresh_token,
            },
            timeout=30.0,
        )

        response.raise_for_status()
        payload: dict[str, Any] = response.json()

        self.access_token = payload["access_token"]
        self.refresh_token = payload["refresh_token"]

        self.access_token_expiration_date = datetime.now(UTC) + timedelta(
            seconds=int(payload["expires_in"])
        )
        self.refresh_threshold: datetime = (
            self.access_token_expiration_date
            - timedelta(minutes=config.ACCESS_TOKEN_REFRESH_ANTICIPATION_IN_MINUTES)
        )
        self.cred_mngr.update_keys(
            access_token=payload["access_token"],
            access_token_expiration_date=datetime.isoformat(
                self.access_token_expiration_date
            ),
            refresh_token=payload["refresh_token"],
        )

    def get_data(self, url: str, **kwargs: str | int) -> dict[str, Any]:
        self.ensure_access_token()

        response: httpx.Response = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "accept": "application/json",
            },
            params=kwargs,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def paginated_query(
        self,
        url: str,
        pagination: int = 1_000_000,
        max_results: int = 10_000,
        **kwargs: Any,
    ) -> Iterator[dict[str, Any]]:
        if pagination <= 0:
            raise ValueError("pagination must be greater than zero")
        if max_results < 0:
            raise ValueError("max_results cannot be negative")

        current_offset = kwargs.pop("offset", 0)
        if not isinstance(current_offset, int) or current_offset < 0:
            raise ValueError("offset must be a non-negative integer")

        total: int | None = None
        fetched = 0
        while fetched < max_results and (total is None or current_offset < total):
            page_size = min(pagination, max_results - fetched)
            params: dict[str, str | int] = {}
            for key, value in kwargs.items():
                if not isinstance(value, (str, int)):
                    raise TypeError(
                        f"query parameter {key!r} must be a string or integer"
                    )
                params[key] = value
            params["offset"] = current_offset
            params["limit"] = page_size
            output = self.get_data(url=url, **params)
            paging_value: Any = output.get("paging", {})
            if not isinstance(paging_value, dict):
                raise TypeError("paginated response 'paging' must be an object")
            paging = cast(dict[str, Any], paging_value)
            results_value: Any = output.get("results", [])
            if not isinstance(results_value, list):
                raise TypeError("paginated response 'results' must be a list")
            results = cast(list[Any], results_value)
            reported_total = paging.get("total")
            if isinstance(reported_total, int):
                total = reported_total

            yield output

            if not results:
                break

            fetched += len(results)
            current_offset += len(results)
            if total is None and len(results) < page_size:
                break
