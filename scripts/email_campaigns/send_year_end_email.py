#!/usr/bin/env python3
"""
Year-End Email Campaign Sender

Sends personalized year-end emails to contacts using the Resend API.
Includes comprehensive tracking, CAN-SPAM compliance, and dry-run mode.

Usage:
    # Dry run (preview without sending)
    python send_year_end_email.py --dry-run

    # Send to specific number of contacts
    python send_year_end_email.py --limit 10

    # Full send (requires confirmation)
    python send_year_end_email.py --send

Author: Justin Steele
"""

import os
import sys
import time
import json
import hmac
import hashlib
import base64
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

import resend
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
PHYSICAL_ADDRESS_ENV = (os.getenv("SENDER_PHYSICAL_ADDRESS") or "").strip()
UNSUBSCRIBE_SECRET = os.getenv("UNSUBSCRIBE_SECRET", "")

# Unsubscribe URL base (Supabase Edge Function)
UNSUBSCRIBE_BASE_URL = "https://ypqsrejrsocebnldicke.supabase.co/functions/v1/unsubscribe"

# Resend rate limits
BATCH_SIZE = 100  # Resend allows up to 100 emails per batch request
RATE_LIMIT_DELAY = 0.6  # Seconds between batch requests (2 req/sec limit)

# Clients are initialized after config validation
supabase = None


def get_supabase_client():
    """Return initialized Supabase client or raise a clear error."""
    if supabase is None:
        raise RuntimeError("Supabase client not initialized. Ensure environment variables are set.")
    return supabase


def generate_unsubscribe_token(contact_id: int) -> str:
    """
    Generate a secure unsubscribe token for a contact.

    Token format: base64(contact_id:hmac_signature)
    This prevents users from guessing other contact IDs.
    """
    if not UNSUBSCRIBE_SECRET:
        raise ValueError("UNSUBSCRIBE_SECRET not configured")

    contact_id_str = str(contact_id)
    signature = hmac.new(
        UNSUBSCRIBE_SECRET.encode(),
        contact_id_str.encode(),
        hashlib.sha256
    ).digest()

    signature_b64 = base64.b64encode(signature).decode()
    token_data = f"{contact_id_str}:{signature_b64}"

    return base64.b64encode(token_data.encode()).decode()


def generate_unsubscribe_url(contact_id: int) -> str:
    """Generate the full unsubscribe URL for a contact."""
    token = generate_unsubscribe_token(contact_id)
    return f"{UNSUBSCRIBE_BASE_URL}?token={token}"


@dataclass
class EmailConfig:
    """Configuration for the email campaign."""
    campaign_name: str = "Year-End 2025 Personal Update"
    subject: str = "A personal year-end hello (and a beach football game)"
    from_email: str = "justin@truesteele.com"  # Must be verified domain
    from_name: str = "Justin Steele"
    reply_to: str = "justinrsteele@gmail.com"

    # CAN-SPAM required physical address
    physical_address: str = PHYSICAL_ADDRESS_ENV or "Oakland, CA"


# HTML Email Template with personalization placeholder
EMAIL_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: Georgia, 'Times New Roman', serif;
            line-height: 1.7;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
        }}
        p {{
            margin: 1em 0;
        }}
        ul {{
            margin: 1em 0;
            padding-left: 0;
            list-style: none;
        }}
        li {{
            margin: 0.8em 0;
            padding-left: 0;
        }}
        a {{
            color: #2563eb;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .hero-image {{
            margin: 1.5em 0;
            text-align: center;
        }}
        .hero-image img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
        }}
        .signature {{
            margin-top: 2em;
        }}
        .links {{
            margin-top: 1.5em;
            font-size: 0.9em;
            color: #666;
        }}
        .links a {{
            color: #666;
        }}
        .cta-list {{
            background: #f8f9fa;
            padding: 15px 20px;
            border-radius: 8px;
            margin: 1.5em 0;
        }}
        .cta-list strong {{
            color: #2563eb;
        }}
        .footer {{
            margin-top: 3em;
            padding-top: 1em;
            border-top: 1px solid #eee;
            font-size: 0.8em;
            color: #999;
        }}
    </style>
</head>
<body>
    <p>Hi {first_name},</p>

    <p>Two days after Thanksgiving, I watched a group of boys (some of whom had never seen the ocean) playing football on the beach at Half Moon Bay.</p>

    <p>Strangers on Friday. Teammates by Saturday.</p>

    <div class="hero-image">
        <img src="https://ypqsrejrsocebnldicke.supabase.co/storage/v1/object/public/images/HMB_Football_email.jpg" width="560" style="max-width: 100%; height: auto; display: block;" alt="Kids playing football on the beach at Half Moon Bay" />
    </div>

    <p>Our three older girls jumped in. The adults stood back with coffee, watching pure joy unfold in a place that hasn't always felt accessible or welcoming to families like theirs.</p>

    <p>That moment is a pretty good summary of my 2025.</p>

    <p>Many of you know that late last year, after nearly a decade leading Google.org's Americas philanthropy, my role was eliminated. It hurt. And it clarified what I wanted to build next.</p>

    <p>What I didn't expect was the outpouring that followed: messages, calls, letters from colleagues and community leaders. It reminded me that the work is carried by people, not institutions. If you were one of those people: thank you.</p>

    <p>I chose not to take severance, which meant I had to move quickly. Here's what I built:</p>

    <ul>
        <li><strong><a href="https://outdoorithmcollective.org">Outdoorithm Collective</a></strong> is a nonprofit I'm building with my wife Sally to help families reconnect with the land and each other. Half Moon Bay was one of our best trips yet: 35 people, cold air, warm fire, and a weekend I don't think any of us will forget. We also built <a href="https://outdoorithm.com">Outdoorithm.com</a>, a "Green Book" for public camping that helps families plan trips on their own.</li>

        <li><strong><a href="https://kindora.co">Kindora</a></strong> is a public benefit corporation I'm building with my co-founder Karibu Nyaggah (we met at Harvard Business School). Kindora uses AI to help small nonprofits find aligned funders. I know what it feels like to have a program that matters, barely any money in the bank, and no time to prospect. We launched in August, grew to 215+ organizations through word-of-mouth, and just moved to paid plans. We welcomed our first outside investor and are exploring whether additional capital makes sense in 2026.</li>

        <li><strong><a href="https://truesteele.com">True Steele</a></strong> is my fractional Chief Impact Officer practice. I've spent the year helping organizations like Flourish Fund, a faith-driven fund investing in foster care, navigate the real tensions of systemic change: staying accountable to communities while meeting funder expectations.</li>
    </ul>

    <p>If I'm sitting with anything as the year closes, it's this: I used to think a corporate paycheck was the definition of security. This year taught me that certainty is always borrowed. Building has been exhilarating, and at times terrifying, especially while raising four kids.</p>

    <p>But I'd rather take the risk on something I'm building than on someone else's org chart.</p>

    <p><strong>Looking ahead:</strong> In 2026, we want to grow Outdoorithm in two ways: bring more families into the Collective, and build a small circle of supporters who want to make outdoor equity real, not just aspirational. And we're focused on scaling Kindora to reach the thousands of nonprofits who need it.</p>

    <p><strong>A small invitation:</strong> If any of this resonates, I'd love to hear from you. Just reply with one of the words below. I'll follow up personally.</p>

    <div class="cta-list">
        <p style="margin: 0.5em 0;"><strong>OUTDOOR</strong> if you want to hear how families can join, or you're open to a conversation about supporting our trips</p>
        <p style="margin: 0.5em 0;"><strong>KINDORA</strong> if you want a demo, know a nonprofit that should try it, or are curious about investing as we grow</p>
        <p style="margin: 0.5em 0;"><strong>HELLO</strong> if you just want to reconnect (I'd genuinely love to hear what you've been up to)</p>
    </div>

    <p>Wishing you and yours a meaningful close to 2025.</p>

    <div class="signature">
        <p>With gratitude,<br><br>Justin</p>
    </div>

    <div class="links">
        <p>
            <a href="https://kindora.co">Kindora</a> &nbsp;|&nbsp;
            <a href="https://outdoorithmcollective.org">Outdoorithm Collective</a> &nbsp;|&nbsp;
            <a href="https://outdoorithm.com">Outdoorithm.com</a> &nbsp;|&nbsp;
            <a href="https://truesteele.com">True Steele</a> &nbsp;|&nbsp;
            <a href="https://www.linkedin.com/in/justinrichardsteele/">LinkedIn</a>
        </p>
    </div>

    <div class="footer">
        <p>{physical_address}</p>
        <p><a href="{unsubscribe_url}" style="color: #999;">Unsubscribe</a> from future emails</p>
    </div>
</body>
</html>
"""

# Plain text version for email clients that don't support HTML
EMAIL_TEXT_TEMPLATE = """
Hi {first_name},

Two days after Thanksgiving, I watched a group of boys (some of whom had never seen the ocean) playing football on the beach at Half Moon Bay.

Strangers on Friday. Teammates by Saturday.

[Photo: Kids playing football on the beach at Half Moon Bay]

Our three older girls jumped in. The adults stood back with coffee, watching pure joy unfold in a place that hasn't always felt accessible or welcoming to families like theirs.

That moment is a pretty good summary of my 2025.

Many of you know that late last year, after nearly a decade leading Google.org's Americas philanthropy, my role was eliminated. It hurt. And it clarified what I wanted to build next.

What I didn't expect was the outpouring that followed: messages, calls, letters from colleagues and community leaders. It reminded me that the work is carried by people, not institutions. If you were one of those people: thank you.

I chose not to take severance, which meant I had to move quickly. Here's what I built:

* Outdoorithm Collective (https://outdoorithmcollective.org) is a nonprofit I'm building with my wife Sally to help families reconnect with the land and each other. Half Moon Bay was one of our best trips yet: 35 people, cold air, warm fire, and a weekend I don't think any of us will forget. We also built Outdoorithm.com (https://outdoorithm.com), a "Green Book" for public camping that helps families plan trips on their own.

* Kindora (https://kindora.co) is a public benefit corporation I'm building with my co-founder Karibu Nyaggah (we met at Harvard Business School). Kindora uses AI to help small nonprofits find aligned funders. I know what it feels like to have a program that matters, barely any money in the bank, and no time to prospect. We launched in August, grew to 215+ organizations through word-of-mouth, and just moved to paid plans. We welcomed our first outside investor and are exploring whether additional capital makes sense in 2026.

* True Steele (https://truesteele.com) is my fractional Chief Impact Officer practice. I've spent the year helping organizations like Flourish Fund, a faith-driven fund investing in foster care, navigate the real tensions of systemic change: staying accountable to communities while meeting funder expectations.

If I'm sitting with anything as the year closes, it's this: I used to think a corporate paycheck was the definition of security. This year taught me that certainty is always borrowed. Building has been exhilarating, and at times terrifying, especially while raising four kids.

But I'd rather take the risk on something I'm building than on someone else's org chart.

Looking ahead: In 2026, we want to grow Outdoorithm in two ways: bring more families into the Collective, and build a small circle of supporters who want to make outdoor equity real, not just aspirational. And we're focused on scaling Kindora to reach the thousands of nonprofits who need it.

A small invitation: If any of this resonates, I'd love to hear from you. Just reply with one of the words below. I'll follow up personally.

Reply with:
- OUTDOOR if you want to hear how families can join, or you're open to a conversation about supporting our trips
- KINDORA if you want a demo, know a nonprofit that should try it, or are curious about investing as we grow
- HELLO if you just want to reconnect (I'd genuinely love to hear what you've been up to)

Wishing you and yours a meaningful close to 2025.

With gratitude,

Justin

---
Kindora: https://kindora.co
Outdoorithm Collective: https://outdoorithmcollective.org
Outdoorithm.com: https://outdoorithm.com
True Steele: https://truesteele.com
LinkedIn: https://www.linkedin.com/in/justinrichardsteele/

---
{physical_address}
Unsubscribe: {unsubscribe_url}
"""


def get_eligible_contacts(limit: Optional[int] = None,
                          exclude_sent_campaign: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch contacts eligible for emailing.

    Criteria:
    - Has a valid email address
    - Not unsubscribed
    - Has a first name for personalization

    Args:
        limit: Maximum number of contacts to fetch
        exclude_sent_campaign: Campaign ID to exclude already-sent contacts

    Returns:
        List of contact dictionaries
    """
    client = get_supabase_client()

    # Get list of contact IDs who already received this campaign
    sent_contact_ids = set()
    if exclude_sent_campaign:
        sent_response = client.table('email_sends').select('contact_id').eq(
            'campaign_id', exclude_sent_campaign
        ).in_('status', ['sent', 'delivered', 'opened', 'clicked']).execute()

        sent_contact_ids = {row['contact_id'] for row in sent_response.data if row['contact_id']}

    # Fetch all contacts using pagination (Supabase default limit is 1000)
    all_contacts = []
    page_size = 1000
    offset = 0

    while True:
        query = client.table('contacts').select(
            'id, first_name, email, personal_email, work_email'
        ).neq('unsubscribed', True)

        query = query.or_("email.not.is.null,personal_email.not.is.null,work_email.not.is.null")
        query = query.order('id')
        query = query.range(offset, offset + page_size - 1)

        response = query.execute()

        if not response.data:
            break

        # Filter out already-sent contacts
        if sent_contact_ids:
            filtered = [c for c in response.data if c['id'] not in sent_contact_ids]
            all_contacts.extend(filtered)
        else:
            all_contacts.extend(response.data)

        # Check if we got a full page (more data might exist)
        if len(response.data) < page_size:
            break

        offset += page_size

        # If we have a limit and we've reached it, stop fetching
        if limit and len(all_contacts) >= limit:
            all_contacts = all_contacts[:limit]
            break

    # Apply limit if specified
    if limit and len(all_contacts) > limit:
        all_contacts = all_contacts[:limit]

    return all_contacts


def get_best_email(contact: Dict[str, Any]) -> Optional[str]:
    """
    Get the best email address for a contact.
    Priority: personal_email > email > work_email (for personal year-end message)
    """
    for field in ('personal_email', 'email', 'work_email'):
        value = contact.get(field)
        if value:
            trimmed = value.strip()
            if trimmed:
                return trimmed
    return None


def normalize_email(email: Optional[str]) -> Optional[str]:
    """Normalize email for consistent comparisons."""
    if not email:
        return None
    return email.strip().lower()


def annotate_and_dedupe_contacts(contacts: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Attach target_email to each contact using priority rules and deduplicate by email.

    Returns:
        Tuple of (deduped_contacts, skipped_contacts_with_reason)
    """
    deduped = []
    skipped = []
    seen_emails = set()

    for contact in contacts:
        email_address = get_best_email(contact)
        normalized = normalize_email(email_address)

        if not normalized:
            skipped.append({
                "contact_id": contact.get('id'),
                "reason": "no_email"
            })
            continue

        if normalized in seen_emails:
            skipped.append({
                "contact_id": contact.get('id'),
                "email": email_address,
                "reason": "duplicate_email"
            })
            continue

        seen_emails.add(normalized)
        contact['target_email'] = email_address
        deduped.append(contact)

    return deduped, skipped


def personalize_email(template: str, contact: Dict[str, Any], config: EmailConfig) -> str:
    """
    Personalize the email template with contact data.

    Args:
        template: Email template with {placeholders}
        contact: Contact data dictionary
        config: Email configuration

    Returns:
        Personalized email content
    """
    first_name = contact.get('first_name', '').strip()

    # Use "there" if no first name available
    if not first_name:
        first_name = "there"

    # Generate unsubscribe URL if secret is configured
    if UNSUBSCRIBE_SECRET:
        unsubscribe_url = generate_unsubscribe_url(contact['id'])
    else:
        # Fallback to mailto link
        unsubscribe_url = f"mailto:{config.reply_to}?subject=unsubscribe"

    return template.format(
        first_name=first_name,
        physical_address=config.physical_address,
        unsubscribe_url=unsubscribe_url
    )


def create_campaign(config: EmailConfig) -> str:
    """
    Create a new email campaign record in the database.

    Returns:
        Campaign ID
    """
    client = get_supabase_client()
    campaign_data = {
        'name': config.campaign_name,
        'subject': config.subject,
        'from_email': config.from_email,
        'from_name': config.from_name,
        'reply_to': config.reply_to,
        'html_body': EMAIL_HTML_TEMPLATE,
        'text_body': EMAIL_TEXT_TEMPLATE,
        'status': 'draft'
    }

    response = client.table('email_campaigns').insert(campaign_data).execute()

    if response.data:
        return response.data[0]['id']
    else:
        raise Exception("Failed to create campaign record")


def update_campaign_status(campaign_id: str, status: str, **kwargs):
    """Update campaign status and optional fields."""
    update_data = {'status': status, **kwargs}
    client = get_supabase_client()
    client.table('email_campaigns').update(update_data).eq('id', campaign_id).execute()


def record_email_send(campaign_id: str, contact: Dict[str, Any],
                      email_address: str, status: str = 'pending',
                      resend_message_id: Optional[str] = None,
                      error_message: Optional[str] = None) -> str:
    """
    Record an email send attempt in the database.

    Returns:
        Email send record ID
    """
    send_data = {
        'campaign_id': campaign_id,
        'contact_id': contact['id'],
        'email_address': email_address,
        'first_name': contact.get('first_name'),
        'status': status,
        'resend_message_id': resend_message_id,
        'error_message': error_message,
        'sent_at': datetime.now().isoformat() if status in ['sent', 'delivered'] else None
    }

    client = get_supabase_client()
    response = client.table('email_sends').insert(send_data).execute()

    if response.data:
        return response.data[0]['id']
    return None


def update_email_send_status(send_id: str, status: str, **kwargs):
    """Update an email send record."""
    update_data = {'status': status, **kwargs}
    client = get_supabase_client()
    client.table('email_sends').update(update_data).eq('id', send_id).execute()


def send_batch_emails(contacts: List[Dict[str, Any]],
                      campaign_id: str,
                      config: EmailConfig,
                      dry_run: bool = False) -> Tuple[int, int]:
    """
    Send emails in batches using Resend's batch API.

    Args:
        contacts: List of contacts to email
        campaign_id: Campaign ID for tracking
        config: Email configuration
        dry_run: If True, simulate sending without actually sending

    Returns:
        Tuple of (success_count, failure_count)
    """
    success_count = 0
    failure_count = 0

    # Process in batches
    for i in range(0, len(contacts), BATCH_SIZE):
        batch = contacts[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(contacts) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} contacts)...")

        if dry_run:
            # Dry run: simulate sending
            for contact in batch:
                email_address = contact.get('target_email')
                if not email_address:
                    print(f"  [SKIP] Contact {contact['id']}: No email address")
                    failure_count += 1
                    continue

                first_name = contact.get('first_name', 'there')
                print(f"  [DRY RUN] Would send to: {email_address} (Hi {first_name})")
                success_count += 1
        else:
            # Real send: prepare batch request
            emails_to_send = []
            contacts_in_batch = []  # Track contacts in order for response mapping

            for contact in batch:
                email_address = contact.get('target_email')
                if not email_address:
                    print(f"  [SKIP] Contact {contact['id']}: No email address")
                    record_email_send(campaign_id, contact, '', 'failed',
                                     error_message='No email address')
                    failure_count += 1
                    continue

                # Personalize content
                html_content = personalize_email(EMAIL_HTML_TEMPLATE, contact, config)
                text_content = personalize_email(EMAIL_TEXT_TEMPLATE, contact, config)

                email_payload = {
                    "from": f"{config.from_name} <{config.from_email}>",
                    "to": [email_address],
                    "reply_to": config.reply_to,
                    "subject": config.subject,
                    "html": html_content,
                    "text": text_content,
                }

                # Add List-Unsubscribe header (one-click URL preferred, mailto as fallback)
                if UNSUBSCRIBE_SECRET:
                    unsub_url = generate_unsubscribe_url(contact['id'])
                    email_payload["headers"] = {
                        "List-Unsubscribe": f"<{unsub_url}>, <mailto:{config.reply_to}?subject=unsubscribe>",
                        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"
                    }
                elif config.reply_to:
                    email_payload["headers"] = {
                        "List-Unsubscribe": f"<mailto:{config.reply_to}?subject=unsubscribe>"
                    }

                emails_to_send.append(email_payload)
                contacts_in_batch.append(contact)

            if not emails_to_send:
                continue

            try:
                # Send batch via Resend
                batch_response = resend.Batch.send(emails_to_send)

                # Process results - batch_response is a dict with 'data' key
                # Results are returned in the same order as emails_to_send
                response_data = batch_response.get('data') if isinstance(batch_response, dict) else getattr(batch_response, 'data', None)
                if response_data:
                    for idx, result in enumerate(response_data):
                        message_id = result.get('id')
                        contact = contacts_in_batch[idx]
                        target_email = contact.get('target_email')

                        record_email_send(
                            campaign_id, contact, target_email,
                            'sent', resend_message_id=message_id
                        )
                        print(f"  [SENT] {target_email} (ID: {message_id})")
                        success_count += 1
                else:
                    # Handle batch send errors
                    for contact in contacts_in_batch:
                        record_email_send(
                            campaign_id, contact, contact.get('target_email'),
                            'failed', error_message='Batch send failed - no response data'
                        )
                        failure_count += 1

            except Exception as e:
                print(f"  [ERROR] Batch send failed: {str(e)}")
                # Record failures for all contacts in this batch
                for contact in contacts_in_batch:
                    record_email_send(
                        campaign_id, contact, contact.get('target_email'),
                        'failed', error_message=str(e)
                    )
                    failure_count += 1

        # Rate limiting: wait between batches
        if i + BATCH_SIZE < len(contacts):
            print(f"  Waiting {RATE_LIMIT_DELAY}s for rate limit...")
            time.sleep(RATE_LIMIT_DELAY)

    return success_count, failure_count


def preview_email(contact: Dict[str, Any], config: EmailConfig):
    """Preview the personalized email for a specific contact."""
    email_address = get_best_email(contact)
    html_content = personalize_email(EMAIL_HTML_TEMPLATE, contact, config)

    print("\n" + "="*60)
    print("EMAIL PREVIEW")
    print("="*60)
    print(f"From: {config.from_name} <{config.from_email}>")
    print(f"Reply-To: {config.reply_to}")
    print(f"To: {email_address}")
    print(f"Subject: {config.subject}")
    print("-"*60)
    print("\n[HTML version - first 2000 chars]")
    print(html_content[:2000])
    if len(html_content) > 2000:
        print(f"\n... ({len(html_content) - 2000} more chars)")
    print("="*60)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Send year-end email campaign via Resend',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python send_year_end_email.py --dry-run           # Preview without sending
  python send_year_end_email.py --dry-run --limit 5 # Preview first 5
  python send_year_end_email.py --preview           # Show email template
  python send_year_end_email.py --send --limit 10   # Send to 10 contacts
  python send_year_end_email.py --send              # Send to all (requires confirm)
        """
    )

    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate sending without actually sending emails')
    parser.add_argument('--send', action='store_true',
                        help='Actually send the emails')
    parser.add_argument('--limit', type=int, default=None,
                        help='Maximum number of contacts to email')
    parser.add_argument('--preview', action='store_true',
                        help='Preview the email template with a sample contact')
    parser.add_argument('--from-email', type=str, default='justin@truesteele.com',
                        help='From email address (must be verified domain)')
    parser.add_argument('--reply-to', type=str, default='justinrsteele@gmail.com',
                        help='Reply-to email address')
    parser.add_argument('--physical-address', type=str, default=PHYSICAL_ADDRESS_ENV,
                        help='Physical mailing address for CAN-SPAM footer')
    parser.add_argument('--resume-campaign', type=str, default=None,
                        help='Resume an existing campaign by ID')

    args = parser.parse_args()

    # Validate environment (skip Supabase/Resend checks for template-only preview)
    if args.send and not RESEND_API_KEY:
        print("ERROR: RESEND_API_KEY not found in environment variables")
        sys.exit(1)

    if (not SUPABASE_URL or not SUPABASE_KEY) and not args.preview:
        print("ERROR: Supabase configuration not found")
        sys.exit(1)

    # Configure email settings
    config = EmailConfig(
        from_email=args.from_email,
        reply_to=args.reply_to,
        physical_address=args.physical_address or (PHYSICAL_ADDRESS_ENV or "Oakland, CA")
    )

    if not config.physical_address:
        print("WARNING: Physical address missing; set SENDER_PHYSICAL_ADDRESS or pass --physical-address.")

    if args.send:
        if not config.physical_address or config.physical_address.strip().lower() == "oakland, ca":
            print("ERROR: Provide a full physical mailing address via SENDER_PHYSICAL_ADDRESS or --physical-address.")
            sys.exit(1)
        if not config.reply_to:
            print("ERROR: Reply-To address is required so unsubscribe replies reach you.")
            sys.exit(1)

    # Initialize clients after validation
    if not args.preview:
        try:
            global supabase
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            print(f"ERROR: Failed to initialize Supabase client: {e}")
            sys.exit(1)

        if args.send:
            resend.api_key = RESEND_API_KEY

    # Preview mode
    if args.preview:
        sample_contact = {
            'id': 0,
            'first_name': 'Alex',
            'email': 'alex@example.com'
        }
        preview_email(sample_contact, config)
        return

    # Require explicit action
    if not args.dry_run and not args.send:
        print("ERROR: Must specify either --dry-run or --send")
        print("Use --dry-run to preview, or --send to actually send emails")
        sys.exit(1)

    # Fetch eligible contacts
    print("\nFetching eligible contacts...")
    contacts = get_eligible_contacts(
        limit=args.limit,
        exclude_sent_campaign=args.resume_campaign
    )

    print(f"Found {len(contacts)} eligible contacts before deduplication")

    contacts, skipped_contacts = annotate_and_dedupe_contacts(contacts)

    if skipped_contacts:
        reason_counts = {}
        for entry in skipped_contacts:
            reason = entry.get("reason", "unknown")
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        print(f"Skipped {len(skipped_contacts)} contacts (details: {reason_counts})")

    print(f"{len(contacts)} contacts remain after deduplication")

    if not contacts:
        print("No contacts to email. Exiting.")
        return

    # Show summary
    print("\n" + "="*60)
    print("CAMPAIGN SUMMARY")
    print("="*60)
    print(f"Campaign: {config.campaign_name}")
    print(f"Subject: {config.subject}")
    print(f"From: {config.from_name} <{config.from_email}>")
    print(f"Reply-To: {config.reply_to}")
    print(f"Recipients: {len(contacts)}")
    print(f"Mode: {'DRY RUN (no emails sent)' if args.dry_run else 'LIVE SEND'}")
    print("="*60)

    # Confirmation for live send
    if args.send and not args.dry_run:
        if len(contacts) > 10 and not args.resume_campaign:
            confirm = input(f"\nYou are about to send {len(contacts)} emails. Type 'SEND' to confirm: ")
            if confirm != 'SEND':
                print("Cancelled.")
                return

    # Create or resume campaign
    if args.resume_campaign:
        campaign_id = args.resume_campaign
        print(f"\nResuming campaign: {campaign_id}")
    elif not args.dry_run:
        campaign_id = create_campaign(config)
        print(f"\nCreated campaign: {campaign_id}")
        update_campaign_status(campaign_id, 'sending',
                              started_at=datetime.now().isoformat(),
                              total_recipients=len(contacts))
    else:
        campaign_id = None

    # Send emails
    start_time = time.time()
    success_count, failure_count = send_batch_emails(
        contacts, campaign_id, config, dry_run=args.dry_run
    )
    elapsed_time = time.time() - start_time

    # Update campaign status
    if campaign_id and not args.dry_run:
        update_campaign_status(
            campaign_id,
            'completed',
            completed_at=datetime.now().isoformat(),
            sent_count=success_count
        )

    # Print summary
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"Total processed: {len(contacts)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failure_count}")
    print(f"Time elapsed: {elapsed_time:.2f} seconds")
    if campaign_id:
        print(f"Campaign ID: {campaign_id}")
    print("="*60)


if __name__ == "__main__":
    main()
