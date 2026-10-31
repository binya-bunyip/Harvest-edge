import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping

import httpx
from bs4 import BeautifulSoup

from harvest_edge.config import get_settings

ScrapedRecord = dict[str, str]


class ScraperError(RuntimeError):
    """Base exception for upstream retrieval and parsing failures."""


class ScraperFetchError(ScraperError):
    """An upstream request failed after the configured retry policy."""


class ScraperParseError(ScraperError):
    """An upstream response did not match the configured table schema."""


class BaseScraper(ABC):
    max_attempts = 3

    def __init__(self, source_url: str, min_interval_seconds: float | None = None) -> None:
        self.source_url = source_url
        self.min_interval_seconds = (
            get_settings().scraper_min_interval_seconds
            if min_interval_seconds is None
            else min_interval_seconds
        )
        self._request_lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def fetch_records(self) -> list[ScrapedRecord]:
        timeout = get_settings().http_timeout_seconds
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for attempt in range(self.max_attempts):
                await self._wait_for_rate_limit()
                try:
                    response = await client.get(self.source_url)
                except httpx.TransportError as exc:
                    if attempt + 1 == self.max_attempts:
                        raise ScraperFetchError(
                            f"Request to {self.source_url} failed: {exc}"
                        ) from exc
                    await asyncio.sleep(min(2**attempt, 8))
                    continue

                if response.status_code == 429 or response.status_code >= 500:
                    if attempt + 1 == self.max_attempts:
                        try:
                            response.raise_for_status()
                        except httpx.HTTPStatusError as exc:
                            raise ScraperFetchError(
                                f"Upstream returned HTTP {response.status_code}"
                            ) from exc
                    await asyncio.sleep(self._retry_delay(response, attempt))
                    continue
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise ScraperFetchError(
                        f"Upstream returned HTTP {response.status_code}"
                    ) from exc
                return self.parse(response.text)
        raise ScraperFetchError(f"Request to {self.source_url} failed after retries")

    async def _wait_for_rate_limit(self) -> None:
        async with self._request_lock:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self.min_interval_seconds:
                await asyncio.sleep(self.min_interval_seconds - elapsed)
            self._last_request_at = time.monotonic()

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return min(max(float(retry_after), 0.0), 60.0)
            except ValueError:
                pass
        return min(2**attempt, 8)

    @abstractmethod
    def parse(self, body: str) -> list[ScrapedRecord]:
        raise NotImplementedError


class PublicHtmlTableScraper(BaseScraper):
    required_fields: frozenset[str] = frozenset()

    def __init__(
        self,
        source_url: str,
        column_map: Mapping[str, str],
        min_interval_seconds: float | None = None,
    ) -> None:
        super().__init__(source_url, min_interval_seconds)
        self.column_map = dict(column_map)
        missing_fields = self.required_fields.difference(self.column_map)
        if missing_fields:
            raise ValueError(
                f"Missing required field mappings: {', '.join(sorted(missing_fields))}"
            )

    def parse(self, body: str) -> list[ScrapedRecord]:
        soup = BeautifulSoup(body, "html.parser")
        table = soup.find("table")
        if table is None:
            raise ScraperParseError("No HTML table found in upstream response")
        rows = table.find_all("tr")
        if not rows:
            raise ScraperParseError("HTML table contains no rows")

        headers = [
            cell.get_text(" ", strip=True).casefold() for cell in rows[0].find_all(["th", "td"])
        ]
        header_indexes = {header: index for index, header in enumerate(headers)}
        missing_columns = set(self.column_map.values()).difference(header_indexes)
        missing_columns = {
            column for column in missing_columns if column.casefold() not in header_indexes
        }
        if missing_columns:
            raise ScraperParseError(
                f"Required columns not found: {', '.join(sorted(missing_columns))}"
            )
        normalized_indexes = {header.casefold(): index for index, header in enumerate(headers)}

        records: list[ScrapedRecord] = []
        for row in rows[1:]:
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            if not cells or not any(cells):
                continue
            if len(cells) != len(headers):
                raise ScraperParseError("HTML table row does not match the header column count")
            records.append(
                {
                    field: cells[normalized_indexes[column.casefold()]]
                    for field, column in self.column_map.items()
                }
            )
        return records


class PublicCashBidScraper(PublicHtmlTableScraper):
    required_fields = frozenset({"site_code", "commodity_code", "grade_code", "bid_price"})


class ReceivalScheduleScraper(PublicHtmlTableScraper):
    required_fields = frozenset({"site_code", "window_name", "start_date", "end_date"})
