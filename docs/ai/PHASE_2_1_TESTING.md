# Phase 2.1 Testing Guide

## Quick Start

### 1. Component Validation (No Email Sending)

Test all components without sending emails:

```bash
poetry run python scripts/phase2/test_phase2_1_components.py
```

**What it validates:**
- ✅ Workflow storage (save/load state)
- ✅ Compliance urgency scoring
- ✅ Multi-channel communicator (email, WhatsApp, voice)
- ✅ Email sender initialization
- ✅ Workflow graph construction

**Time:** ~30 seconds  
**Requirements:** OpenAI API key, Neo4j, Pinecone

### 2. Full Workflow Test (With Email Sending)

Test complete workflow with real enriched leads:

```bash
poetry run python scripts/phase2/test_phase2_1_workflow.py
```

**What it tests:**
- ✅ Complete workflow: LeadIngestion → Research → Qualification → Draft → Review → Send
- ✅ Researcher node (Neo4j queries, Pinecone search, urgency scoring)
- ✅ Communicator node (outreach generation)
- ✅ Human review (auto-approval)
- ✅ Email sending (if configured)

**Time:** ~1-2 minutes  
**Requirements:** 
- Enriched leads from Phase 1.3
- OpenAI API key
- Neo4j & Pinecone
- Email provider configured (optional - will fail gracefully if not configured)

## Prerequisites Checklist

Before testing, ensure:

- [ ] **Phase 1.3 Complete**: Have enriched leads
  ```bash
  # If needed, create enriched leads:
  poetry run python scripts/phase1_3/test_enrichment_pipeline.py
  ```

- [ ] **OpenAI API Key**: Required for LLM
  ```bash
  # In .env:
  OPENAI_API_KEY=your_key_here
  ```

- [ ] **Neo4j Running**: For fire code queries
  ```bash
  docker compose up -d neo4j
  ```

- [ ] **Pinecone Configured**: For case study search
  ```bash
  # In .env:
  PINECONE_API_KEY=your_key_here
  PINECONE_INDEX=aoro-case-studies
  ```

- [ ] **Email Provider** (Optional): For actual email sending
  ```bash
  # Option 1: SMTP (simplest)
  EMAIL_PROVIDER=smtp
  SMTP_HOST=localhost
  
  # Option 2: SendGrid (recommended)
  EMAIL_PROVIDER=sendgrid
  SENDGRID_API_KEY=your_key
  # Note: Install sendgrid: pip install sendgrid
  
  # Option 3: AWS SES
  EMAIL_PROVIDER=ses
  AWS_SES_REGION=us-east-1
  # Note: Install boto3: pip install boto3
  ```

## Expected Test Results

### Component Test Output

```
============================================================
Testing Workflow Storage
============================================================
✓ Saved workflow state
✓ Loaded workflow state
  Lead ID: test-storage-001
  Score: 0.75
✓ Saved outreach
✓ Saved response

============================================================
Testing Compliance Urgency Scoring
============================================================
High urgency case: 0.85
✓ High urgency scoring works
Low urgency case: 0.15
✓ Low urgency scoring works

============================================================
Testing Multi-Channel Communicator
============================================================
✓ Email outreach generated
  Length: 245 chars
✓ WhatsApp outreach generated
  Length: 128 chars
✓ Voice script generated
  Length: 312 chars

============================================================
Test Summary
============================================================
✅ PASS: Workflow Storage
✅ PASS: Compliance Urgency Scoring
✅ PASS: Multi-Channel Communicator
✅ PASS: Email Sender Initialization
✅ PASS: Workflow Graph Construction

Results: 5/5 tests passed
✅ All Phase 2.1 components validated!
```

### Full Workflow Test Output

```
============================================================
Testing Phase 2.1: Core Workflow & Outreach Generation
============================================================
Testing with lead: test-lead-001
  Company: Test Company
  Decision Maker: John Doe
  Permit: Fire Alarm - Issued

============================================================
Running workflow...
============================================================

============================================================
Workflow completed!
============================================================

Qualification Score: 0.70
Compliance Urgency: 0.65
Human Approved: True
Applicable Codes: 2
Compliance Gaps: 2
Case Studies: 3

------------------------------------------------------------
Outreach Draft:
------------------------------------------------------------
Subject: Fire Safety Compliance Consultation for Test Company

Dear John Doe,

Your facility at 123 Test St is subject to NFPA 72 requirements...

[Full email draft]

------------------------------------------------------------
Response History:
------------------------------------------------------------
  - outreach_sent: email
    Email ID: abc123xyz

✅ Phase 2.1 workflow test completed successfully!
```

## Troubleshooting

### "No enriched leads found"
**Solution:** Run Phase 1.3 enrichment:
```bash
poetry run python scripts/phase1_3/test_enrichment_pipeline.py
```

### "Email sending failed"
**Solution:** 
- For SMTP: Use a local mail server or mailtrap.io
- For SendGrid: Install package: `pip install sendgrid`
- For SES: Install package: `pip install boto3`
- Or skip email sending (workflow will still work, just won't send)

### "Neo4j connection failed"
**Solution:** Start Neo4j:
```bash
docker compose up -d neo4j
```

### "OpenAI API error"
**Solution:** Check your API key and credits in `.env`

## Success Criteria

Phase 2.1 is **fully operational** when:

- ✅ Component test passes (5/5 tests)
- ✅ Full workflow test completes successfully
- ✅ Researcher queries Neo4j and Pinecone
- ✅ Compliance urgency score is calculated (0.0-1.0)
- ✅ Communicator generates outreach for all channels
- ✅ Human review auto-approves high-confidence leads
- ✅ Workflow state is persisted to `data/workflow_states.json`
- ✅ Outreach is tracked in `data/workflow_outreachs.json`
- ✅ Email sending works (or fails gracefully if not configured)

## Next Steps

After Phase 2.1 is verified:
- ✅ Proceed to Phase 2.2: Response Handling & Classification
- ✅ Test with real email responses
- ✅ Implement response webhooks
