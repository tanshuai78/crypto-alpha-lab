import json

from scripts.external_signal_shadow.collect_stage1_5a_external_catalyst_events import (
    classify_event_type,
    collect_records_from_binance_cms_json,
    collect_records_from_html,
    extract_symbols_from_title,
    load_rows_from_source_file,
    write_jsonl,
)


def test_collects_binance_cms_articles_into_stage1_5a_rows(tmp_path):
    payload = {
        "data": {
            "catalogs": [
                {
                    "articles": [
                        {
                            "title": "Binance Will Delist ABC and XYZ on 2024-04-03",
                            "releaseDate": 1710921600000,
                            "code": "binance-will-delist-abc-and-xyz",
                        }
                    ]
                }
            ]
        }
    }

    rows = collect_records_from_binance_cms_json(payload, source_url="https://www.binance.com/bapi/test")

    assert len(rows) == 1
    assert rows[0]["title"] == "Binance Will Delist ABC and XYZ on 2024-04-03"
    assert rows[0]["time"] == 1710921600000
    assert rows[0]["symbol"] == ["ABC", "XYZ"]
    assert rows[0]["url"].startswith("https://www.binance.com/en/support/announcement/")
    assert rows[0]["manual_review_required"] is True
    assert "api_key" not in rows[0]


def test_classifies_and_filters_non_catalyst_titles():
    assert classify_event_type("Binance Will Delist ABC") == "exchange_delisting_notice"
    assert classify_event_type("Binance Futures Will Launch USD-M ABC Perpetual Contract") == "futures_contract_launch"
    assert classify_event_type("Binance Adds ABC to Cross Margin") == "margin_enablement"
    assert classify_event_type("Binance Completes Wallet Maintenance") == "unknown"


def test_extract_symbols_from_title_excludes_exchange_words():
    symbols = extract_symbols_from_title("OKX to Delist ABC and XYZ Trading Pairs on 2024-04-05")
    assert symbols == ["ABC", "XYZ"]


def test_extract_symbols_prefers_usdt_contract_base_asset():
    symbols = extract_symbols_from_title("Binance Futures Will Launch USDⓈ-Margined ARXUSDT Perpetual Contract")
    assert symbols == ["ARX"]


def test_extract_symbols_uses_parenthesized_tickers_for_bstocks():
    symbols = extract_symbols_from_title(
        "Binance Exchange Adds bStocks Advanced Micro Devices (AMDB), Intel (INTCB) Trading Pair(s)"
    )
    assert symbols == ["AMDB", "INTCB"]


def test_extract_symbols_returns_empty_for_multiple_generic_launch_without_tickers():
    symbols = extract_symbols_from_title("Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts")
    assert symbols == []


def test_collects_okx_like_html_title_url_and_published_time():
    html = """
    <html><body>
      <a href="/help/okx-to-delist-abc-and-xyz">OKX to Delist ABC and XYZ Trading Pairs</a>
      <span>Published on Mar 22, 2024</span>
    </body></html>
    """

    rows = collect_records_from_html(
        html,
        source_url="https://www.okx.com/en-us/help/section/announcements-delistings",
        source_name="okx_official_announcements",
    )

    assert len(rows) == 1
    assert rows[0]["title"] == "OKX to Delist ABC and XYZ Trading Pairs"
    assert rows[0]["url"] == "https://www.okx.com/help/okx-to-delist-abc-and-xyz"
    assert rows[0]["time"] == 1711065600000
    assert rows[0]["symbol"] == ["ABC", "XYZ"]


def test_write_jsonl_dedupes_and_writes_stage1_5a_safe_rows(tmp_path):
    rows = [
        {
            "title": "Binance Will Delist ABC",
            "time": 1710921600000,
            "symbol": ["ABC"],
            "url": "https://www.binance.com/en/support/announcement/a",
            "source_url": "https://www.binance.com/bapi/test",
            "manual_review_required": True,
        },
        {
            "title": "Binance Will Delist ABC",
            "time": 1710921600000,
            "symbol": ["ABC"],
            "url": "https://www.binance.com/en/support/announcement/a",
            "source_url": "https://www.binance.com/bapi/test",
            "manual_review_required": True,
        },
    ]
    out = tmp_path / "events.jsonl"

    written = write_jsonl(rows, out)

    assert written == 1
    loaded = [json.loads(line) for line in out.read_text().splitlines()]
    assert loaded == [rows[0]]


def test_load_rows_from_source_file_supports_jsonl(tmp_path):
    source = tmp_path / "announcements.jsonl"
    source.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "title": "Binance Will Delist ABC",
                        "time": 1710921600000,
                        "symbol": "ABC",
                        "url": "https://www.binance.com/en/support/announcement/a",
                    }
                ),
                json.dumps(
                    {
                        "title": "Binance Completes Wallet Maintenance",
                        "time": 1710921700000,
                        "symbol": "BTC",
                        "url": "https://www.binance.com/en/support/announcement/b",
                    }
                ),
            ]
        )
    )

    rows = load_rows_from_source_file(str(source), source_name="manual_source_file")

    assert len(rows) == 1
    assert rows[0]["title"] == "Binance Will Delist ABC"
    assert rows[0]["symbol"] == ["ABC"]


def test_load_rows_from_source_file_skips_rows_with_forbidden_payload_keys(tmp_path):
    source = tmp_path / "announcements.jsonl"
    source.write_text(
        json.dumps(
            {
                "title": "Binance Will Delist ABC",
                "time": 1710921600000,
                "symbol": "ABC",
                "url": "https://www.binance.com/en/support/announcement/a",
                "api_key": "must_not_be_silently_stripped",
            }
        )
    )

    rows = load_rows_from_source_file(str(source), source_name="manual_source_file")

    assert rows == []
