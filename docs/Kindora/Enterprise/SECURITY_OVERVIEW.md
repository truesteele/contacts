# Kindora — Enterprise Security Overview

**Last Updated:** March 2026
**Version:** 1.0

*This document provides an overview of Kindora's security practices for enterprise customers and their procurement teams. It is provided for informational purposes only and does not form part of any contractual agreement unless expressly incorporated by reference in an Order Form.*

---

## Company Information

| | |
|---|---|
| **Company** | Kindora, PBC |
| **Legal Structure** | Delaware Public Benefit Corporation |
| **Founded** | 2025 |
| **Headquarters** | Oakland, California |
| **Public Benefit** | To democratize philanthropic giving to under-resourced nonprofits |

---

## Infrastructure & Hosting

| Area | Details |
|------|---------|
| **Cloud Provider** | Vercel (frontend), Supabase (database + auth) |
| **Data Center Locations** | United States (AWS us-east-1 / us-west-2) |
| **Database** | PostgreSQL (Supabase-managed), with automated backups |
| **CDN** | Vercel Edge Network (global) |
| **Uptime Target** | 99.5% monthly |

---

## Data Security

### What data we store
- **Organization profile data:** Name, mission, programs, NTEE codes, geographic focus
- **User account data:** Name, email, role, authentication credentials (hashed)
- **Funder research data:** Search queries, saved funders, pipeline status, Intel Briefs
- **Grant application drafts:** User-generated content created within the platform
- **Usage analytics:** Aggregate feature usage for product improvement

### What data we do NOT store
- Social security numbers or government IDs
- Bank account or financial information (payments processed by Stripe)
- Donor personal information or gift amounts
- Physical documents or file uploads beyond platform-generated content

### Encryption
| Layer | Standard |
|-------|----------|
| **In transit** | TLS 1.2+ (HTTPS enforced on all endpoints) |
| **At rest** | AES-256 (Supabase-managed PostgreSQL encryption) |
| **Backups** | Encrypted at rest with provider-managed keys |

### Access Controls
- Role-based access control (RBAC) within each organization workspace
- Multi-tenant isolation: each organization's data is logically separated
- Enterprise sponsor dashboards show aggregate metrics only — no access to individual org data
- Authentication via email/password with bcrypt hashing, or OAuth (Google)
- Session management with secure, HTTP-only cookies

---

## Enterprise Data Isolation

For Enterprise Network Plans, data isolation is a core architectural commitment:

| What the sponsor CAN see | What the sponsor CANNOT see |
|--------------------------|----------------------------|
| Total codes redeemed | Individual org names |
| Number of active orgs | Org-specific funder searches |
| Aggregate briefs generated | Pipeline or grant applications |
| Aggregate credits used | Strategic plans or saved funders |
| Aggregate adoption health metrics | Intel Brief content |

No organization-identifying information is visible to the sponsor unless the affected organization provides separate written opt-in consent. This isolation is enforced at the application layer and is not configurable by the sponsor.

---

## Application Security

| Practice | Status |
|----------|--------|
| **Dependency scanning** | Automated via GitHub Dependabot |
| **Code review** | All changes reviewed before merge |
| **Secret management** | Environment variables; no secrets in code |
| **Input validation** | Server-side validation on all API endpoints |
| **SQL injection prevention** | Parameterized queries via Supabase client |
| **XSS prevention** | React auto-escaping; Content Security Policy headers |
| **CSRF protection** | SameSite cookies; token-based API authentication |

---

## Payment Security

- All payment processing handled by **Stripe** (PCI DSS Level 1 certified)
- Kindora does not store credit card numbers, CVVs, or bank account details
- Enterprise invoices processed via ACH or check; no card data handled by Kindora

---

## Compliance & Privacy

| Area | Status |
|------|--------|
| **Privacy Policy** | Published at kindora.co/privacy |
| **CCPA/CPRA** | Compliant; California consumer rights honored |
| **GDPR** | Data Processing Addendum available upon request |
| **SOC 2** | Planned (not yet completed) |
| **Data retention** | Customer data retained during active subscription; deleted within 30 days of termination upon request |
| **Data export** | Available upon request within 30 days of termination |
| **Sub-processors** | List available upon request |

---

## Incident Response

| Procedure | Commitment |
|-----------|------------|
| **Detection** | Automated monitoring and alerting |
| **Notification** | Customer notified within 72 hours of confirmed data breach |
| **Response** | Containment, investigation, remediation, and post-incident review |
| **Contact** | security@kindora.co |

---

## Business Continuity

| Area | Approach |
|------|----------|
| **Database backups** | Automated daily backups with point-in-time recovery (Supabase-managed) |
| **Disaster recovery** | Multi-region failover capability via cloud providers |
| **Data portability** | Customer data exportable in standard formats (CSV, JSON) |

---

## Contact

For security questions, vendor onboarding, or to request additional documentation:

| | |
|---|---|
| **Security inquiries** | security@kindora.co |
| **General enterprise** | enterprise@kindora.co |
| **CEO** | justin@kindora.co |
