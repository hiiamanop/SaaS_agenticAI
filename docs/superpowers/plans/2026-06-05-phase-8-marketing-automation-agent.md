# Phase 8: Marketing Automation Agent Service — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Marketing Automation Agent Service that automates the complete marketing funnel: market intelligence → content creation → ad deployment → lead capture → CRM integration. The service bridges marketing operations with the CRM Service via Kafka events.

**Architecture:** New FastAPI microservice (marketing-service) with 6 specialized autonomous agents integrated via agent-service (LangGraph). Agents work in sequence with HITL checkpoints (Marketing Manager approvals). Data flows to CRM Service via Kafka events.

**Tech Stack:** FastAPI, SQLModel, asyncpg, PostgreSQL (marketing_db), LangGraph agents, Kafka, Baileys WhatsApp API, Ollama/Claude for content generation, pytest + httpx.

---

## Summary of Tasks

**Task 1:** Marketing Service scaffold + 4 database tables + migrations
**Task 2:** Marketing Service API (CRUD campaigns) + 6 tests  
**Task 3:** Extend agent-service with 6 marketing agents + 12 tests
**Task 4:** Marketing → CRM integration (Kafka events) + 3 tests
**Task 5:** Dockerfiles + CI update
**Task 6:** End-to-end marketing funnel smoke test

**Total new tests:** 21 (6 + 12 + 3)
**Total tests Phase 8 end:** 161+ (140 + 21)

---

## Task 1: Marketing Service — Scaffold + Database

**Scope:** Create pyproject.toml, models, alembic migrations, update infra.

**Files to create:**
```
services/marketing-service/
  pyproject.toml
  app/
    __init__.py
    config.py
    database.py
    models.py (Campaign, CompanyTarget, ContentAsset, AdCampaign)
  alembic.ini
  alembic/env.py
  alembic/versions/001_create_marketing_tables.py
```

**Models:**
- Campaign (id, tenant_id, name, industry, target_audience, pain_points, value_proposition, status, created_at)
- CompanyTarget (id, campaign_id, tenant_id, company_name, industry, website, decision_makers, pain_point_match, contact_validation, status)
- ContentAsset (id, campaign_id, tenant_id, asset_type, title, content, metadata, publish_status, engagement_metrics)
- AdCampaign (id, campaign_id, tenant_id, platform, creative_json, targeting_json, daily_budget, metrics, status)

**All tables:** RLS enabled, tenant_id indexed

**Steps:** Create all files, update infra/postgres/init.sql (add marketing_db), run migration, commit

**Expected:** Migration runs successfully, tables created with RLS

---

## Task 2: Marketing Service — API + 6 Tests

**Scope:** TDD — write failing tests, implement CRUD routes, ensure tenant isolation.

**Tests:**
1. test_health (GET /health)
2. test_create_campaign (POST /campaigns/)
3. test_get_campaign (GET /campaigns/{id})
4. test_update_campaign_status (PATCH /campaigns/{id})
5. test_list_campaigns_by_tenant (GET /campaigns/?tenant_id=X)
6. test_campaigns_isolated_by_tenant

**Endpoints:**
- GET /health → 200
- POST /campaigns/ → 201 (create campaign)
- GET /campaigns/{id} → 200
- GET /campaigns/?tenant_id=X → 200 (list, filtered by tenant)
- PATCH /campaigns/{id} → 200 (update status)

**Files to create:**
- app/schemas.py (CampaignCreate, CampaignRead, CampaignUpdate)
- app/dependencies.py (get_current_user from erp-shared)
- app/events.py (Kafka CloudEvents publisher)
- app/routers/health.py
- app/routers/campaigns.py
- app/main.py (FastAPI app, lifespan with start/stop producer)
- tests/conftest.py, test_campaigns.py

**Expected:** 6 tests pass

---

## Task 3: Extend agent-service with Marketing Agents

**Scope:** Implement 6 autonomous agents for marketing workflow + 12 tests.

**Agents:**
1. **CIS Agent** (Company Intelligence Scout)
   - Tools: google_maps, web_scraper, baileys_whatsapp, clearbit_api
   - Output: list[CompanyTarget] with validated WA contacts
   - Tests: discover companies, validate WA, score relevance (3 tests)

2. **Content Planner Agent**
   - Analyze pain_points, create content strategy
   - Output: campaign matrix (blog articles, LinkedIn posts, ad creatives)
   - Tests: strategy generation, HITL approval (2 tests)

3. **Blog Writer Agent**
   - Generate SEO-optimized articles (2000+ words)
   - Tools: plagiarism_checker, yoast_seo_audit
   - Output: blog article + metadata
   - Tests: article generation, plagiarism check (2 tests)

4. **Ads Orchestrator Agent**
   - Create ad creatives + targeting for Meta, Google, LinkedIn
   - Output: ad campaigns with budgets + tracking
   - Tests: ad creation, platform-specific setup (2 tests)

5. **Landing Page Agent**
   - Generate HTML/CSS landing page
   - Output: deployed page + conversion tracking
   - Tests: page generation, form creation (2 tests)

6. **CRM Agent** (extended from existing)
   - Personalize WA messages for contacts
   - Output: lead scoring + message templates
   - Tests: message personalization, lead scoring (1 test)

**Files to create:**
- app/agents/cis_agent.py, content_planner_agent.py, blog_writer_agent.py, ads_orchestrator_agent.py, landing_page_agent.py
- app/tools/google_maps_tool.py, baileys_whatsapp_tool.py, plagiarism_checker_tool.py, seo_audit_tool.py
- tests/test_cis_agent.py, test_content_planner_agent.py, test_blog_writer_agent.py, test_ads_orchestrator_agent.py, test_landing_page_agent.py

**Expected:** 12 tests pass (agent HITL workflows, Kafka event publishing)

---

## Task 4: Marketing → CRM Integration

**Scope:** Connect marketing-service to crm-service via Kafka events.

**Events:**
- `marketing.contact.interested` (contact filled landing page form)
  ↓ (REST API POST)
  → `crm.opportunity.created` (auto-create opportunity in CRM)

**Tests:**
1. test_contact_interested_creates_crm_opportunity
2. test_contact_info_synced_to_crm
3. test_opportunity_scored_from_campaign

**Expected:** 3 tests pass, CRM opportunities created from marketing leads

---

## Task 5: Dockerfiles + CI Update

**Scope:** Containerize marketing-service, add CI job.

**Files:**
- services/marketing-service/Dockerfile (same pattern as Phase 4-7)
- Update .github/workflows/ci.yml (add test-marketing-service job)

**Expected:** Docker image builds, CI job passes

---

## Task 6: End-to-End Marketing Funnel Test

**Scope:** Full workflow from campaign creation to CRM opportunity.

**Flow:**
1. Create campaign in marketing-service (POST /campaigns/)
2. Trigger CIS Agent → discover companies → publish marketing.contacts.discovered
3. Trigger Content Planner Agent → generate strategy → await HITL approval
4. Marketing Manager approves → marketing.campaign.strategy.approved
5. Trigger Blog Writer Agent → write article → publish article
6. Trigger Ads Agent → create ads → deploy campaigns
7. Trigger Landing Page Agent → generate page → deploy
8. Simulate contact interest (POST /campaigns/{id}/landing-page/form)
9. Verify crm.opportunity.created event in Kafka
10. Verify opportunity visible in CRM Service

**Expected:** Full funnel works, event trail complete, opportunity in CRM

---

## Summary

**Phase 8 adds:**
- Marketing Service (FastAPI + marketing_db)
- 4 core entities with RLS
- 6 autonomous agents (CIS, Content Planner, Blog Writer, Ads, Landing Page, CRM)
- Kafka integration (10+ event types)
- CRM sync via events
- 21 new tests
- Full marketing automation workflow

**Go:** Execute Task 1 → Task 2 → ... → Task 6 using subagent-driven-development.
