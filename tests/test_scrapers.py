import pytest

from harvest_edge.ingestion.base import (
    PublicCashBidScraper,
    ReceivalScheduleScraper,
    ScraperParseError,
)


def test_cash_bid_scraper_maps_public_table_columns() -> None:
    scraper = PublicCashBidScraper(
        "https://example.test/bids",
        {
            "site_code": "Site",
            "commodity_code": "Commodity",
            "grade_code": "Grade",
            "bid_price": "Cash Bid",
        },
        min_interval_seconds=0,
    )

    records = scraper.parse(
        "<table><tr><th>Site</th><th>Commodity</th><th>Grade</th><th>Cash Bid</th></tr>"
        "<tr><td>AB12</td><td>Wheat</td><td>APW1</td><td>312.50</td></tr></table>"
    )

    assert records == [
        {
            "site_code": "AB12",
            "commodity_code": "Wheat",
            "grade_code": "APW1",
            "bid_price": "312.50",
        }
    ]


def test_schedule_scraper_rejects_missing_columns() -> None:
    scraper = ReceivalScheduleScraper(
        "https://example.test/schedule",
        {
            "site_code": "Site",
            "window_name": "Window",
            "start_date": "Start",
            "end_date": "End",
        },
        min_interval_seconds=0,
    )

    with pytest.raises(ScraperParseError, match="Required columns not found"):
        scraper.parse("<table><tr><th>Site</th><th>Window</th></tr></table>")
