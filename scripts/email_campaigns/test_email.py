#!/usr/bin/env python3
"""
Test script to send a single email to verify the full flow works.
Usage: python scripts/email_campaigns/test_email.py
"""

import os
import sys
import hmac
import hashlib
import base64

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import resend

# Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
UNSUBSCRIBE_SECRET = os.getenv("UNSUBSCRIBE_SECRET")
SENDER_PHYSICAL_ADDRESS = os.getenv("SENDER_PHYSICAL_ADDRESS", "")

# Test recipient
TEST_EMAIL = "justin@outdoorithm.com"
TEST_FIRST_NAME = "Justin"
TEST_CONTACT_ID = 99999  # Fake ID for testing

# Email settings
FROM_EMAIL = "justin@truesteele.com"
FROM_NAME = "Justin Steele"
REPLY_TO = "justinrsteele@gmail.com"
SUBJECT = "[TEST] A personal year-end hello (and a beach football game)"


def generate_unsubscribe_token(contact_id: int) -> str:
    """Generate HMAC-signed token for secure unsubscribe."""
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


def get_unsubscribe_url(contact_id: int) -> str:
    """Generate the full unsubscribe URL."""
    token = generate_unsubscribe_token(contact_id)
    return f"{SUPABASE_URL}/functions/v1/unsubscribe?token={token}"


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>A personal year-end hello</title>
</head>
<body style="font-family: Georgia, 'Times New Roman', serif; max-width: 600px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #333;">
  <p>Hi {first_name},</p>

  <p>Two days after Thanksgiving, I watched a group of boys (some of whom had never seen the ocean) playing football on the beach at Half Moon Bay.</p>

  <p>Strangers on Friday. Teammates by Saturday.</p>

  <img src="https://ypqsrejrsocebnldicke.supabase.co/storage/v1/object/public/images/HMB_Football_email.jpg" width="560" alt="Kids playing football on Half Moon Bay beach" style="max-width: 100%; height: auto; margin: 20px 0; border-radius: 8px; display: block;">

  <p>Our three older girls jumped in. The adults stood back with coffee, watching pure joy unfold in a place that hasn't always felt accessible or welcoming to families like theirs.</p>

  <p>That moment is a pretty good summary of my 2025.</p>

  <p>Many of you know that late last year, after nearly a decade leading Google.org's Americas philanthropy, my role was eliminated. It hurt. And it clarified what I wanted to build next.</p>

  <p>What I didn't expect was the outpouring that followed: messages, calls, letters from colleagues and community leaders. It reminded me that the work is carried by people, not institutions. If you were one of those people: thank you.</p>

  <p>I chose not to take severance, which meant I had to move quickly. Here's what I built:</p>

  <p><strong>Outdoorithm Collective</strong> is a nonprofit I'm building with my wife Sally to help families reconnect with the land and each other. Half Moon Bay was one of our best trips yet: 35 people, cold air, warm fire, and a weekend I don't think any of us will forget. We also built <a href="https://outdoorithm.com">Outdoorithm.com</a>, a "Green Book" for public camping that helps families plan trips on their own.</p>

  <p><strong>Kindora</strong> is a public benefit corporation I'm building with my co-founder Karibu Nyaggah (we met at Harvard Business School). Kindora uses AI to help small nonprofits find aligned funders. I know what it feels like to have a program that matters, barely any money in the bank, and no time to prospect. We launched in August, grew to 215+ organizations through word-of-mouth, and just moved to paid plans. We welcomed our first outside investor and are exploring whether additional capital makes sense in 2026.</p>

  <p><strong>True Steele</strong> is my fractional Chief Impact Officer practice. I've spent the year helping organizations like Flourish Fund, a faith-driven fund investing in foster care, navigate the real tensions of systemic change: staying accountable to communities while meeting funder expectations.</p>

  <p>If I'm sitting with anything as the year closes, it's this: I used to think a corporate paycheck was the definition of security. This year taught me that certainty is always borrowed. Building has been exhilarating, and at times terrifying, especially while raising four kids.</p>

  <p>But I'd rather take the risk on something I'm building than on someone else's org chart.</p>

  <p><strong>Looking ahead:</strong> In 2026, we want to grow Outdoorithm in two ways: bring more families into the Collective, and build a small circle of supporters who want to make outdoor equity real, not just aspirational. And we're focused on scaling Kindora to reach the thousands of nonprofits who need it.</p>

  <p><strong>A small invitation:</strong> If any of this resonates, I'd love to hear from you. Just reply with one of the words below. I'll follow up personally.</p>

  <ul style="list-style: none; padding-left: 0;">
    <li style="margin-bottom: 10px;">• <strong>OUTDOOR</strong> if you want to hear how families can join, or you're open to a conversation about supporting our trips</li>
    <li style="margin-bottom: 10px;">• <strong>KINDORA</strong> if you want a demo, know a nonprofit that should try it, or are curious about investing as we grow</li>
    <li style="margin-bottom: 10px;">• <strong>HELLO</strong> if you just want to reconnect (I'd genuinely love to hear what you've been up to)</li>
  </ul>

  <p>Wishing you and yours a meaningful close to 2025.</p>

  <p>With gratitude,<br><br>Justin</p>

  <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

  <p style="font-size: 14px; color: #666;">
    <a href="https://kindora.co">Kindora</a> ·
    <a href="https://outdoorithmcollective.org">Outdoorithm Collective</a> ·
    <a href="https://outdoorithm.com">Outdoorithm.com</a> ·
    <a href="https://truesteele.com">True Steele</a> ·
    <a href="https://www.linkedin.com/in/justinrichardsteele/">LinkedIn</a>
  </p>

  <p style="font-size: 12px; color: #999; margin-top: 30px;">
    {physical_address}<br>
    <a href="{unsubscribe_url}" style="color: #999;">Unsubscribe</a>
  </p>
</body>
</html>"""


TEXT_TEMPLATE = """Hi {first_name},

Two days after Thanksgiving, I watched a group of boys (some of whom had never seen the ocean) playing football on the beach at Half Moon Bay.

Strangers on Friday. Teammates by Saturday.

[Photo: Kids playing football on Half Moon Bay beach]

Our three older girls jumped in. The adults stood back with coffee, watching pure joy unfold in a place that hasn't always felt accessible or welcoming to families like theirs.

That moment is a pretty good summary of my 2025.

Many of you know that late last year, after nearly a decade leading Google.org's Americas philanthropy, my role was eliminated. It hurt. And it clarified what I wanted to build next.

What I didn't expect was the outpouring that followed: messages, calls, letters from colleagues and community leaders. It reminded me that the work is carried by people, not institutions. If you were one of those people: thank you.

I chose not to take severance, which meant I had to move quickly. Here's what I built:

OUTDOORITHM COLLECTIVE is a nonprofit I'm building with my wife Sally to help families reconnect with the land and each other. Half Moon Bay was one of our best trips yet: 35 people, cold air, warm fire, and a weekend I don't think any of us will forget. We also built Outdoorithm.com, a "Green Book" for public camping that helps families plan trips on their own.

KINDORA is a public benefit corporation I'm building with my co-founder Karibu Nyaggah (we met at Harvard Business School). Kindora uses AI to help small nonprofits find aligned funders. I know what it feels like to have a program that matters, barely any money in the bank, and no time to prospect. We launched in August, grew to 215+ organizations through word-of-mouth, and just moved to paid plans. We welcomed our first outside investor and are exploring whether additional capital makes sense in 2026.

TRUE STEELE is my fractional Chief Impact Officer practice. I've spent the year helping organizations like Flourish Fund, a faith-driven fund investing in foster care, navigate the real tensions of systemic change: staying accountable to communities while meeting funder expectations.

If I'm sitting with anything as the year closes, it's this: I used to think a corporate paycheck was the definition of security. This year taught me that certainty is always borrowed. Building has been exhilarating, and at times terrifying, especially while raising four kids.

But I'd rather take the risk on something I'm building than on someone else's org chart.

LOOKING AHEAD: In 2026, we want to grow Outdoorithm in two ways: bring more families into the Collective, and build a small circle of supporters who want to make outdoor equity real, not just aspirational. And we're focused on scaling Kindora to reach the thousands of nonprofits who need it.

A SMALL INVITATION: If any of this resonates, I'd love to hear from you. Just reply with one of the words below. I'll follow up personally.

• OUTDOOR if you want to hear how families can join, or you're open to a conversation about supporting our trips
• KINDORA if you want a demo, know a nonprofit that should try it, or are curious about investing as we grow
• HELLO if you just want to reconnect (I'd genuinely love to hear what you've been up to)

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


def main():
    # Validate configuration
    if not RESEND_API_KEY:
        print("ERROR: RESEND_API_KEY not configured")
        sys.exit(1)

    if not UNSUBSCRIBE_SECRET:
        print("ERROR: UNSUBSCRIBE_SECRET not configured")
        sys.exit(1)

    if not SENDER_PHYSICAL_ADDRESS:
        print("ERROR: SENDER_PHYSICAL_ADDRESS not configured")
        sys.exit(1)

    resend.api_key = RESEND_API_KEY

    # Generate unsubscribe URL
    unsubscribe_url = get_unsubscribe_url(TEST_CONTACT_ID)

    print(f"Sending test email to: {TEST_EMAIL}")
    print(f"From: {FROM_NAME} <{FROM_EMAIL}>")
    print(f"Reply-To: {REPLY_TO}")
    print(f"Subject: {SUBJECT}")
    print()
    print(f"Unsubscribe URL (for testing):")
    print(f"  {unsubscribe_url}")
    print()

    # Prepare email content
    html_body = HTML_TEMPLATE.format(
        first_name=TEST_FIRST_NAME,
        physical_address=SENDER_PHYSICAL_ADDRESS,
        unsubscribe_url=unsubscribe_url
    )

    text_body = TEXT_TEMPLATE.format(
        first_name=TEST_FIRST_NAME,
        physical_address=SENDER_PHYSICAL_ADDRESS,
        unsubscribe_url=unsubscribe_url
    )

    # Send email
    try:
        response = resend.Emails.send({
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": [TEST_EMAIL],
            "reply_to": REPLY_TO,
            "subject": SUBJECT,
            "html": html_body,
            "text": text_body,
            "headers": {
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"
            }
        })

        print(f"SUCCESS! Email sent.")
        print(f"Resend Message ID: {response.get('id', 'N/A')}")
        print()
        print("Next steps:")
        print("1. Check justin@outdoorithm.com inbox for the email")
        print("2. Click the unsubscribe link to test the edge function")
        print("   (It will show an error since contact ID 99999 doesn't exist,")
        print("    but it confirms the edge function is working)")
        print()
        print("When ready to send to real contacts:")
        print("  python scripts/email_campaigns/send_year_end_email.py --limit 5")

    except Exception as e:
        print(f"ERROR sending email: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
