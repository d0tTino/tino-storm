"""Client helpers for the remote Docs Hub service."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

import httpx


class DocsHubClientError(RuntimeError):
    """Base exception raised when the Docs Hub client fails."""


class DocsHubClientNotConfigured(DocsHubClientError):
    """Raised when the client is used without a configured endpoint."""


class DocsHubRemoteError(DocsHubClientError):
    """Raised when the remote Docs Hub service returns an error."""


def _load_timeout(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        logging.warning(
            "Invalid STORM_DOCS_HUB_TIMEOUT value %r – falling back to default", value
        )
        return None


def _load_extra_headers(value: Optional[str]) -> Dict[str, str]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        logging.warning("Failed to parse STORM_DOCS_HUB_HEADERS: %s", exc)
        return {}
    if not isinstance(parsed, Mapping):  # pragma: no cover - defensive
        logging.warning("STORM_DOCS_HUB_HEADERS must be a JSON object")
        return {}
    return {str(key): str(val) for key, val in parsed.items()}


@dataclass
class DocsHubClient:
    """HTTP client used to talk to a remote Docs Hub instance."""

    base_url: Optional[str] = None
    api_key: Optional[str] = None
    timeout: Optional[float] = None
    extra_headers: Optional[Dict[str, str]] = None

    def __post_init__(self) -> None:
        if self.base_url is None:
            self.base_url = os.getenv("STORM_DOCS_HUB_URL")
        if self.api_key is None:
            self.api_key = os.getenv("STORM_DOCS_HUB_API_KEY")
        if self.timeout is None:
            self.timeout = _load_timeout(os.getenv("STORM_DOCS_HUB_TIMEOUT"))
        if self.extra_headers is None:
            self.extra_headers = _load_extra_headers(
                os.getenv("STORM_DOCS_HUB_HEADERS")
            )

    @property
    def is_configured(self) -> bool:
        """Return ``True`` when a remote endpoint is configured."""

        return bool(self.base_url)

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.extra_headers:
            headers.update(self.extra_headers)
        return headers

    def _build_payload(
        self,
        query: str,
        vaults: Iterable[str],
        *,
        k_per_vault: int,
        rrf_k: int,
        chroma_path: Optional[str],
        vault: Optional[str],
        timeout: Optional[float],
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "query": query,
            "vaults": list(vaults),
            "k_per_vault": k_per_vault,
            "rrf_k": rrf_k,
        }
        if chroma_path is not None:
            payload["chroma_path"] = chroma_path
        if vault is not None:
            payload["vault"] = vault
        if timeout is not None:
            payload["timeout"] = timeout
        return payload

    def _normalise_response(self, data: Any) -> List[Mapping[str, Any]]:
        if isinstance(data, Mapping):
            data = data.get("results", data.get("data", data))
        if not isinstance(data, list):
            raise DocsHubRemoteError("Docs Hub response must be a list of results")
        normalised: List[Mapping[str, Any]] = []
        for item in data:
            if not isinstance(item, Mapping):
                raise DocsHubRemoteError("Docs Hub results must be mappings")
            normalised.append(item)
        return normalised

    def _request_kwargs(
        self, *, timeout: Optional[float] = None
    ) -> MutableMapping[str, Any]:
        kwargs: MutableMapping[str, Any] = {}
        effective_timeout = timeout if timeout is not None else self.timeout
        if effective_timeout is not None:
            kwargs["timeout"] = effective_timeout
        return kwargs

    def search(
        self,
        query: str,
        vaults: Iterable[str],
        *,
        k_per_vault: int,
        rrf_k: int,
        chroma_path: Optional[str],
        vault: Optional[str],
        timeout: Optional[float],
    ) -> List[Mapping[str, Any]]:
        """Synchronously query the remote Docs Hub API."""

        if not self.is_configured:
            raise DocsHubClientNotConfigured("STORM_DOCS_HUB_URL is not configured")

        payload = self._build_payload(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            timeout=timeout,
        )
        headers = self._build_headers()
        request_kwargs = self._request_kwargs(timeout=timeout)
        try:
            with httpx.Client(**request_kwargs) as client:
                response = client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DocsHubRemoteError(str(exc)) from exc
        return self._normalise_response(response.json())

    async def search_async(
        self,
        query: str,
        vaults: Iterable[str],
        *,
        k_per_vault: int,
        rrf_k: int,
        chroma_path: Optional[str],
        vault: Optional[str],
        timeout: Optional[float],
    ) -> List[Mapping[str, Any]]:
        """Asynchronously query the remote Docs Hub API."""

        if not self.is_configured:
            raise DocsHubClientNotConfigured("STORM_DOCS_HUB_URL is not configured")

        payload = self._build_payload(
            query,
            vaults,
            k_per_vault=k_per_vault,
            rrf_k=rrf_k,
            chroma_path=chroma_path,
            vault=vault,
            timeout=timeout,
        )
        headers = self._build_headers()
        request_kwargs = self._request_kwargs(timeout=timeout)
        try:
            async with httpx.AsyncClient(**request_kwargs) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DocsHubRemoteError(str(exc)) from exc
        return self._normalise_response(response.json())


def get_docs_hub_client() -> DocsHubClient:
    """Return a DocsHubClient configured from environment variables."""

    return DocsHubClient()


__all__ = [
    "DocsHubClient",
    "DocsHubClientError",
    "DocsHubClientNotConfigured",
    "DocsHubRemoteError",
    "get_docs_hub_client",
]
