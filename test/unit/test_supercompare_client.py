from __future__ import annotations

from typing import Any

import pytest
import requests

from src.product_classification.supercompare.client import SuperCompareClient
from src.product_classification.supercompare.config import SuperCompareConfig


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: object | None = None,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.headers: dict[str, str] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        assert isinstance(response, FakeResponse)
        return response

    def close(self) -> None:
        pass


def test_fetch_category_page_retries_transient_status_and_honors_retry_after() -> None:
    session = FakeSession(
        [
            FakeResponse(status_code=503, headers={"Retry-After": "2"}),
            FakeResponse(
                payload={
                    "totalPages": 1,
                    "data": [
                        {
                            "itemCode": 123,
                            "itemName": "Milk",
                            "manufacturerName": "Dairy",
                        }
                    ],
                }
            ),
        ]
    )
    sleeps: list[float] = []
    client = SuperCompareClient(
        SuperCompareConfig(request_interval_seconds=0),
        session=session,  # type: ignore[arg-type]
        sleep=sleeps.append,
    )

    page = client.fetch_category_page(
        category_slug="dairy-and-eggs",
        subcategory_slug="milk",
        page_number=1,
    )

    assert len(session.calls) == 2
    assert sleeps == [2.0]
    assert page.total_pages == 1
    assert page.products[0].item_code == "123"
    assert page.products[0].main_category == "Dairy & Eggs"


def test_request_retries_ssl_error_with_bounded_backoff() -> None:
    session = FakeSession(
        [
            requests.exceptions.SSLError("temporary TLS error"),
            FakeResponse(text="ok"),
        ]
    )
    sleeps: list[float] = []
    client = SuperCompareClient(
        SuperCompareConfig(
            request_interval_seconds=0,
            backoff_initial_seconds=4,
        ),
        session=session,  # type: ignore[arg-type]
        sleep=sleeps.append,
        random_value=lambda: 0.5,
    )

    response = client._request("https://example.test")

    assert response.text == "ok"
    assert sleeps == [2.0]
    assert len(session.calls) == 2


def test_request_does_not_retry_non_retryable_client_error() -> None:
    session = FakeSession([FakeResponse(status_code=404)])
    client = SuperCompareClient(
        SuperCompareConfig(request_interval_seconds=0),
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(requests.HTTPError, match="404"):
        client._request("https://example.test")

    assert len(session.calls) == 1


def test_parse_taxonomy_filters_parent_and_non_chip_links() -> None:
    category_html = """
        <a href="/he/categories/dairy-and-eggs">Dairy</a>
        <a href="/he/categories/bakery/">Bakery</a>
    """
    subcategory_html = """
        <a class="rounded-full" href="/he/categories/dairy-and-eggs">Parent</a>
        <a class="rounded-full" href="/he/categories/milk">Milk</a>
        <a href="/he/categories/footer-category">Footer</a>
    """

    assert SuperCompareClient._parse_category_slugs(category_html) == (
        "bakery",
        "dairy-and-eggs",
    )
    assert SuperCompareClient._parse_subcategory_slugs(
        subcategory_html,
        "dairy-and-eggs",
    ) == ("milk",)


def test_fetch_category_page_rejects_invalid_payload() -> None:
    session = FakeSession(
        [FakeResponse(payload={"totalPages": 1, "data": "not-a-list"})]
    )
    client = SuperCompareClient(
        SuperCompareConfig(request_interval_seconds=0),
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(TypeError, match="Invalid data list"):
        client.fetch_category_page(
            category_slug="dairy-and-eggs",
            subcategory_slug="milk",
            page_number=1,
        )
