import pytest

from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
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


