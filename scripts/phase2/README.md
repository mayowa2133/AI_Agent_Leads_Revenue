# Phase 2: Agentic Workflow Tests

Tests for the multi-agent LangGraph workflow.

## Phase 2.1: Core Workflow & Outreach Generation

### Prerequisites

Before testing Phase 2.1, ensure:

1. **Phase 1.3 Complete**: You have enriched leads from Phase 1.3
   ```bash
   # If you don't have enriched leads, create some first:
   poetry run python scripts/phase1_3/test_enrichment_pipeline.py
   ```

2. **Email Configuration**: Configure email provider in `.env`
   ```bash
   # Option 1: SMTP (simplest, for testing)
   EMAIL_PROVIDER=smtp
   SMTP_HOST=localhost
   SMTP_PORT=587
   
   # Option 2: SendGrid (recommended for production)
   EMAIL_PROVIDER=sendgrid
   SENDGRID_API_KEY=your_sendgrid_key
   
   # Option 3: AWS SES
   EMAIL_PROVIDER=ses
   AWS_SES_REGION=us-east-1
   ```

3. **OpenAI API Key**: Required for LLM-based outreach generation
   ```bash
   OPENAI_API_KEY=your_openai_key
   ```

4. **Neo4j & Pinecone**: Required for Researcher agent
   - Neo4j: Fire code graph queries
   - Pinecone: Case study search

### Test Scripts

#### 1. Full Workflow Test (Recommended)

Tests the complete Phase 2.1 workflow with real enriched leads:

```bash
poetry run python scripts/phase2/test_phase2_1_workflow.py
```

**What it tests:**
- ✅ Loads enriched leads from Phase 1.3
- ✅ Runs complete workflow: LeadIngestion → Research → Qualification → Draft → Review → Send
- ✅ Validates Researcher node (Neo4j queries, Pinecone search, urgency scoring)
- ✅ Validates Communicator node (outreach generation)
- ✅ Validates Human Review node (auto-approval logic)
- ✅ Validates Email Sender (sends email via configured provider)
- ✅ Validates workflow state persistence

**Expected Output:**
- Qualification score
- Compliance urgency score
- Applicable codes found
- Compliance gaps identified
- Case studies retrieved
- Outreach draft generated
- Email sent (if email configured)

#### 2. Component Validation Test

Validates individual components without sending emails:

```bash
poetry run python scripts/phase2/test_phase2_1_components.py
```

**What it tests:**
- ✅ Workflow storage (save/load state)
- ✅ Researcher node (urgency scoring)
- ✅ Communicator node (multi-channel support)
- ✅ Email sender initialization
- ✅ Workflow graph construction

### Testing Scenarios

#### Scenario 1: High-Quality Lead (Should Qualify)

**Test Lead:**
- Permit: Fire Alarm, Status: "Issued"
- Building Type: Commercial
- Decision Maker: Has email
- Company: Has domain

**Expected:**
- Qualification Score: ≥ 0.5
- Compliance Urgency: ≥ 0.4
- Human Approved: True (if score ≥ 0.8)
- Email Sent: Yes

#### Scenario 2: Low-Quality Lead (Should Disqualify)

**Test Lead:**
- Permit: Generic, Status: "Pending"
- Building Type: Unknown
- Decision Maker: No email
- Company: No domain

**Expected:**
- Qualification Score: < 0.5
- Workflow Ends: At QualificationCheck
- Email Sent: No

#### Scenario 3: Medium-Quality Lead (Needs Review)

**Test Lead:**
- Permit: Fire Alarm, Status: "Issued"
- Building Type: Commercial
- Decision Maker: Has email
- Qualification Score: 0.6-0.79

**Expected:**
- Qualification Score: 0.5-0.79
- Human Approved: False (triggers interrupt)
- Workflow Pauses: At HumanReview
- Email Sent: No (until approved)

### Manual Testing Steps

1. **Test with Real Enriched Lead:**
   ```bash
   # Ensure you have enriched leads
   poetry run python scripts/phase1_3/test_enrichment_pipeline.py
   
   # Run Phase 2.1 workflow
   poetry run python scripts/phase2/test_phase2_1_workflow.py
   ```

2. **Verify Workflow State Storage:**
   ```bash
   # Check that workflow states are saved
   cat data/workflow_states.json
   
   # Check that outreach messages are tracked
   cat data/workflow_outreachs.json
   ```

3. **Test Email Sending (Dry Run):**
   ```bash
   # For SMTP, use a local mail server or mailtrap
   # For SendGrid, use a test API key
   # Check email service dashboard for sent emails
   ```

4. **Test Multi-Channel Support:**
   ```python
   # Modify test to use different channels
   initial_state["outreach_channel"] = "whatsapp"  # or "voice"
   ```

### Troubleshooting

#### Issue: "No enriched leads found"
**Solution:** Run Phase 1.3 enrichment first:
```bash
poetry run python scripts/phase1_3/test_enrichment_pipeline.py
```

#### Issue: "Email sending failed"
**Solution:** Check email configuration:
- Verify `EMAIL_PROVIDER` in `.env`
- For SMTP: Ensure mail server is running
- For SendGrid: Verify API key
- For SES: Verify AWS credentials

#### Issue: "Neo4j connection failed"
**Solution:** Ensure Neo4j is running:
```bash
docker compose up -d neo4j
```

#### Issue: "Pinecone connection failed"
**Solution:** Verify Pinecone configuration:
- Check `PINECONE_API_KEY` in `.env`
- Verify `PINECONE_INDEX` exists

#### Issue: "OpenAI API error"
**Solution:** Verify OpenAI API key:
- Check `OPENAI_API_KEY` in `.env`
- Verify API key is valid and has credits

### Success Criteria

Phase 2.1 is fully operational when:

- ✅ Workflow processes enriched leads successfully
- ✅ Researcher node queries Neo4j and Pinecone
- ✅ Compliance urgency score is calculated
- ✅ Communicator generates outreach drafts
- ✅ Human review gates work (auto-approve high confidence)
- ✅ Email sending works (or fails gracefully if not configured)
- ✅ Workflow state is persisted
- ✅ Outreach messages are tracked

## Phase 2.2: Response Handling & Classification

### Prerequisites

Before testing Phase 2.2, ensure:

1. **Phase 2.1 Complete**: Core workflow and outreach generation working
2. **OpenAI API Key**: Required for response classification
   ```bash
   OPENAI_API_KEY=your_openai_key
   ```

### Test Scripts

#### 1. Response Handling Test (Recommended)

Tests the complete Phase 2.2 response handling flow:

```bash
poetry run python scripts/phase2/test_phase2_2_response_handling.py
```

**What it tests:**
- ✅ Response storage (save/retrieve)
- ✅ WaitForResponse node (response received, timeout, still waiting)
- ✅ HandleResponse node (positive, objection, empty responses)
- ✅ Webhook integration (simulated)
- ✅ End-to-end response flow

**Expected Output:**
- Response saved to storage
- Response detected by WaitForResponse
- Response classified (positive/objection/no_response)
- Sentiment and interest level extracted
- Objections extracted (if applicable)

### Testing Scenarios

#### Scenario 1: Positive Response

**Test Response:**
```
"Yes, I'd like to schedule a consultation. When are you available?"
```

**Expected:**
- Classification: `positive`
- Sentiment: `positive`
- Interest Level: `high`
- Route: BookMeeting (Phase 2.3)

#### Scenario 2: Objection Response

**Test Response:**
```
"We already have a vendor for fire safety. Thanks but no thanks."
```

**Expected:**
- Classification: `objection`
- Sentiment: `negative`
- Interest Level: `none`
- Extracted Objections: `["Already have a vendor for fire safety"]`
- Route: ObjectionHandling

#### Scenario 3: No Response / Empty

**Test Response:**
```
""
```

**Expected:**
- Classification: `no_response`
- Sentiment: `neutral`
- Route: FollowUp (Phase 2.3)

### Webhook Testing

#### Test Webhook Endpoint

```bash
# Start the API server
poetry run uvicorn src.api.main:app --reload

# Send test webhook
curl -X POST http://localhost:8000/webhooks/email-response \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": "test-lead-001",
    "from_email": "customer@example.com",
    "to_email": "noreply@aoro.ai",
    "subject": "Re: Fire Safety Consultation",
    "content": "I am interested!",
    "received_at": "2026-01-07T12:00:00Z",
    "source": "email"
  }'
```

**Expected Response:**
```json
{
  "ok": true,
  "lead_id": "test-lead-001",
  "message": "Response saved"
}
```

### Manual Testing Steps

1. **Test Response Storage:**
   ```bash
   # Run test script
   poetry run python scripts/phase2/test_phase2_2_response_handling.py
   
   # Check that responses are saved
   cat data/workflow_responses.json
   ```

2. **Test Webhook Handler:**
   ```bash
   # Start API server
   poetry run uvicorn src.api.main:app --reload
   
   # Send test webhook (see above)
   ```

3. **Test End-to-End Flow:**
   ```bash
   # 1. Send outreach (Phase 2.1)
   poetry run python scripts/phase2/test_phase2_1_workflow.py
   
   # 2. Simulate response via webhook
   curl -X POST http://localhost:8000/webhooks/email-response ...
   
   # 3. Run workflow again to process response
   poetry run python scripts/phase2/test_phase2_1_workflow.py
   ```

### Troubleshooting

#### Issue: "Response classification failed"
**Solution:** Check OpenAI API key:
- Verify `OPENAI_API_KEY` in `.env`
- Verify API key is valid and has credits

#### Issue: "Webhook not saving response"
**Solution:** Check webhook payload:
- Ensure `lead_id` is provided
- Verify response content is not empty
- Check API server logs for errors

#### Issue: "WaitForResponse not detecting response"
**Solution:** Check response storage:
- Verify response was saved with correct `lead_id`
- Check `received_at` timestamp is after `outreach_sent_at`
- Verify `data/workflow_responses.json` contains the response

### Success Criteria

Phase 2.2 is fully operational when:

- ✅ Responses are saved to storage via webhook
- ✅ WaitForResponse detects responses correctly
- ✅ WaitForResponse detects timeouts correctly
- ✅ HandleResponse classifies responses accurately
- ✅ Response sentiment and interest level are extracted
- ✅ Objections are extracted from responses
- ✅ Workflow routes correctly based on classification

### Next Steps

After Phase 2.2 is verified:
- Proceed to Phase 2.3: Follow-ups & Objection Management
- Implement automated follow-up sequences
- Enhance objection handling
- Implement meeting booking
