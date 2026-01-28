"""Show detailed outreach information including drafts and sent emails."""

from __future__ import annotations

import json
from pathlib import Path

from src.agents.storage.workflow_storage import WorkflowStorage


def show_outreach_details():
    """Show all outreach drafts and sent emails."""
    print("=" * 80)
    print("OUTREACH DETAILS")
    print("=" * 80)
    print()
    
    storage = WorkflowStorage()
    
    # Load all workflow states to find outreach drafts
    states = storage.load_all_states()
    
    # Load all sent outreachs
    sent_outreachs = storage.load_all_outreachs()
    
    print("📧 SENT OUTREACH EMAILS")
    print("-" * 80)
    if not sent_outreachs:
        print("   No emails have been sent yet.")
    else:
        for lead_id, outreach_list in sent_outreachs.items():
            print(f"\n   Lead ID: {lead_id}")
            for outreach in outreach_list:
                print(f"   ──────────────────────────────────────────────────────────────")
                print(f"   Channel: {outreach.get('channel', 'N/A')}")
                print(f"   Sent At: {outreach.get('sent_at', 'N/A')}")
                print(f"   To: {outreach.get('to_name', 'N/A')} <{outreach.get('to_email', 'N/A')}>")
                print(f"   Subject: {outreach.get('subject', 'N/A')}")
                print(f"   Email ID: {outreach.get('email_id', 'N/A')}")
                print(f"   Full Email Body:")
                print(f"   ──────────────────────────────────────────────────────────────")
                body = outreach.get('body', '')
                for line in body.split('\n'):
                    print(f"      {line}")
                print(f"   ──────────────────────────────────────────────────────────────")
    
    print()
    print("📝 OUTREACH DRAFTS (Not Yet Sent)")
    print("-" * 80)
    
    drafts_found = False
    for lead_id, state_dict in states.items():
        outreach_draft = state_dict.get("outreach_draft")
        qualification_score = state_dict.get("qualification_score", 0.0)
        human_approved = state_dict.get("human_approved")
        workflow_status = state_dict.get("workflow_status")
        
        if outreach_draft:
            drafts_found = True
            print(f"\n   Lead ID: {lead_id}")
            print(f"   ──────────────────────────────────────────────────────────────")
            print(f"   Qualification Score: {qualification_score:.2f}")
            print(f"   Human Approved: {human_approved}")
            print(f"   Workflow Status: {workflow_status}")
            print(f"   Draft Status: {'✅ Generated' if outreach_draft else '❌ Not generated'}")
            
            if outreach_draft:
                print(f"   Full Draft Content:")
                print(f"   ──────────────────────────────────────────────────────────────")
                for line in outreach_draft.split('\n'):
                    print(f"      {line}")
                print(f"   ──────────────────────────────────────────────────────────────")
                print()
                
                # Check if it was sent
                if lead_id in sent_outreachs:
                    print(f"   ✅ This draft was SENT as an email")
                else:
                    print(f"   ⚠️  This draft was NOT sent (likely failed human review)")
                    if qualification_score < 0.8:
                        print(f"      Reason: Score {qualification_score:.2f} < 0.8 (requires human approval)")
    
    if not drafts_found:
        print("   No outreach drafts found in workflow states.")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_drafts = sum(1 for s in states.values() if s.get("outreach_draft"))
    total_sent = sum(len(outreachs) for outreachs in sent_outreachs.values())
    
    print(f"   Total Drafts Generated: {total_drafts}")
    print(f"   Total Emails Sent: {total_sent}")
    print(f"   Sent Rate: {(total_sent/total_drafts*100) if total_drafts > 0 else 0:.1f}%")
    print()


if __name__ == "__main__":
    show_outreach_details()
