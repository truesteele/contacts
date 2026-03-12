#!/usr/bin/env python3
"""
verify_emails.py — Cross-reference contact emails against actual Gmail thread participants.

For each contact with an email, checks if that email actually appears in any of their
email thread participants. If a different email appears instead, flags the mismatch.

This catches the "Rowan Barnett problem": find_emails.py generates a valid email permutation
(e.g., rbarnett@google.com) that belongs to a different person (Ryan Barnett), while the
real email (rowbar@google.com) exists in actual correspondence.

Smart fix mode (--fix):
  - Classifies emails as work vs personal
  - Never overwrites a work email with a personal one in the primary field
  - Populates work_email and personal_email fields appropriately
  - Requires strong name match (last name in local part) for auto-fix
"""

import os
import sys
import argparse
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

import psycopg2
import psycopg2.extras


def get_db_connection():
    return psycopg2.connect(
        host="db.ypqsrejrsocebnldicke.supabase.co",
        port=5432,
        dbname="postgres",
        user="postgres",
        password=os.environ["SUPABASE_DB_PASSWORD"],
    )


def normalize_email(email):
    """Lowercase and strip an email address."""
    if not email:
        return None
    return email.strip().lower()


# Justin's own email addresses — exclude from participant matching
JUSTIN_EMAILS = {
    "justinrsteele@gmail.com",
    "justin@truesteele.com",
    "justin@kindora.co",
    "justin@outdoorithm.com",
    "justin@outdoorithmcollective.org",
    "jsteele@google.com",
    "justinsteele@google.com",
    "steele, justin",
}

PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "me.com", "aol.com", "protonmail.com", "live.com", "msn.com",
    "comcast.net", "verizon.net", "att.net", "sbcglobal.net", "frontier.com",
    "mac.com", "rocketmail.com", "earthlink.net", "netzero.net", "optonline.net",
    "yahoo.co.uk", "hotmail.co.uk", "googlemail.com",
}


def is_personal_email(email):
    """Check if an email is from a personal domain (gmail, yahoo, etc.)."""
    if not email:
        return False
    domain = email.split("@")[1] if "@" in email else ""
    return domain in PERSONAL_DOMAINS


def is_edu_email(email):
    """Check if an email is from an educational institution."""
    if not email:
        return False
    domain = email.split("@")[1] if "@" in email else ""
    return domain.endswith(".edu")


def classify_email(email):
    """Classify email as 'personal', 'edu', or 'work'."""
    if not email:
        return None
    if is_personal_email(email):
        return "personal"
    if is_edu_email(email):
        return "edu"
    return "work"


def extract_participant_emails(participants):
    """Extract email addresses from participants JSONB array."""
    if not participants:
        return set()
    emails = set()
    for p in participants:
        email = p.get("email", "")
        if email and "@" in email:
            emails.add(normalize_email(email))
    return emails


def score_candidate(email, first_name, last_name):
    """Score how well an email matches a contact's name. Higher = better match.
    Returns negative score if the email likely belongs to a different person."""
    local_part = email.split("@")[0].lower()
    first = (first_name or "").lower()
    last = (last_name or "").lower()
    score = 0

    if last and len(last) > 2 and last in local_part:
        score += 10  # last name match is strong signal
    if first and len(first) > 2 and first in local_part:
        score += 5  # first name match is good signal

    # Negative signal: if local part looks like "othername.lastname" or "othername_lastname"
    # where othername is NOT the contact's first name, it's likely a different person
    if score >= 10 and first and len(first) > 2:
        # Method 1: Split local part by common separators
        parts = local_part.replace(".", " ").replace("_", " ").replace("-", " ").split()
        if len(parts) >= 2:
            potential_first = parts[0]
            if (len(potential_first) >= 3
                    and potential_first != first
                    and potential_first.isalpha()
                    and first not in potential_first
                    and potential_first not in first):
                score = -1

        # Method 2: Check concatenated form — strip the last name from local part
        # e.g., "lisaflazarus" → strip "lazarus" → "lisaf" — not "amy"
        if score >= 10 and last in local_part:
            idx = local_part.find(last)
            prefix = local_part[:idx].rstrip("._-")
            if (len(prefix) >= 3
                    and prefix.isalpha()
                    and prefix != first
                    and first not in prefix
                    and prefix not in first):
                score = -1

    return score


def find_best_candidates(participant_emails, first_name, last_name):
    """Find candidate emails that match the contact's name, with scores."""
    candidates = []
    for pe in participant_emails:
        s = score_candidate(pe, first_name, last_name)
        if s > 0:
            candidates.append((pe, s))
    # Sort by score descending
    candidates.sort(key=lambda x: -x[1])
    return candidates


def run_verification(fix=False, dry_run=False, verbose=False):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Step 1: Get all contacts with emails
    print("Loading contacts with emails...")
    cur.execute("""
        SELECT id, first_name, last_name, email, email_type,
               work_email, personal_email, linkedin_url
        FROM contacts
        WHERE email IS NOT NULL AND email != ''
        ORDER BY id
    """)
    contacts = {row["id"]: row for row in cur.fetchall()}
    print(f"  {len(contacts)} contacts with emails")

    # Step 2: Get all email threads with participants
    print("Loading email threads with participants...")
    cur.execute("""
        SELECT contact_id, participants, account_email, subject
        FROM contact_email_threads
        WHERE channel = 'email'
        AND participants IS NOT NULL
    """)
    threads = cur.fetchall()
    print(f"  {len(threads)} email threads loaded")

    # Step 3: Build participant email map per contact
    print("Building participant email map...")
    contact_participant_emails = defaultdict(set)
    for thread in threads:
        cid = thread["contact_id"]
        participant_emails = extract_participant_emails(thread["participants"])
        participant_emails -= JUSTIN_EMAILS
        contact_participant_emails[cid] |= participant_emails

    contacts_with_threads = set(contact_participant_emails.keys())
    print(f"  {len(contacts_with_threads)} contacts have email threads with participant data")

    # Step 4: Cross-reference
    mismatches = []
    verified = []
    no_threads = []
    not_in_participants = []

    for cid, contact in contacts.items():
        db_email = normalize_email(contact["email"])

        if cid not in contacts_with_threads:
            no_threads.append(contact)
            continue

        participant_emails = contact_participant_emails[cid]

        if db_email in participant_emails:
            verified.append(contact)
        else:
            first_name = (contact["first_name"] or "").lower()
            last_name = (contact["last_name"] or "").lower()

            scored_candidates = find_best_candidates(participant_emails, first_name, last_name)

            # Only include candidates with last name match (score >= 10)
            # to reduce false positives like "dave.scott" matching Dave Coles
            strong_candidates = [(e, s) for e, s in scored_candidates if s >= 10]

            if strong_candidates:
                mismatches.append({
                    "contact": contact,
                    "db_email": db_email,
                    "candidates": strong_candidates,
                    "all_participant_emails": participant_emails,
                })
            elif scored_candidates:
                # Weak match (first name only) — flag but don't auto-fix
                mismatches.append({
                    "contact": contact,
                    "db_email": db_email,
                    "candidates": scored_candidates,
                    "all_participant_emails": participant_emails,
                    "weak_match": True,
                })
            else:
                not_in_participants.append({
                    "contact": contact,
                    "db_email": db_email,
                    "all_participant_emails": participant_emails,
                })

    # Step 5: Report
    print("\n" + "=" * 80)
    print("EMAIL VERIFICATION RESULTS")
    print("=" * 80)

    strong_mismatches = [m for m in mismatches if not m.get("weak_match")]
    weak_mismatches = [m for m in mismatches if m.get("weak_match")]

    print(f"\nTotal contacts with email:         {len(contacts)}")
    print(f"  Verified (email in threads):     {len(verified)}")
    print(f"  No email threads at all:         {len(no_threads)}")
    print(f"  MISMATCH (strong, last name):    {len(strong_mismatches)}")
    print(f"  MISMATCH (weak, first name only):{len(weak_mismatches)}")
    print(f"  Not in participants (unclear):   {len(not_in_participants)}")

    for label, items in [("STRONG MISMATCHES", strong_mismatches), ("WEAK MISMATCHES", weak_mismatches)]:
        if items:
            print(f"\n{'=' * 80}")
            print(f"{label}")
            print(f"{'=' * 80}")
            for m in items:
                c = m["contact"]
                name = f"{c['first_name'] or ''} {c['last_name'] or ''}".strip()
                db_type = classify_email(m["db_email"])
                print(f"\n  [{c['id']}] {name}")
                print(f"    DB email:     {m['db_email']} ({db_type})")
                print(f"    DB work_email: {c.get('work_email') or '(empty)'}")
                print(f"    DB personal:   {c.get('personal_email') or '(empty)'}")
                for email, score in m["candidates"]:
                    ctype = classify_email(email)
                    print(f"    Candidate:    {email} ({ctype}, score={score})")
                if verbose:
                    cand_emails = {e for e, _ in m["candidates"]}
                    other = m["all_participant_emails"] - cand_emails
                    if other:
                        print(f"    Other addrs:  {len(other)} other participant emails")

    if not_in_participants and verbose:
        print(f"\n{'=' * 80}")
        print(f"NOT IN PARTICIPANTS — DB email absent but no name-match found")
        print(f"{'=' * 80}")
        for item in not_in_participants[:50]:
            c = item["contact"]
            name = f"{c['first_name'] or ''} {c['last_name'] or ''}".strip()
            print(f"\n  [{c['id']}] {name}")
            print(f"    DB email:       {item['db_email']}")
            n = len(item["all_participant_emails"])
            print(f"    Thread emails:  {n} unique addresses (none match name)")

    # Step 6: Smart fix
    if (fix or dry_run) and strong_mismatches:
        print(f"\n{'=' * 80}")
        action = "DRY RUN" if dry_run else "AUTO-FIXING"
        print(f"{action} — {len(strong_mismatches)} strong mismatches")
        print(f"{'=' * 80}")

        fixed = 0
        skipped = 0
        updates = []

        for m in strong_mismatches:
            c = m["contact"]
            cid = c["id"]
            name = f"{c['first_name'] or ''} {c['last_name'] or ''}".strip()
            db_email = m["db_email"]
            db_type = classify_email(db_email)
            existing_work = normalize_email(c.get("work_email"))
            existing_personal = normalize_email(c.get("personal_email"))

            # Pick the best candidate (highest score, prefer single)
            candidates = m["candidates"]
            if len(candidates) > 3:
                print(f"  SKIP [{cid}] {name}: too many candidates ({len(candidates)})")
                skipped += 1
                continue

            # If multiple candidates, try to narrow: prefer ones with BOTH first+last name
            first_name = (c["first_name"] or "").lower()
            last_name = (c["last_name"] or "").lower()
            best = [e for e, s in candidates if s >= 15]  # both first+last
            if not best:
                best = [e for e, s in candidates if s >= 10]  # at least last name

            if len(best) > 2:
                print(f"  SKIP [{cid}] {name}: {len(best)} strong candidates, manual review needed")
                for e in best:
                    print(f"         {e} ({classify_email(e)})")
                skipped += 1
                continue

            # For each candidate, decide what to do
            applied = False
            for new_email in best:
                new_type = classify_email(new_email)

                # Check if this email is already stored in the right place
                if new_email == existing_work or new_email == existing_personal:
                    # Already have this email — check if primary needs updating
                    if new_email == existing_work and db_type == "personal":
                        # Work email exists but primary is personal — promote work
                        update = {"id": cid, "name": name}
                        update["action"] = "promote_existing_work"
                        update["sql"] = ("UPDATE contacts SET email = %s, "
                                         "email_type = 'work' WHERE id = %s")
                        update["params"] = (new_email, cid)
                        update["desc"] = (f"PROMOTE existing work_email={new_email} to primary "
                                          f"(was email={db_email})")
                        updates.append(update)
                        break
                    else:
                        # Already stored — try next candidate instead of giving up
                        continue

                # Determine the update action
                update = {"id": cid, "name": name, "old": db_email, "new": new_email}

                if db_type in ("work", "edu") and new_type == "personal":
                    # DB has work email, thread shows personal — KEEP work, ADD personal
                    if existing_personal and existing_personal != new_email:
                        print(f"  SKIP [{cid}] {name}: already has personal_email={existing_personal}, "
                              f"won't overwrite with {new_email}")
                        skipped += 1
                        continue
                    update["action"] = "add_personal"
                    update["sql"] = "UPDATE contacts SET personal_email = %s WHERE id = %s"
                    update["params"] = (new_email, cid)
                    update["desc"] = f"ADD personal_email={new_email} (keep email={db_email})"

                elif db_type == "personal" and new_type in ("work", "edu"):
                    # DB has personal email, thread shows work — PROMOTE work to primary
                    update["action"] = "promote_work"
                    update["sql"] = ("UPDATE contacts SET email = %s, work_email = %s, "
                                     "personal_email = COALESCE(personal_email, %s), "
                                     "email_type = 'work' WHERE id = %s")
                    update["params"] = (new_email, new_email, db_email, cid)
                    update["desc"] = (f"SET email={new_email} (work), "
                                      f"personal_email={db_email}")

                elif db_type == "personal" and new_type == "personal":
                    # Both personal — the one in threads is verified, replace primary
                    update["action"] = "replace_personal"
                    update["sql"] = "UPDATE contacts SET email = %s, personal_email = %s WHERE id = %s"
                    update["params"] = (new_email, new_email, cid)
                    update["desc"] = f"REPLACE email={db_email} → {new_email} (both personal)"

                elif db_type in ("work", "edu") and new_type in ("work", "edu"):
                    # Both work — the one in threads is likely current, replace
                    update["action"] = "replace_work"
                    update["sql"] = ("UPDATE contacts SET email = %s, work_email = %s, "
                                     "email_type = 'work' WHERE id = %s")
                    update["params"] = (new_email, new_email, cid)
                    update["desc"] = f"REPLACE email={db_email} → {new_email} (both work)"

                else:
                    print(f"  SKIP [{cid}] {name}: unexpected types {db_type} → {new_type}")
                    skipped += 1
                    continue

                updates.append(update)
                applied = True
                break  # Only process the first/best candidate

            if not applied and not any(u["id"] == cid for u in updates):
                print(f"  SKIP [{cid}] {name}: all candidates already stored in work/personal fields")
                skipped += 1

        # Apply updates
        for u in updates:
            prefix = "  [DRY] " if dry_run else "  "
            print(f"{prefix}[{u['id']}] {u['name']}: {u['desc']}")
            if not dry_run:
                cur.execute(u["sql"], u["params"])

        if not dry_run and updates:
            conn.commit()

        print(f"\n  {'Would fix' if dry_run else 'Fixed'}: {len(updates)}, Skipped: {skipped}")

    cur.close()
    conn.close()

    return {
        "total": len(contacts),
        "verified": len(verified),
        "no_threads": len(no_threads),
        "strong_mismatches": len(strong_mismatches),
        "weak_mismatches": len(weak_mismatches),
        "not_in_participants": len(not_in_participants),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify contact emails against Gmail thread participants"
    )
    parser.add_argument("--fix", action="store_true",
                        help="Auto-fix mismatches with smart work/personal logic")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be fixed without making changes")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed output")
    args = parser.parse_args()

    results = run_verification(fix=args.fix, dry_run=args.dry_run, verbose=args.verbose)
