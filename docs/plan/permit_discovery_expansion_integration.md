# Permit Discovery Expansion: Integration with Master Plan

**Date:** January 13, 2026  
**Purpose:** Clarify how the Permit Discovery Expansion Plan fits into the AORO MVP Master Plan

---

## Master Plan Structure

The AORO MVP Master Plan is organized into three main phases:

### Phase 1: Signal Engine (Weeks 1-4)
- **1.1 Permit Scraper Framework** ✅ Complete
  - Build scraper framework
  - Implement first municipal portal scraper
  - Target: Extract 100+ fire permits from 1 municipality
  - **Status:** ✅ Completed (2 municipalities: Mecklenburg, San Antonio)

- **1.2 Regulatory Listener** ✅ Complete
  - Monitor state fire marshal bulletins
  - NFPA code amendment announcements
  - EPA regulatory updates

- **1.3 Data Enrichment Pipeline** ✅ Complete
  - Geocoding service
  - Company matching (Apollo)
  - Decision maker identification (Hunter.io)
  - Regulatory matching

### Phase 2: Agentic Workflow (Weeks 5-8) ✅ Complete
- LangGraph state machine
- Researcher, Communicator, Closer agents
- Human-in-the-loop gates

### Phase 3: MCP Integration (Weeks 9-12) ⏳ Pending
- FastMCP server
- ServiceTitan API integration
- Multi-tenant security

---

## Where Permit Discovery Expansion Fits

### Position: **Phase 1.4: Permit Discovery Expansion**

The Permit Discovery Expansion Plan is a **scaling and optimization enhancement** of Phase 1.1 (Permit Scraper Framework).

### Relationship to Master Plan

```
Master Plan Phase 1.1 (Original Scope)
├── Build scraper framework ✅
├── Implement first scraper ✅
└── Extract 100+ permits from 1 municipality ✅

    ↓ (Enhancement/Expansion)

Permit Discovery Expansion Plan (Phase 1.4)
├── Scale to 50+ municipalities
├── Automated portal discovery
├── Scraper standardization
├── Open data API integration
└── Quality filtering
```

### Integration Points

#### 1. **Extends Phase 1.1: Permit Scraper Framework**
- **Original Goal:** 1 municipality, 100+ permits
- **Expansion Goal:** 50+ municipalities, 1,000+ permits/month
- **Enhancement:** Automated discovery, standardized scrapers, quality filtering

#### 2. **Enhances Phase 1.3: Data Enrichment Pipeline**
- **Original:** Enrich all permits
- **Enhancement:** Pre-filter permits before enrichment (save credits, improve quality)
- **Quality Scoring:** Only enrich permits with applicant names, valid addresses

#### 3. **Supports Phase 2: Agentic Workflow**
- **More Leads:** 50+ cities = 10x more leads for workflow
- **Better Quality:** Pre-filtering = higher qualification scores
- **Scalability:** Can handle increased volume

---

## Revised Master Plan Structure

### Option A: As Sub-Phase 1.4 (Recommended)

```
Phase 1: Signal Engine
├── 1.1 Permit Scraper Framework ✅ Complete
│   ├── Base scraper framework
│   ├── Mecklenburg County scraper
│   └── San Antonio scraper
│
├── 1.2 Regulatory Listener ✅ Complete
│
├── 1.3 Data Enrichment Pipeline ✅ Complete
│
└── 1.4 Permit Discovery Expansion ⏳ New
    ├── Automated portal discovery (Google Custom Search)
    ├── Scraper standardization (Accela, ViewPoint, EnerGov)
    ├── Open data API integration (Socrata, CKAN)
    ├── Quality filtering & pre-enrichment validation
    └── Unified permit ingestion layer
```

**Timeline:** Weeks 13-20 (after Phase 3, or parallel if resources allow)

### Option B: As Post-MVP Enhancement

```
MVP Phases (Weeks 1-12)
├── Phase 1: Signal Engine ✅
├── Phase 2: Agentic Workflow ✅
└── Phase 3: MCP Integration ⏳

Post-MVP Enhancements
└── Permit Discovery Expansion (Weeks 13-20)
    └── Scale from 2 cities to 50+ cities
```

**Timeline:** After MVP completion

### Option C: As Parallel Enhancement

```
Phase 1: Signal Engine
├── 1.1 Permit Scraper Framework ✅
├── 1.2 Regulatory Listener ✅
├── 1.3 Data Enrichment Pipeline ✅
└── 1.4 Permit Discovery Expansion ⏳ (Parallel to Phase 2/3)
```

**Timeline:** Can run in parallel with Phase 2/3 (different team/resources)

---

## Recommended Approach: **Option A (Sub-Phase 1.4)**

### Rationale

1. **Logical Continuity:** Natural extension of Phase 1.1
2. **Dependencies:** Builds on existing scraper framework
3. **Value:** Increases lead volume 10x without changing core architecture
4. **Timing:** Can start after Phase 1.3 complete (which it is)

### Updated Master Plan Timeline

| Phase | Original Timeline | With Expansion |
|-------|-------------------|----------------|
| **Phase 1.1** | Weeks 1-2 | ✅ Complete |
| **Phase 1.2** | Weeks 2-3 | ✅ Complete |
| **Phase 1.3** | Weeks 3-4 | ✅ Complete |
| **Phase 1.4** | - | **Weeks 13-20** (New) |
| **Phase 2** | Weeks 5-8 | ✅ Complete |
| **Phase 3** | Weeks 9-12 | ⏳ Pending |

### Implementation Strategy

#### Option 1: Sequential (After Phase 3)
- Complete Phase 3 first
- Then implement Phase 1.4
- **Pros:** Focus on MVP completion first
- **Cons:** Delays scaling

#### Option 2: Parallel (Recommended)
- Start Phase 1.4 while Phase 3 is in progress
- Different resources/team members
- **Pros:** Faster time to scale, doesn't block Phase 3
- **Cons:** Requires parallel resources

#### Option 3: Incremental
- Implement Phase 1.4 incrementally
- Add 5-10 cities per week
- **Pros:** Lower risk, continuous improvement
- **Cons:** Slower overall progress

---

## Impact on Other Phases

### Phase 2: Agentic Workflow
- **Current:** Processes leads from 2 cities
- **After Expansion:** Processes leads from 50+ cities
- **Impact:** 10x more leads, but workflow already handles this
- **Action:** No changes needed (already scalable)

### Phase 3: MCP Integration
- **Current:** Books appointments from 2-city leads
- **After Expansion:** Books appointments from 50+ city leads
- **Impact:** More booking volume
- **Action:** Ensure ServiceTitan integration can handle volume

### Knowledge Layer
- **Current:** Neo4j/Pinecone support existing workflow
- **After Expansion:** Same knowledge layer, more queries
- **Impact:** Higher query volume
- **Action:** Monitor performance, scale if needed

---

## Success Criteria Alignment

### Master Plan Phase 1.1 (Original)
- ✅ Extract 100+ fire permits from 1 municipality
- ✅ Scraper framework working
- ✅ Scheduled job runner functional

### Phase 1.4 Expansion (New)
- 🎯 50+ municipalities with active permit sources
- 🎯 1,000+ permits/month discovered
- 🎯 70%+ permits with applicant names (quality)
- 🎯 60%+ enrichment efficiency (decision maker emails)
- 🎯 $0/month cost (free methods only)

---

## Dependencies

### Phase 1.4 Depends On:
- ✅ Phase 1.1: Scraper framework (complete)
- ✅ Phase 1.3: Enrichment pipeline (complete)
- ✅ Base infrastructure (complete)

### Phase 1.4 Enables:
- 🚀 10x lead volume for Phase 2
- 🚀 Better data quality for Phase 2
- 🚀 Scalable foundation for production

---

## Recommendation

**Implement Phase 1.4 as a sub-phase of Phase 1, starting after Phase 1.3 completion.**

### Timeline Suggestion:
- **Start:** After Phase 1.3 (already complete)
- **Duration:** 8 weeks (as per expansion plan)
- **Parallel with:** Phase 3 (MCP Integration) if resources allow
- **Priority:** High (enables 10x scaling)

### Implementation Order:
1. **Week 1-2:** Portal discovery (Phase 1.4.1)
2. **Week 3-4:** Scraper standardization (Phase 1.4.2)
3. **Week 5-6:** Open data APIs (Phase 1.4.3)
4. **Week 7:** Quality filtering (Phase 1.4.4)
5. **Week 8:** Integration & automation (Phase 1.4.5)

---

## Conclusion

The **Permit Discovery Expansion Plan** is a natural extension of **Phase 1.1: Permit Scraper Framework** and should be implemented as **Phase 1.4** in the master plan.

**Key Points:**
- ✅ Builds on existing Phase 1.1 infrastructure
- ✅ Enhances Phase 1.3 enrichment efficiency
- ✅ Supports Phase 2 workflow with 10x more leads
- ✅ Can run in parallel with Phase 3
- ✅ Zero cost (free methods only)
- ✅ High value (10x scaling)

**Next Step:** Begin Phase 1.4 implementation after confirming resource allocation and timeline.

---

**Document Version:** 1.0  
**Last Updated:** January 13, 2026
