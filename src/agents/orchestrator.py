from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from src.agents.nodes.book_meeting import book_meeting_node
from src.agents.nodes.closer import closer_node
from src.agents.nodes.communicator import communicator_node
from src.agents.nodes.followup import followup_node
from src.agents.nodes.handle_response import handle_response_node
from src.agents.nodes.human_review import human_review_node
from src.agents.nodes.researcher import researcher_node
from src.agents.nodes.update_crm import update_crm_node
from src.agents.nodes.wait_response import wait_response_node
from src.agents.state import AOROState
from src.core.config import get_settings
from src.core.observability import audit_event

logger = logging.getLogger(__name__)


async def lead_ingestion_node(state: AOROState) -> AOROState:
    # Normalize minimal required fields into state.
    permit = state.get("permit_data") or {}
    company_name = state.get("company_name") or permit.get("applicant_name") or "Unknown"
    return {
        **state,
        "company_name": company_name,
        "outreach_channel": state.get("outreach_channel", "email"),
        "response_history": state.get("response_history", []),
    }


async def qualification_check_node(state: AOROState) -> AOROState:
    """
    Enhanced qualification scoring with additional factors.
    
    Scoring factors:
    - Base score: 0.2
    - Status is good (issued/approved/active/completed): +0.3
    - Status indicates progress (inspection/passed): +0.2
    - Permit is fire-related (type or source): +0.2
    - Has decision maker: +0.1
    - Compliance urgency (from Researcher): +0.15 (weighted)
    - Building type risk (high-risk types): +0.1
    - Permit recency (issued within 30 days): +0.05
    """
    from datetime import datetime, timedelta
    
    from src.signal_engine.scrapers.status_normalizer import is_good_status, is_progress_status
    
    permit = state.get("permit_data") or {}
    status = permit.get("status")  # Status should already be normalized by scraper
    ptype = str(permit.get("permit_type") or "").lower()
    source = str(permit.get("source") or "").lower()
    building_type = str(permit.get("building_type") or "").lower()
    issued_date_str = permit.get("issued_date")
    
    score = 0.2  # Base score
    
    # Factor 1: Good status (+0.3)
    # Use status normalizer to check if status is good
    if is_good_status(status):
        score += 0.3
    
    # Factor 2: Progress status (+0.2)
    # Use status normalizer to check if status indicates progress
    if is_progress_status(status):
        score += 0.2
    
    # Factor 3: Fire-related permit (+0.2)
    # Check both permit_type AND source field (like quality filter does)
    is_fire_related = False
    
    # Check permit type for fire keywords
    fire_keywords = ["fire", "sprinkler", "alarm", "suppression", "detection", "extinguishing"]
    if any(keyword in ptype for keyword in fire_keywords):
        is_fire_related = True
    
    # Also check source field for fire module (e.g., "accela_cosa_fire")
    if "fire" in source:
        is_fire_related = True
    
    # Check for MEP (Mechanical, Electrical, Plumbing) - often includes fire systems
    if "mep" in ptype.lower():
        # Give partial credit for MEP permits (they often include fire systems)
        score += 0.1
        is_fire_related = True  # Count as fire-related for full credit
    
    if is_fire_related:
        score += 0.2
    
    # Factor 4: Has decision maker (+0.1)
    decision_maker = state.get("decision_maker")
    if decision_maker and (decision_maker.get("email") or decision_maker.get("full_name")):
        score += 0.1
    
    # Factor 5: Compliance urgency from Researcher node (+0.15 weighted)
    # This is calculated by the Researcher node based on permit status, type, codes, gaps
    compliance_urgency = state.get("compliance_urgency_score", 0.0)
    if compliance_urgency > 0:
        # Weight the urgency score (0.0-1.0) by 0.15
        score += compliance_urgency * 0.15
    
    # Factor 6: Building type risk (+0.1)
    # High-risk building types need more urgent attention
    high_risk_building_types = ["hospital", "data_center", "data center", "school", "nursing", "care", "assisted living", "skilled nursing"]
    if any(risk_type in building_type for risk_type in high_risk_building_types):
        score += 0.1
    
    # Factor 7: Permit recency (+0.05)
    # Recently issued permits are more time-sensitive
    if issued_date_str:
        try:
            # Handle both datetime objects and ISO strings
            if isinstance(issued_date_str, datetime):
                issued_date = issued_date_str
            else:
                issued_date = datetime.fromisoformat(issued_date_str.replace("Z", "+00:00"))
            
            # Check if issued within last 30 days
            days_old = (datetime.now() - issued_date.replace(tzinfo=None)).days
            if days_old <= 30:
                score += 0.05
        except Exception:
            # If date parsing fails, skip this factor
            pass
    
    # Cap at 1.0
    score = min(score, 1.0)
    
    return {**state, "qualification_score": score}


async def send_outreach_node(state: AOROState) -> AOROState:
    """
    Send outreach via the configured channel.
    
    For email: Uses EmailSender to send via configured provider
    For WhatsApp/Voice: Placeholder (Phase 2.2+)
    """
    from datetime import datetime

    from src.agents.infrastructure.email_sender import EmailSender
    from src.agents.monitoring import append_workflow_event
    from src.agents.storage.workflow_storage import WorkflowStorage
    from src.core.config import get_settings

    channel = state.get("outreach_channel", "email")
    draft = state.get("outreach_draft", "")
    decision_maker = state.get("decision_maker") or {}
    lead_id = state.get("lead_id", "")

    history = list(state.get("response_history") or [])

    if channel == "email":
        # Extract email and name from decision maker
        to_email = decision_maker.get("email") or decision_maker.get("email_address")
        to_name = decision_maker.get("full_name") or decision_maker.get("name")

        if not to_email:
            logger.warning(f"No email address found for lead {lead_id}, skipping send")
            history.append(
                {
                    "type": "outreach_failed",
                    "channel": channel,
                    "reason": "no_email_address",
                }
            )
            return {**state, "response_history": history}

        # Extract subject from draft (first line) and body (rest)
        lines = draft.split("\n")
        subject = lines[0].replace("Subject:", "").strip() if lines else "Fire Safety Compliance Consultation"
        if lead_id and f"[AORO-{lead_id}]" not in subject:
            subject = f"{subject} [AORO-{lead_id}]"
        body = "\n".join(lines[1:]) if len(lines) > 1 else draft

        # Send email
        email_sender = EmailSender()
        send_result = await email_sender.send_outreach_email(
            lead_id=lead_id,
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            body=body,
        )

        if send_result.get("status") == "sent":
            # Save outreach to storage
            storage = WorkflowStorage()
            storage.save_outreach(
                lead_id,
                {
                    "channel": channel,
                    "subject": subject,
                    "body": body,
                    "to_email": to_email,
                    "to_name": to_name,
                    "sent_at": datetime.now().isoformat(),
                    "email_id": send_result.get("email_id"),
                },
            )
            append_workflow_event(
                "outreach_sent",
                {
                    "lead_id": lead_id,
                    "channel": channel,
                    "email_id": send_result.get("email_id"),
                    "to_email": to_email,
                },
            )

            history.append(
                {
                    "type": "outreach_sent",
                    "channel": channel,
                    "sent_at": datetime.now().isoformat(),
                    "email_id": send_result.get("email_id"),
                }
            )
            audit_event(
                "outreach_sent",
                {
                    "lead_id": lead_id,
                    "channel": channel,
                    "email_id": send_result.get("email_id"),
                },
            )
        else:
            history.append(
                {
                    "type": "outreach_failed",
                    "channel": channel,
                    "error": send_result.get("error"),
                }
            )
            logger.error(f"Failed to send email for lead {lead_id}: {send_result.get('error')}")
    else:
        # WhatsApp/Voice: Placeholder for Phase 2.2+
        history.append(
            {
                "type": "outreach_ready",
                "channel": channel,
                "draft": draft,
                "note": "Channel not yet implemented",
            }
        )
        logger.info(f"Outreach ready for {channel} (not yet implemented)")

    updated_state = {
        **state,
        "response_history": history,
        "outreach_sent_at": datetime.now().isoformat() if channel == "email" and send_result.get("status") == "sent" else None,
    }

    settings = get_settings()
    if settings.workflow_persistence_enabled and channel == "email" and send_result.get("status") == "sent":
        storage = WorkflowStorage()
        storage.save_workflow_state(lead_id, updated_state)

    return updated_state


def build_graph():
    graph = StateGraph(AOROState)

    # Phase 2.1 nodes
    graph.add_node("LeadIngestion", lead_ingestion_node)
    graph.add_node("Research", researcher_node)
    graph.add_node("QualificationCheck", qualification_check_node)
    graph.add_node("DraftOutreach", communicator_node)
    graph.add_node("HumanReview", human_review_node)
    graph.add_node("SendOutreach", send_outreach_node)
    
    # Phase 2.2 nodes
    graph.add_node("WaitForResponse", wait_response_node)
    graph.add_node("HandleResponse", handle_response_node)
    
    # Phase 2.3 nodes
    graph.add_node("FollowUp", followup_node)
    graph.add_node("ObjectionHandling", closer_node)
    graph.add_node("BookMeeting", book_meeting_node)
    graph.add_node("UpdateCRM", update_crm_node)

    # Phase 2.1 flow
    graph.add_edge(START, "LeadIngestion")
    graph.add_edge("LeadIngestion", "Research")
    graph.add_edge("Research", "QualificationCheck")

    def route_after_qualification(state: AOROState) -> str:
        if float(state.get("qualification_score") or 0.0) < 0.5:
            return END
        return "DraftOutreach"

    graph.add_conditional_edges("QualificationCheck", route_after_qualification)
    graph.add_edge("DraftOutreach", "HumanReview")

    def route_after_review(state: AOROState) -> str:
        if state.get("human_approved") is True:
            return "SendOutreach"
        return END

    graph.add_conditional_edges("HumanReview", route_after_review)
    
    # Phase 2.2: After sending outreach, wait for response
    graph.add_edge("SendOutreach", "WaitForResponse")
    
    def route_after_wait(state: AOROState) -> str:
        """Route after waiting for response."""
        if state.get("response_received") is True:
            return "HandleResponse"
        elif state.get("response_timeout") is True:
            # Timeout - route to FollowUp
            return "FollowUp"
        else:
            # Still waiting - for MVP, end workflow
            # In production with checkpointer, would interrupt and resume
            return END

    graph.add_conditional_edges("WaitForResponse", route_after_wait)
    
    def route_after_response(state: AOROState) -> str:
        """Route after handling response."""
        classification = state.get("response_classification")
        
        if classification == "positive":
            return "BookMeeting"
        elif classification == "objection":
            return "ObjectionHandling"
        elif classification == "no_response":
            return "FollowUp"
        elif classification == "unsubscribe":
            # Unsubscribe - end workflow
            return END
        else:
            return END

    graph.add_conditional_edges("HandleResponse", route_after_response)
    
    # Phase 2.3: FollowUp routing
    def route_after_followup(state: AOROState) -> str:
        """Route after follow-up."""
        workflow_complete = state.get("workflow_complete", False)
        
        if workflow_complete:
            # Max attempts reached - end workflow
            return END
        else:
            # Follow-up scheduled - send it and wait for response
            return "SendOutreach"  # Send follow-up, then wait again
    
    graph.add_conditional_edges("FollowUp", route_after_followup)
    
    # Phase 2.3: Objection handling routing
    def route_after_objection(state: AOROState) -> str:
        """Route after objection handling."""
        settings = get_settings()
        objection_count = state.get("objection_handling_count", 0)
        max_cycles = getattr(settings, "max_objection_handling_cycles", 3)
        
        if objection_count >= max_cycles:
            # Max objection handling cycles reached - end workflow
            logger.warning(f"Max objection handling cycles ({max_cycles}) reached")
            return END
        else:
            # Route back to DraftOutreach with revised message
            return "DraftOutreach"
    
    graph.add_conditional_edges("ObjectionHandling", route_after_objection)
    
    # Phase 2.3: BookMeeting routes to UpdateCRM
    graph.add_edge("BookMeeting", "UpdateCRM")
    
    # Phase 2.3: UpdateCRM ends workflow
    graph.add_edge("UpdateCRM", END)

    return graph.compile()


