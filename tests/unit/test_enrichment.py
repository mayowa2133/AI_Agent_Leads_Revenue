import pytest

from scripts.e2e.test_ckan_enrichment import should_stop_for_email_target
from src.signal_engine.enrichment.company_enricher import (
    EnrichmentInputs,
    _is_email_domain_sane,
    enrich_permit_to_lead,
)
from src.signal_engine.enrichment.hunter_client import (
    HunterDomainSearchResult,
    HunterEmailRecord,
)
from src.signal_engine.enrichment.provider_manager import ProviderManager
from src.signal_engine.models import PermitData


@pytest.mark.asyncio
async def test_enrich_permit_to_lead_minimal():
    permit = PermitData(
        source="test",
        permit_id="P-123",
        permit_type="Fire Alarm",
        address="123 Main St",
        building_type="Hospital",
        status="Permit Issued",
        applicant_name="Acme Fire Systems",
    )
    lead = await enrich_permit_to_lead(EnrichmentInputs(tenant_id="demo", permit=permit))
    assert lead.tenant_id == "demo"
    assert lead.company.name == "Acme Fire Systems"
    assert lead.permit.permit_id == "P-123"


def test_email_domain_sanity_filter():
    assert _is_email_domain_sane(
        email="owner@acmefire.com",
        company_domain="acmefire.com",
        company_name="Acme Fire Systems",
    )
    assert not _is_email_domain_sane(
        email="owner@gmail.com",
        company_domain="acmefire.com",
        company_name="Acme Fire Systems",
    )
    assert not _is_email_domain_sane(
        email="owner@school.edu",
        company_domain="acmefire.com",
        company_name="Acme Fire Systems",
    )
    assert _is_email_domain_sane(
        email="ceo@acmefs.com",
        company_domain=None,
        company_name="Acme Fire Systems",
    )
    assert not _is_email_domain_sane(
        email="director@district.k12.tx.us",
        company_domain=None,
        company_name="Acme Fire Systems",
        blocked_tlds={"edu"},
    )
    assert not _is_email_domain_sane(
        email="owner@local.org",
        company_domain=None,
        company_name="Acme Fire Systems",
        blocked_tlds={"org"},
    )
    assert not _is_email_domain_sane(
        email="owner@local.io",
        company_domain=None,
        company_name="Acme Fire Systems",
        allowed_tlds_no_domain={"com", "net"},
    )
    assert not _is_email_domain_sane(
        email="owner@spammy.biz",
        company_domain=None,
        company_name="Acme Fire Systems",
        blocked_domains={"spammy.biz"},
    )


@pytest.mark.asyncio
async def test_hunter_domain_search_fallback_selects_best_contact(monkeypatch):
    async def fake_domain_search(_domain: str):
        return HunterDomainSearchResult(
            pattern="{first}.{last}",
            emails=[
                HunterEmailRecord(
                    email="info@example.com",
                    first_name="Info",
                    last_name="Inbox",
                    position="Info",
                    confidence=80,
                ),
                HunterEmailRecord(
                    email="ceo@example.com",
                    first_name="Alex",
                    last_name="Leader",
                    position="CEO",
                    confidence=70,
                ),
            ],
        )

    manager = ProviderManager(hunter_api_key="test", dry_run=True)
    monkeypatch.setattr(manager, "_get_domain_search_result", fake_domain_search)
    decision_maker = await manager.find_any_contact_email_via_domain_search(
        company_domain="example.com"
    )
    assert decision_maker is not None
    assert decision_maker.email == "ceo@example.com"


def test_should_stop_for_email_target():
    results = [
        {"email": "a@example.com"},
        {"email": None},
        {"email": "b@example.com"},
    ]
    assert should_stop_for_email_target(results, 2)
    assert not should_stop_for_email_target(results, 3)

