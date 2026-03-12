# Salesforce Integration — User Guide

**Kindora + Salesforce**

> **Full help article:** [kindora.co/resources/salesforce-integration](https://www.kindora.co/resources/salesforce-integration)

---

## What It Does

Connect your Salesforce account to Kindora to:
- **Import** foundation accounts and auto-match them against 175K+ foundations
- **See gift history** — past grants from each funder, pulled from Salesforce
- **Push funders to Salesforce** — one click creates an Account in your CRM
- **Discover warm intros** — cross-references your Salesforce contacts against foundation board members from 990 data

> **Works with any edition.** Standard Salesforce, NPSP (Nonprofit Success Pack), and Nonprofit Cloud are all supported. Kindora auto-detects your edition at connection time.

---

## 1. Connect Your Salesforce Account

1. Go to **Settings > Integrations**
2. Find the **Salesforce** card
3. Click **Connect to Salesforce**
4. Sign in to Salesforce and authorize Kindora
5. You'll be redirected back — the card now shows **Connected** in green with your org name and edition badge (Standard, NPSP, or Nonprofit Cloud)

Setup takes about 30 seconds.

---

## 2. Import Your Foundation Accounts

1. Click **Sync Now** on the Salesforce card
2. Kindora pulls in foundation-type accounts from your Salesforce org
3. Each account is auto-matched against Kindora's foundation database using:
   - **EIN exact match** (highest confidence)
   - **Name + state match**
   - **Name-only fuzzy match**
4. An **Import Summary** appears showing: Total Imported, Matched, Unmatched, and In Pipeline
5. Click **Add to My Funders** to promote matched foundations into your prospect pipeline

> **No automatic charges.** Imported funders land in your pipeline as "Not Yet Evaluated." You decide when to run an Intel Brief — you'll see the credit cost and confirm before anything is spent.

---

## 3. Import Gift History

1. Click **Sync Gift History** in the Gift History section on the Integrations page
2. Kindora imports grants and donations from Salesforce Opportunities (NPSP and Nonprofit Cloud gift records are also supported)
3. After the sync, you'll see the total number of gifts, total dollar amount, and count of unique funders

Open any matched funder's detail page to see a **Your Giving History** section showing:
- Total amount received and last gift date
- Gift type, status, fund/campaign name, and date for each gift
- Average gift size summary

---

## 4. Who Do You Know?

On a funder's detail page, look for the **Who Do You Know?** section:

1. Click **Scan for Connections** (first time only)
2. Kindora cross-references your Salesforce contacts against the funder's officers, directors, and trustees from IRS 990 filings
3. Each match shows:
   - **Contact name** from your Salesforce
   - **Connection type** — Direct, Employer, Shared Organization, or Past Affiliation
   - **Connection strength** — 1 to 5 dots
   - **Relationship path** — how they're connected
4. Click **Rescan** anytime to refresh after syncing new data

> This works for foundations that file IRS Form 990-PF (which lists officers and trustees). It won't appear for funders without an EIN.

---

## 5. Push Funders to Salesforce

When you discover a great funder match in Kindora that isn't in your Salesforce:

1. Open the funder's detail page
2. Click the **Add to Salesforce** button
3. Kindora creates an Account record in Salesforce containing the funder's details and intelligence summary
4. The button changes to a green **In Salesforce** badge

If the funder was originally imported from Salesforce, it will already show "In Salesforce." No duplicates are created.

---

## Sync History

Every sync is logged at **Settings > Integrations** in the Sync History table. You can see the date, sync type (account sync, gift import, relationship scan), status, records processed, and records matched. Click **Sync Now** anytime to pull in new accounts added since your last sync.

---

## Disconnecting

Click **Disconnect** on the Salesforce card and confirm. Your imported funders remain in Kindora — only the live connection is removed. You can reconnect at any time.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| **Token Expired** status | Click Disconnect, then Connect to Salesforce again to re-authorize |
| **No matches found** after sync | Kindora matches foundation-type accounts by EIN and name. Check that your Salesforce accounts have accurate names |
| **Who Do You Know shows no results** | Requires a funder with an EIN and 990 filings that list officers. Some newer or smaller foundations may not have this data |
| **Add to Salesforce button not visible** | Only appears on funders that have been evaluated with an Intel Brief. Run an evaluation first |
| **Gift history shows no results** | Requires Salesforce Opportunity records associated with foundation accounts. NPSP and Nonprofit Cloud gift records are also supported |

---

## Need Help?

- **In-app help:** Visit the Help Center at [kindora.co/resources/salesforce-integration](https://www.kindora.co/resources/salesforce-integration)
- **Schedule a walkthrough:** [calendly.com/justin-kindora/justin-meet](https://calendly.com/justin-kindora/justin-meet)
- **Email:** justin@kindora.co
