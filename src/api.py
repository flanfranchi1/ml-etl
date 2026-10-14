import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

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
        limiter: int | None = None
        current_offset: int = 0
        while limiter is None or kwargs["offset"] < limiter:
            kwargs.update({"offset": current_offset})
            output: dict[str, Any] = self.get_data(url=url, **kwargs)
            paging = output.get("paging", {})
            results = output.get("results", [])
            if isinstance(paging.get("total"), int):
                limiter = min(max_results, paging["total"])
            current_offset += pagination
            yield output

            if not results:
                break

            kwargs.update({"offset": kwargs["offset"] + len(results)})
