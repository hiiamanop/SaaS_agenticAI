ROLE
Act as a Principal Enterprise Architect, Staff Software Engineer, SaaS Platform Architect, AI Systems Architect, and CTO-level Technical Reviewer.
Your responsibility is to deeply analyze, review, challenge, improve, and help design this product as if you are preparing it for real-world production deployment serving thousands of enterprise customers.
Do not simply agree with my design.
Actively identify:
* architectural weaknesses
* scalability bottlenecks
* security risks
* operational risks
* AI governance concerns
* multi-tenant challenges
* cost inefficiencies
* technical debt risks
When appropriate, propose better alternatives and explain tradeoffs.

PRODUCT VISION
We are building a next-generation Autonomous AI-Powered Enterprise ERP SaaS Platform.
The goal is not to build a traditional ERP.
The goal is to build an Autonomous Enterprise Operating System capable of:
* managing business operations
* proactively identifying business opportunities
* autonomously generating recommendations
* orchestrating workflows
* coordinating AI agents across departments
* maintaining strict Human-in-the-Loop governance
The platform must be:
* cloud-native
* multi-tenant
* horizontally scalable
* event-driven
* AI-first
* enterprise-grade
* Kubernetes-ready
* highly observable
* secure-by-design

ARCHITECTURAL PRINCIPLES
The system follows these core principles:
1. Microservices Architecture
Business domains must be fully decoupled.
1. Event-Driven Architecture
Services communicate asynchronously through Kafka.
Avoid direct service-to-service coupling whenever possible.
1. Horizontal Scalability
All services must be stateless and scalable using Kubernetes HPA.
1. Database per Service
Every service owns its own database.
1. Human-in-the-Loop Governance
AI can reason, recommend, plan, and automate.
Critical business actions require approval.
1. Multi-Tenant SaaS
All services must be tenant-aware.
1. Enterprise Security
RBAC, SSO, auditability, tenant isolation, and compliance.
1. Autonomous Multi-Agent System
AI agents collaborate across business domains.
1. AI Cost Efficiency
Semantic caching and optimized inference routing.
1. High Availability
No single point of failure.

TARGET AUTONOMY LEVEL
The platform should target:
Level 3:Autonomous Planning + HITL
Level 4:Autonomous Execution + HITL
Future Vision:Level 5 Autonomous Enterprise Operations

SYSTEM ARCHITECTURE
=================================================LAYER 1CLIENT INTERFACE LAYER
Components:
* React Enterprise ERP Dashboard
* Mobile ERP Application
* WhatsApp Business Channel
* LinkedIn Prospecting Extension
* Landing Page AI Knowledge Assistant
Users:
* Owner
* CEO
* Sales
* Marketing
* Procurement
* Finance
* Accounting
* Operations
* Administrators

=================================================LAYER 2IDENTITY, SSO & SECURITY PLATFORM
Components:
* External Load Balancer
* API Gateway
* Identity Service
* Authentication Service
* Authorization Service
* RBAC Service
* SSO Service
* Tenant Management Service
* Subscription Management Service
* Feature Flag Service
SSO REQUIREMENTS:
Support:
* Local Login
* Google OAuth
* Microsoft Azure AD
* OpenID Connect
* SAML 2.0
ERP LAUNCHPAD
After login users enter an ERP Launchpad.
The launchpad acts like:
* SAP Fiori
* Microsoft 365
* Google Workspace
Users only see modules enabled by:
* Tenant Subscription
* User Role
* Feature Flags
Examples:
Starter Plan:
* CRM
* Sales
Business Plan:
* CRM
* Sales
* Inventory
* Procurement
Enterprise Plan:
* CRM
* Sales
* Inventory
* Procurement
* Accounting
* AI Platform
* Knowledge Platform
Tenant admins can enable or disable modules based on subscription plans.
All module access is controlled centrally.

=================================================LAYER 3CORE BUSINESS PLATFORM
Kubernetes Deployment
Each service deployed as:
x3 Pods minimum
Components:
CRM Service
Responsibilities:
* Leads
* Contacts
* Opportunities
* Customer Lifecycle
Sales Service
Responsibilities:
* Quotations
* Sales Orders
* Revenue Tracking
Inventory Service
Responsibilities:
* Stock
* Warehouses
* Transfers
* Demand Forecasting
Procurement Service
Responsibilities:
* Purchase Requests
* Purchase Orders
* Vendor Management
Accounting Service
Responsibilities:
* Journal Entries
* Invoices
* Payments
* Financial Statements
Approval Center
Responsibilities:
* Human-in-the-Loop approvals
* Enterprise workflow approvals
* Risk-based authorization
Notification Service
Responsibilities:
* Email
* WhatsApp
* Push Notifications

=================================================LAYER 4EVENT & WORKFLOW PLATFORM
Apache Kafka
Acts as the central nervous system.
All services publish events.
Examples:
sales.order.created
sales.order.approved
inventory.low_stock
procurement.request.created
invoice.generated
payment.completed
Services subscribe to relevant events.
Additional Components:
Workflow Engine
Approval Engine
Audit Service
Event Replay
Dead Letter Queue
Observability Layer
Requirements:
* Event sourcing friendly
* Replay capability
* Retry handling
* Failure recovery

=================================================LAYER 5AUTONOMOUS MULTI-AGENT PLATFORM
The system must support collaborative enterprise AI agents.
Components:
Agent Orchestrator
Agent Registry
Agent Communication Layer
Agent Workflow Runtime
Agent State Store
Agent Memory Store
Human Approval Gateway
Agent Event Integration
Agents communicate through:
* Kafka
* Agent Messaging Layer
* Shared Context Memory
Avoid hard-coded dependencies.

AGENTS
CRM Agent
Responsibilities:
* lead qualification
* customer segmentation
* churn prediction
* engagement recommendations
Sales Agent
Responsibilities:
* quotation generation
* sales forecasting
* pipeline analysis
* pricing recommendations
Inventory Agent
Responsibilities:
* stock optimization
* shortage prediction
* transfer recommendations
Procurement Agent
Responsibilities:
* supplier selection
* purchase recommendations
* procurement planning
Accounting Agent
Responsibilities:
* anomaly detection
* reconciliation
* cashflow forecasting
Knowledge Agent
Responsibilities:
* enterprise search
* SOP retrieval
* policy reasoning
Executive Copilot Agent
Responsibilities:
* business intelligence
* strategic recommendations
* executive summaries

MULTI-AGENT EXAMPLE
Inventory Agent
detects low stock
↓
Procurement Agent
finds suppliers
↓
Accounting Agent
validates budget
↓
Executive Copilot
creates recommendation
↓
Approval Center
↓
Manager Approval
↓
Purchase Order Created

=================================================LAYER 6AI PLATFORM
Components:
AI Orchestrator (x3 Pods)
Prompt Registry
Tool Registry
Memory Store
Semantic Cache
Inference Router
Model Gateway
Redis Cache
Ollama Cluster
OpenAI Compatibility Layer
Requirements:
* tool calling
* structured outputs
* reasoning workflows
* semantic caching
* model routing
The AI platform must be tenant-aware.
Each request includes:
* tenant id
* subscription plan
* AI quota
* model permissions

=================================================LAYER 7KNOWLEDGE PLATFORM
This is independent from business services.
Components:
Document Ingestion Service
Document Parser
Chunking Service
Embedding Service
Knowledge API
Hybrid Search
Reranking Service
Vector Database
Semantic Search Engine
Knowledge Sources:
* SOP
* Internal Policies
* Product Documentation
* Training Materials
* FAQ
* Public Knowledge
Vector Database:
Qdrant preferred.
Requirements:
* horizontal scalability
* metadata filtering
* tenant isolation
IMPORTANT SECURITY RULE:
Knowledge Platform must never directly access ERP transactional databases.
Knowledge retrieval must be isolated.

=================================================DATA LAYER
Database per service.
PostgreSQL:
* Auth DB
* Tenant DB
* Subscription DB
* CRM DB
* Sales DB
* Inventory DB
* Procurement DB
* Accounting DB
* Approval DB
* Audit DB
Redis:
* Semantic Cache
* Session Cache
Qdrant:
* Knowledge Embeddings

=================================================DEPLOYMENT TARGET
Infrastructure:
* Kubernetes
* Horizontal Pod Autoscaler
* Ingress Nginx
* Kafka Cluster
* Redis Cluster
* PostgreSQL HA
* Qdrant Cluster
Requirements:
* Multi AZ
* Auto Scaling
* Zero Downtime Deployments
* Observability
* Disaster Recovery

WHAT I WANT FROM YOU
Review the entire architecture.
Then provide:
1. Architectural Review
2. Design Flaws
3. Scalability Risks
4. Security Risks
5. Multi-Tenant Risks
6. AI Governance Risks
7. Cost Optimization Recommendations
8. Suggested Improvements
9. Missing Components
10. Recommended Tech Stack
11. Service Boundaries
12. Event Contracts
13. Database Design Suggestions
14. Agent Architecture Suggestions
15. Kubernetes Deployment Recommendations
16. Production Readiness Assessment
17. Architecture Score (1-10)
18. C4 Architecture Design
19. Implementation Roadmap (MVP → Enterprise Scale)

Challenge assumptions where necessary and prioritize production-grade enterprise architecture decisions.
