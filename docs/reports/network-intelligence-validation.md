# Network Intelligence System — End-to-End Validation Report

**Date:** 2026-02-18
**Database:** 2,498 contacts, 2,496 tagged (99.9%), 2,498 embedded (100%)

---

## Use Case 1: Outdoorithm Collective Fundraiser Invite

**Query:** `proximity >= 40 AND outdoorithm_invite_fit IN ('high', 'medium')`
**Total matches:** 1,247 contacts

### Top 10 Results

| # | Name | Company | Proximity | Capacity | Fit |
|---|------|---------|-----------|----------|-----|
| 1 | Judith Bell | San Francisco Foundation | 94 (inner_circle) | 88 (major_donor) | high |
| 2 | Fred Blackwell | The San Francisco Foundation | 92 (inner_circle) | 98 (major_donor) | high |
| 3 | Mark Doherty | Founders Pledge | 92 (inner_circle) | 88 (major_donor) | medium |
| 4 | Raquiba LaBrie | San Francisco Foundation | 92 (inner_circle) | 78 (major_donor) | high |
| 5 | Karibu Nyaggah | Kindora | 92 (inner_circle) | 78 (major_donor) | medium |
| 6 | Samantha Hennessey | Google (Google.org Americas) | 90 (inner_circle) | 90 (major_donor) | medium |
| 7 | Sergio Garcia | UC Berkeley Advisory Board | 90 (inner_circle) | 80 (major_donor) | medium |
| 8 | Valerie Goode | Chief | 90 (inner_circle) | 78 (major_donor) | high |
| 9 | Ling Woo Liu | San Francisco Foundation | 90 (inner_circle) | 55 (mid_level) | high |
| 10 | Sally Steele | Louisville Institute | 90 (inner_circle) | 45 (mid_level) | high |

**Assessment:** Results are highly relevant. Top results are SF Foundation colleagues, Google.org collaborators, and close personal contacts — exactly who you'd invite to an Outdoorithm fundraiser. The 1,247 total is large because most warm+ contacts get "medium" fit; the ~222 "high" fit contacts would be the core invite list.

---

## Use Case 2: Kindora Enterprise Prospects

**Query:** `kindora_prospect_score >= 50 AND prospect_type IN ('enterprise_buyer', 'champion')`
**Total matches:** 935 contacts

### Top 10 Results

| # | Name | Company | Score | Type | Proximity |
|---|------|---------|-------|------|-----------|
| 1 | Annie Maxwell | Anthropic | 95 | enterprise_buyer | 48 (warm) |
| 2 | Fred Blackwell | The San Francisco Foundation | 92 | champion | 92 (inner_circle) |
| 3 | Rhea Suh | Marin Community Foundation | 92 | enterprise_buyer | 50 (warm) |
| 4 | Gregory Johnson | Foundation for the Mid South | 92 | enterprise_buyer | 48 (warm) |
| 5 | Stephanie Cornell | Fathers' UpLift | 92 | enterprise_buyer | 55 (warm) |
| 6 | Luis Arteaga | Y & H Soda Foundation | 92 | enterprise_buyer | 50 (warm) |
| 7 | Michele Lawrence Jawando | Omidyar Network | 92 | champion | 50 (warm) |
| 8 | Fatima Angeles | Levi Strauss Foundation | 92 | enterprise_buyer | 45 (warm) |
| 9 | Don Howard | James Irvine Foundation | 92 | enterprise_buyer | 58 (warm) |
| 10 | Karibu Nyaggah | Kindora | 92 | champion | 92 (inner_circle) |

**Assessment:** Excellent prospect identification. Foundation CEOs (Rhea Suh, Gregory Johnson, Don Howard, Luis Arteaga), corporate foundation leaders (Fatima Angeles at Levi Strauss), and network leaders (Michele Jawando at Omidyar) are exactly the enterprise buyer profile. Note: Karibu Nyaggah is a Kindora co-founder, not an external prospect — this is a known false positive.

---

## Use Case 3: People Interested in Outdoor Equity (Semantic Search)

**Query embedding:** "outdoor equity, nature access, public lands, camping, environmental justice"
**Method:** `match_contacts_by_interests` RPC (interests_embedding cosine similarity)

### Top 10 Results

| # | Name | Company | Similarity | Proximity |
|---|------|---------|------------|-----------|
| 1 | Jessica Oya | Oakland Unified School District | 0.597 | 58 (warm) |
| 2 | Cary Simmons | The Trust for Public Land | 0.591 | 45 (warm) |
| 3 | Wade Crowfoot | California Natural Resources Agency | 0.568 | 48 (warm) |
| 4 | Julian Castro | (former HUD Secretary) | 0.558 | 8 (distant) |
| 5 | Ben Jealous | Sierra Club | 0.547 | 15 (acquaintance) |
| 6 | Josie Norris | NewSun Energy | 0.543 | 52 (warm) |
| 7 | Alex Bailey | Black Outside, Inc | 0.543 | 50 (warm) |
| 8 | Erika Symmonds | GRID Alternatives | 0.539 | 28 (familiar) |
| 9 | Ron Griswell | Boyz N The Wood | 0.537 | 55 (warm) |
| 10 | CJ Goulding | Boyz N The Wood | 0.536 | 55 (warm) |

**Assessment:** Semantic search produces excellent topical matches. Trust for Public Land, CA Natural Resources Agency, Sierra Club, Black Outside, GRID Alternatives, and Boyz N The Wood are all directly relevant to outdoor equity. The model correctly identifies people whose interests and backgrounds align with nature access and environmental justice, even when those exact keywords aren't in their profiles.

---

## Use Case 4: Close Contacts (proximity >= 60)

**Query:** `proximity_score >= 60`
**Total matches:** 729 contacts

### Top 10 Results

| # | Name | Company | Proximity | Capacity |
|---|------|---------|-----------|----------|
| 1 | Judith Bell | San Francisco Foundation | 94 (inner_circle) | 88 (major_donor) |
| 2 | Fred Blackwell | The San Francisco Foundation | 92 (inner_circle) | 95 (major_donor) |
| 3 | Karibu Nyaggah | Kindora | 92 (inner_circle) | 78 (major_donor) |
| 4 | Mark Doherty | Founders Pledge | 92 (inner_circle) | 88 (major_donor) |
| 5 | Raquiba LaBrie | San Francisco Foundation | 92 (inner_circle) | 78 (major_donor) |
| 6 | Sergio Garcia | UC Berkeley Advisory Board | 90 (inner_circle) | 80 (major_donor) |
| 7 | Sally Steele | Louisville Institute | 90 (inner_circle) | 45 (mid_level) |
| 8 | Valerie Goode | Chief | 90 (inner_circle) | 78 (major_donor) |
| 9 | Samantha Hennessey | Google (Google.org Americas) | 90 (inner_circle) | 90 (major_donor) |
| 10 | Gerald Chertavian | Year Up | 88 (inner_circle) | 88 (major_donor) |

**Assessment:** The inner circle is correctly identified: SF Foundation board colleagues, Kindora co-founder, Google.org teammates, Year Up founder (Gerald Chertavian). Sally Steele (likely family) is appropriately scored high. Note: Layer 3 (communication history) is not yet implemented, so we can't filter by "haven't spoken to recently" — that will be a future enhancement.

---

## Use Case 5: Hybrid Search — "philanthropy education technology"

**Query:** Text "philanthropy education technology" + semantic embedding, RRF fusion
**Method:** `hybrid_contact_search` RPC (semantic + keyword + RRF)

### Top 10 Results

| # | Name | Company | RRF Score |
|---|------|---------|-----------|
| 1 | Hussainatu Blake | ED2Tech | 0.0377 |
| 2 | Alison Ascher Webber | Immigration Institute of the Bay Area | 0.0326 |
| 3 | Alexandra Trabulsi | Self-employed | 0.0320 |
| 4 | Sara Lomelin | Philanthropy Together | 0.0196 |
| 5 | Martin Munoz Careaga | American Heart Association | 0.0196 |
| 6 | Shanti Corrigan | Consortium of Cybersecurity Clinics | 0.0192 |
| 7 | Dakarai Aarons | Chan Zuckerberg Initiative | 0.0189 |
| 8 | Berit Ashla | Fremont Group | 0.0189 |
| 9 | Devi Thomas | Google | 0.0185 |
| 10 | Janak Padhiar | Renaissance Philanthropy | 0.0182 |

**Assessment:** Hybrid search effectively combines keyword and semantic signals. ED2Tech (education + technology), Philanthropy Together, Chan Zuckerberg Initiative (education + philanthropy + tech), and Renaissance Philanthropy are all on-point. The RRF fusion correctly ranks contacts that match across both modalities higher than those matching only one.

---

## Calibration Observations

### What's Working Well
1. **Proximity scores are dramatically better than old Perplexity scoring.** Old system: 94% "Cold." New system: 40% warm, 28% close, 0.9% inner circle. Shared employer/school detection works.
2. **Semantic search produces topically relevant results.** Outdoor equity query returns Trust for Public Land, Sierra Club, Black Outside — exactly right.
3. **Hybrid search combines signals effectively.** ED2Tech ranks #1 for "philanthropy education technology" because it matches both keyword and semantic signals.
4. **Enterprise buyer detection is accurate.** Foundation CEOs and corporate foundation leaders are correctly identified.

### Potential Calibration Issues
1. **Duplicate contacts.** Fred Blackwell, Judith Bell, and Brandi Howard each appear 2x in results — this is a data quality issue (duplicate rows in the contacts table), not a scoring issue.
2. **Kindora prospect scores skew high.** 935 contacts match the enterprise buyer/champion filter at score >= 50. A tighter filter (>= 70) would yield a more actionable list.
3. **Karibu Nyaggah appears as Kindora prospect.** As a Kindora co-founder, she's correctly tagged as "champion" but shouldn't be on an external sales prospect list. Would need a manual exclusion.
4. **Proximity tier thresholds may be generous.** 729 contacts with proximity >= 60 is a large "close" network. Layer 3 (communication history) will help separate truly active relationships from inferred ones.
5. **Semantic similarity scores are moderate** (0.5-0.6 range for interests). This is normal for text-embedding-3-small at 768 dims — the results are well-ranked even if absolute similarity values seem low.

### Not Yet Testable
- **Use Case 4 "haven't spoken to" filter** requires Layer 3 (communication history), which is Phase 3. Currently we can only identify close contacts, not filter by recency of communication.

---

## Validation Script

Script: `scripts/intelligence/validate_use_cases.py`
Run with: `source .venv/bin/activate && python scripts/intelligence/validate_use_cases.py`
