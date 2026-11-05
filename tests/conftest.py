import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-db-tests",
        action="store_true",
        default=False,
        help="Run database integration tests and fail if the test database URL is missing",
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    if session.config.getoption("--run-db-tests") and not (
        os.getenv("HARVEST_EDGE_TEST_DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    ):
        raise pytest.UsageError(
            "--run-db-tests requires HARVEST_EDGE_TEST_DATABASE_URL or TEST_DATABASE_URL"
        )
