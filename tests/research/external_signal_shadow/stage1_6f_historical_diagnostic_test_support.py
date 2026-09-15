"""Test support utilities for Stage 1.6F historical mechanism diagnostic tests."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import src.research.external_signal_shadow.stage1_6a_sealed_export_adapter as adapter
import src.research.external_signal_shadow.stage1_6a_sealed_export_adapter_storage as adapter_storage
from tests.research.external_signal_shadow.stage1_6a_sealed_export_adapter_test_support import (
    build_valid_historical_sealed_export,
    trusted_article,
)


def build_30_trusted_articles() -> List[Dict[str, Any]]:
    """Build 32 distinct trusted articles across 12 days to pass sample sufficiency (>=30 events, >=10 days, >=3 symbols)."""
    articles = []
    for i in range(32):
        symbol = f"TOK{i:02d}USDT"
        p_date = 1700000000000 + (i % 12) * 86_400_000 + i * 1000
        title = f"Binance Will Delist {symbol} (2026-08-20)"
        body_nodes = [
            {"node": "element", "tag": "p", "child": [{"node": "text", "text": "Fellow Binancians,"}]},
            {
                "node": "element",
                "tag": "p",
                "child": [
                    {
                        "node": "text",
                        "text": f"Binance Futures will delist the USDⓈ-M {symbol} Perpetual Contract at 2026-08-25 09:00 (UTC).",
                    }
                ],
            },
        ]
        articles.append(
            trusted_article(
                article_id=f"art_{i+1:028d}",
                title=title,
                publish_date=p_date,
                body_nodes=body_nodes,
            )
        )
    return articles


def build_valid_completed_c_root(
    tmp_path: Path,
    *,
    run_id: str = "run_c_positive_001",
    article_specs: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Path, Path, Path]:
    """
    Build a positive completed C audit root exclusively through canonical upstream APIs:
    build_valid_historical_sealed_export -> load_verified_source_snapshot -> reduce_verified_snapshot -> persist_adapter_audit.
    Does NOT handcraft completion manifest, summary, or JSONLs.
    Returns (project_root, completed_root, source_export).
    """
    if article_specs is None:
        article_specs = build_30_trusted_articles()

    project_root, source_export = build_valid_historical_sealed_export(
        tmp_path,
        article_specs=article_specs,
        run_id=f"hist_{run_id}",
    )
    snapshot = adapter.load_verified_source_snapshot(project_root, source_export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot,
        semantic_extracted_at_ms=1700000050000,
        grammar_pair=adapter.G2_GRAMMAR_PAIR,
    )

    out_root = (
        project_root
        / "data"
        / "external_signal_shadow"
        / "stage1_6a"
        / "sealed_export_source_audits"
        / run_id
    )
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    return project_root, out_root, source_export


def build_insufficient_completed_c_root(
    tmp_path: Path,
    *,
    run_id: str = "run_c_insufficient_001",
) -> Tuple[Path, Path, Path]:
    """Build a completed C audit with only 1 article, so sample_sufficiency_passed is False and source_audit_passed is False."""
    article_specs = [trusted_article()]
    return build_valid_completed_c_root(
        tmp_path,
        run_id=run_id,
        article_specs=article_specs,
    )


def copy_market_evidence_package(target_dir: Path) -> Path:
    """
    Copies tests/fixtures/external_signal_shadow/stage1_6f/evidence_package to target_dir.
    Derived strictly from repo-relative path, no hardcoded machine absolute path.
    """
    import shutil

    src_dir = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "external_signal_shadow"
        / "stage1_6f"
        / "evidence_package"
    )
    assert src_dir.is_dir(), f"Evidence package directory not found: {src_dir}"
    dest_dir = target_dir / "evidence_package"
    shutil.copytree(src_dir, dest_dir)
    return dest_dir

