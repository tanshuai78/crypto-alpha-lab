"""
tests/research/external_signal_shadow/test_stage1_4a2_vendor_models.py
"""
import pytest

from research.external_signal_shadow.stage1_4a2_vendor import (
    VendorLiquidationAudit,
    load_vendor_audits_json,
)
from tests.research.external_signal_shadow.stage1_4a2_vendor_fixtures import (
    base_vendor_audit_payload,
)


def test_vendor_audit_model_accepts_complete_payload() -> None:
    audit = VendorLiquidationAudit.from_dict(base_vendor_audit_payload())
    assert audit.vendor == "tardis_dev"
    assert audit.evidence_level == "trial_export"


@pytest.mark.parametrize("bad_level", ["marketing", "docs", ""])
def test_vendor_audit_model_rejects_unknown_evidence_level(bad_level: str) -> None:
    payload = base_vendor_audit_payload()
    payload["evidence_level"] = bad_level
    with pytest.raises(ValueError, match="evidence_level"):
        VendorLiquidationAudit.from_dict(payload)


def test_vendor_audit_model_requires_license_split_fields() -> None:
    payload = base_vendor_audit_payload()
    del payload["license_allows_backtesting"]
    with pytest.raises(ValueError, match="license_allows_backtesting"):
        VendorLiquidationAudit.from_dict(payload)


def test_vendor_audit_model_rejects_unknown_source_surface() -> None:
    payload = base_vendor_audit_payload()
    payload["source_surface"] = "unknown_surface"
    with pytest.raises(ValueError, match="source_surface"):
        VendorLiquidationAudit.from_dict(payload)


def test_vendor_audit_model_requires_evidence_urls_and_date() -> None:
    payload = base_vendor_audit_payload()
    payload["evidence_urls"] = []
    with pytest.raises(ValueError, match="evidence_urls"):
        VendorLiquidationAudit.from_dict(payload)


def test_load_vendor_audits_json_supports_list_root(tmp_path) -> None:
    import json

    path = tmp_path / "audits.json"
    path.write_text(json.dumps([base_vendor_audit_payload()]), encoding="utf-8")
    audits = load_vendor_audits_json(path)
    assert len(audits) == 1
