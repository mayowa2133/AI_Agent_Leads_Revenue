from __future__ import annotations

import copy
import time
from datetime import datetime, timedelta
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agents.nodes.human_review import human_review_node
from src.agents.state import AOROState
from src.core.config import get_settings

DEFAULT_DEMO_LEADS: list[dict[str, Any]] = [
    {
        "lead_id": "demo-lead-001",
        "company_name": "Atlas Medical Center",
        "decision_maker": {
            "full_name": "Renee Walker",
            "email": "renee.walker@atlasmed.com",
            "title": "Facilities Director",
        },
        "permit_data": {
            "permit_id": "FIRE-ATX-1021",
            "permit_type": "Fire Alarm Installation",
            "status": "Issued",
            "building_type": "Hospital",
            "address": "1000 Health Ave, Austin, TX",
        },
        "outreach_channel": "email",
    },
    {
        "lead_id": "demo-lead-002",
        "company_name": "Westgate Logistics",
        "decision_maker": {
            "full_name": "Andre Johnson",
            "email": "andre@westgatelogistics.com",
            "title": "Operations Manager",
        },
        "permit_data": {
            "permit_id": "FIRE-HOU-4459",
            "permit_type": "Fire Sprinkler Modification",
            "status": "Inspection Scheduled",
            "building_type": "Warehouse",
            "address": "4800 Commerce Blvd, Houston, TX",
        },
        "outreach_channel": "email",
    },
    {
        "lead_id": "demo-lead-003",
        "company_name": "Ridgeview Apartments",
        "decision_maker": {
            "full_name": "Sabrina Lee",
            "email": "sabrina@ridgeviewliving.com",
            "title": "Property Manager",
        },
        "permit_data": {
            "permit_id": "FIRE-SAT-3307",
            "permit_type": "Fire Suppression System",
            "status": "Pending",
            "building_type": "Residential",
            "address": "2200 Ridgeview Dr, San Antonio, TX",
        },
        "outreach_channel": "email",
    },
]


def get_demo_leads() -> list[dict[str, Any]]:
    return copy.deepcopy(DEFAULT_DEMO_LEADS)


def _serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    def _serialize(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: _serialize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_serialize(v) for v in value]
        return value

    return {k: _serialize(v) for k, v in dict(state).items()}


def _diff_state(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    for key in sorted(set(before.keys()) | set(after.keys())):
        if before.get(key) != after.get(key):
            changes[key] = {"before": before.get(key), "after": after.get(key)}
    return changes


class DemoTracker:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def wrap(self, node_name: str, fn):
        async def wrapped(state: AOROState) -> AOROState:
            start = time.time()
            before = _serialize_state(state)
            result = await fn(state)
            after = _serialize_state(result)
            duration_ms = int((time.time() - start) * 1000)
            event = {
                "node": node_name,
                "timestamp": datetime.now().isoformat(),
                "duration_ms": duration_ms,
                "changes": _diff_state(before, after),
            }
            self.events.append(event)
            return result

        return wrapped


async def _lead_ingestion_node(state: AOROState) -> AOROState:
    permit = state.get("permit_data") or {}
    company_name = state.get("company_name") or permit.get("applicant_name") or "Unknown"
    return {
        **state,
        "company_name": company_name,
        "outreach_channel": state.get("outreach_channel", "email"),
        "response_history": state.get("response_history", []),
    }


async def _qualification_check_node(state: AOROState) -> AOROState:
    from datetime import datetime

    from src.signal_engine.scrapers.status_normalizer import is_good_status, is_progress_status

    permit = state.get("permit_data") or {}
    status = permit.get("status")
    ptype = str(permit.get("permit_type") or "").lower()
    source = str(permit.get("source") or "").lower()
    building_type = str(permit.get("building_type") or "").lower()
    issued_date_str = permit.get("issued_date")

    score = 0.2

    if is_good_status(status):
        score += 0.3
    if is_progress_status(status):
        score += 0.2

    is_fire_related = False
    fire_keywords = ["fire", "sprinkler", "alarm", "suppression", "detection", "extinguishing"]
    if any(keyword in ptype for keyword in fire_keywords):
        is_fire_related = True
    if "fire" in source:
        is_fire_related = True
    if "mep" in ptype.lower():
        score += 0.1
        is_fire_related = True
    if is_fire_related:
        score += 0.2

    decision_maker = state.get("decision_maker")
    if decision_maker and (decision_maker.get("email") or decision_maker.get("full_name")):
        score += 0.1

    compliance_urgency = state.get("compliance_urgency_score", 0.0)
    if compliance_urgency > 0:
        score += compliance_urgency * 0.15

    high_risk_building_types = [
        "hospital",
        "data_center",
        "data center",
        "school",
        "nursing",
        "care",
        "assisted living",
        "skilled nursing",
    ]
    if any(risk_type in building_type for risk_type in high_risk_building_types):
        score += 0.1

    if issued_date_str:
        try:
            if isinstance(issued_date_str, datetime):
                issued_date = issued_date_str
            else:
                issued_date = datetime.fromisoformat(str(issued_date_str).replace("Z", "+00:00"))
            days_old = (datetime.now() - issued_date.replace(tzinfo=None)).days
            if days_old <= 30:
                score += 0.05
        except Exception:
            pass

    score = min(score, 1.0)
    return {**state, "qualification_score": score}


async def _demo_researcher_node(state: AOROState) -> AOROState:
    permit = state.get("permit_data") or {}
    ptype = str(permit.get("permit_type") or "").lower()
    status = str(permit.get("status") or "").lower()

    applicable = ["NFPA 72", "NFPA 25"]
    compliance_gaps = []
    if "alarm" in ptype:
        compliance_gaps.append("Alarm device testing and documentation likely required before inspection.")
    if "inspection" in status:
        compliance_gaps.append("Inspection scheduled indicates near-term readiness gap.")

    case_studies = [
        {"title": "Hospital AHJ pass rate improved", "summary": "Reduced inspection failures by 32% in 60 days."},
        {"title": "Warehouse retrofit compliance", "summary": "Completed retrofit ahead of deadline."},
    ]

    urgency = 0.6 if "inspection" in status else 0.4
    return {
        **state,
        "applicable_codes": applicable,
        "compliance_gaps": compliance_gaps,
        "case_studies": case_studies,
        "compliance_urgency_score": urgency,
    }


async def _demo_communicator_node(state: AOROState) -> AOROState:
    permit = state.get("permit_data") or {}
    company = state.get("company_name") or "your facility"
    subject = "Subject: Fire Safety Compliance Consultation"
    body = (
        f"Hi {company},\n\n"
        f"I noticed your {permit.get('permit_type')} permit ({permit.get('status')}). "
        "We help facilities align with NFPA codes and reduce inspection risk. "
        "Would you be open to a 15-minute call this week?\n\n"
        "Best,\nAORO"
    )
    return {**state, "outreach_draft": f"{subject}\n{body}"}


async def _demo_send_outreach_node(state: AOROState) -> AOROState:
    history = list(state.get("response_history") or [])
    history.append({"type": "outreach_sent", "channel": state.get("outreach_channel", "email")})
    return {
        **state,
        "response_history": history,
        "outreach_sent_at": datetime.now().isoformat(),
    }


async def _demo_wait_response_node(state: AOROState) -> AOROState:
    response_data = state.get("response_data")
    return {
        **state,
        "response_received": True,
        "response_timeout": False,
        "waiting_for_response": False,
        "response_data": response_data,
    }


async def _demo_handle_response_node(state: AOROState) -> AOROState:
    response_type = state.get("demo_response_type") or "positive"
    response_text = (state.get("response_data") or {}).get("content", "")
    if not response_text:
        response_type = "no_response"
    sentiment = "positive" if response_type == "positive" else "negative" if response_type == "objection" else "neutral"
    interest = "high" if response_type == "positive" else "low" if response_type == "objection" else "none"
    objections = []
    if response_type == "objection":
        objections = ["Already have a vendor"] if response_text else ["Budget timing"]
    return {
        **state,
        "response_classification": response_type,
        "response_sentiment": sentiment,
        "interest_level": interest,
        "extracted_objections": objections,
        "current_objection": objections[0] if objections else None,
    }


async def _demo_followup_node(state: AOROState) -> AOROState:
    settings = get_settings()
    followup_count = state.get("followup_count", 0)
    max_followups = getattr(settings, "max_followup_attempts", 2)

    if followup_count >= max_followups:
        return {
            **state,
            "workflow_complete": True,
            "workflow_status": "no_response",
            "followup_count": followup_count,
        }

    next_count = followup_count + 1
    scheduled_at = datetime.now() + timedelta(days=3 * next_count)
    followup_draft = f"Subject: Re: Fire Safety Compliance Consultation\n\nJust following up on our note."
    return {
        **state,
        "followup_count": next_count,
        "outreach_draft": followup_draft,
        "followup_scheduled_at": scheduled_at.isoformat(),
    }


async def _demo_closer_node(state: AOROState) -> AOROState:
    objection_count = state.get("objection_handling_count", 0) + 1
    objection = state.get("current_objection") or "Already have a vendor"
    reply = "Totally fair. We can complement your current vendor with compliance audits."
    history = list(state.get("response_history") or [])
    history.append({"type": "objection_reply", "objection": objection, "reply": reply})
    return {
        **state,
        "response_history": history,
        "outreach_draft": f"Subject: Re: Fire Safety Compliance Consultation\n\n{reply}",
        "objection_handling_count": objection_count,
        "current_objection": objection,
    }


async def _demo_book_meeting_node(state: AOROState) -> AOROState:
    decision_maker = state.get("decision_maker") or {}
    permit_data = state.get("permit_data") or {}
    meeting_preferences = {
        "preferred_times": ["morning"],
        "preferred_dates": ["next week"],
        "meeting_format": "video",
        "timezone": "America/Chicago",
        "constraints": [],
        "urgency": "medium",
    }
    booking_payload = {
        "lead_id": state.get("lead_id"),
        "company_name": state.get("company_name"),
        "decision_maker": {
            "full_name": decision_maker.get("full_name"),
            "email": decision_maker.get("email"),
        },
        "permit_data": {
            "permit_id": permit_data.get("permit_id"),
            "permit_type": permit_data.get("permit_type"),
            "address": permit_data.get("address"),
            "status": permit_data.get("status"),
        },
        "meeting_preferences": meeting_preferences,
        "meeting_type": "consultation",
        "source": "demo_simulator",
        "notes": "Demo simulator booking payload",
    }
    return {
        **state,
        "booking_payload": booking_payload,
        "booking_ready": True,
        "meeting_preferences": meeting_preferences,
    }


def _select_nodes(live_services: bool) -> dict[str, Any]:
    from src.agents.nodes.update_crm import update_crm_node

    if live_services:
        from src.agents.nodes.book_meeting import book_meeting_node
        from src.agents.nodes.closer import closer_node
        from src.agents.nodes.communicator import communicator_node
        from src.agents.nodes.followup import followup_node
        from src.agents.nodes.handle_response import handle_response_node
        from src.agents.nodes.researcher import researcher_node
        from src.agents.nodes.update_crm import update_crm_node
        from src.agents.nodes.wait_response import wait_response_node
        from src.agents.orchestrator import send_outreach_node

        return {
            "Research": researcher_node,
            "DraftOutreach": communicator_node,
            "HumanReview": human_review_node,
            "SendOutreach": send_outreach_node,
            "WaitForResponse": wait_response_node,
            "HandleResponse": handle_response_node,
            "FollowUp": followup_node,
            "ObjectionHandling": closer_node,
            "BookMeeting": book_meeting_node,
            "UpdateCRM": update_crm_node,
        }
    return {
        "Research": _demo_researcher_node,
        "DraftOutreach": _demo_communicator_node,
        "HumanReview": human_review_node,
        "SendOutreach": _demo_send_outreach_node,
        "WaitForResponse": _demo_wait_response_node,
        "HandleResponse": _demo_handle_response_node,
        "FollowUp": _demo_followup_node,
        "ObjectionHandling": _demo_closer_node,
        "BookMeeting": _demo_book_meeting_node,
        "UpdateCRM": update_crm_node,
    }


def build_demo_graph(tracker: DemoTracker, *, live_services: bool = False):
    nodes = _select_nodes(live_services)
    graph = StateGraph(AOROState)

    graph.add_node("LeadIngestion", tracker.wrap("LeadIngestion", _lead_ingestion_node))
    graph.add_node("Research", tracker.wrap("Research", nodes["Research"]))
    graph.add_node("QualificationCheck", tracker.wrap("QualificationCheck", _qualification_check_node))
    graph.add_node("DraftOutreach", tracker.wrap("DraftOutreach", nodes["DraftOutreach"]))
    graph.add_node("HumanReview", tracker.wrap("HumanReview", nodes["HumanReview"]))
    graph.add_node("SendOutreach", tracker.wrap("SendOutreach", nodes["SendOutreach"]))
    graph.add_node("WaitForResponse", tracker.wrap("WaitForResponse", nodes["WaitForResponse"]))
    graph.add_node("HandleResponse", tracker.wrap("HandleResponse", nodes["HandleResponse"]))
    graph.add_node("FollowUp", tracker.wrap("FollowUp", nodes["FollowUp"]))
    graph.add_node("ObjectionHandling", tracker.wrap("ObjectionHandling", nodes["ObjectionHandling"]))
    graph.add_node("BookMeeting", tracker.wrap("BookMeeting", nodes["BookMeeting"]))
    graph.add_node("UpdateCRM", tracker.wrap("UpdateCRM", nodes["UpdateCRM"]))

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
    graph.add_edge("SendOutreach", "WaitForResponse")

    def route_after_wait(state: AOROState) -> str:
        if state.get("response_received") is True:
            return "HandleResponse"
        if state.get("response_timeout") is True:
            return "FollowUp"
        return END

    graph.add_conditional_edges("WaitForResponse", route_after_wait)

    def route_after_response(state: AOROState) -> str:
        classification = state.get("response_classification")
        if classification == "positive":
            return "BookMeeting"
        if classification == "objection":
            return "ObjectionHandling"
        if classification == "no_response":
            return "FollowUp"
        return END

    graph.add_conditional_edges("HandleResponse", route_after_response)

    def route_after_followup(state: AOROState) -> str:
        if state.get("workflow_complete", False):
            return END
        return "SendOutreach"

    graph.add_conditional_edges("FollowUp", route_after_followup)

    def route_after_objection(state: AOROState) -> str:
        settings = get_settings()
        objection_count = state.get("objection_handling_count", 0)
        max_cycles = getattr(settings, "max_objection_handling_cycles", 3)
        if objection_count >= max_cycles:
            return END
        return "DraftOutreach"

    graph.add_conditional_edges("ObjectionHandling", route_after_objection)
    graph.add_edge("BookMeeting", "UpdateCRM")
    graph.add_edge("UpdateCRM", END)

    return graph.compile()


async def run_demo(lead_state: dict[str, Any], *, live_services: bool = False) -> dict[str, Any]:
    tracker = DemoTracker()
    graph = build_demo_graph(tracker, live_services=live_services)
    result = await graph.ainvoke(lead_state)
    return {"timeline": tracker.events, "state": _serialize_state(result)}


async def run_demo_response(
    state: dict[str, Any],
    *,
    response_type: str,
    response_content: str,
    live_services: bool = False,
) -> dict[str, Any]:
    tracker = DemoTracker()
    nodes = _select_nodes(live_services)

    working_state = {
        **state,
        "response_data": {
            "content": response_content,
            "received_at": datetime.now().isoformat(),
            "source": "demo",
        },
        "response_received": True,
        "response_timeout": False,
        "waiting_for_response": False,
        "demo_response_type": response_type,
    }

    wait_node = tracker.wrap("WaitForResponse", _demo_wait_response_node)
    handle_node = tracker.wrap("HandleResponse", nodes["HandleResponse"])
    followup_node = tracker.wrap("FollowUp", nodes["FollowUp"])
    objection_node = tracker.wrap("ObjectionHandling", nodes["ObjectionHandling"])
    draft_node = tracker.wrap("DraftOutreach", nodes["DraftOutreach"])
    review_node = tracker.wrap("HumanReview", nodes["HumanReview"])
    send_node = tracker.wrap("SendOutreach", nodes["SendOutreach"])
    book_node = tracker.wrap("BookMeeting", nodes["BookMeeting"])
    update_node = tracker.wrap("UpdateCRM", nodes["UpdateCRM"])

    state_after_wait = await wait_node(working_state)
    state_after_handle = await handle_node(state_after_wait)
    classification = state_after_handle.get("response_classification")

    if classification == "positive":
        state_after_book = await book_node(state_after_handle)
        final_state = await update_node(state_after_book)
        return {"timeline": tracker.events, "state": _serialize_state(final_state)}

    if classification == "objection":
        state_after_obj = await objection_node(state_after_handle)
        settings = get_settings()
        objection_count = state_after_obj.get("objection_handling_count", 0)
        max_cycles = getattr(settings, "max_objection_handling_cycles", 3)
        if objection_count >= max_cycles:
            return {"timeline": tracker.events, "state": _serialize_state(state_after_obj)}
        state_after_draft = await draft_node(state_after_obj)
        state_after_review = await review_node(state_after_draft)
        if state_after_review.get("human_approved") is True:
            state_after_send = await send_node(state_after_review)
            final_state = await wait_node(state_after_send)
            return {"timeline": tracker.events, "state": _serialize_state(final_state)}
        return {"timeline": tracker.events, "state": _serialize_state(state_after_review)}

    if classification == "no_response":
        state_after_followup = await followup_node(state_after_handle)
        if state_after_followup.get("workflow_complete", False):
            return {"timeline": tracker.events, "state": _serialize_state(state_after_followup)}
        state_after_send = await send_node(state_after_followup)
        final_state = await wait_node(state_after_send)
        return {"timeline": tracker.events, "state": _serialize_state(final_state)}

    return {"timeline": tracker.events, "state": _serialize_state(state_after_handle)}
