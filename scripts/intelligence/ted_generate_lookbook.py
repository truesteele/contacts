#!/usr/bin/env python3
"""
TED 2026 — Generate Outdoorithm Networking Brief HTML Lookbook for Sally Steele

Assembles all enrichment data (TED profiles, LinkedIn profiles, LinkedIn posts,
GPT triage scores, warm lead matching) into a single-file HTML lookbook.

Usage:
  python scripts/intelligence/ted_generate_lookbook.py
"""

import json
import html
import re
from datetime import datetime
from ted_deep_writeups import DEEP_WRITEUPS

# ── Load Data ──────────────────────────────────────────────────────────

shortlist = json.load(open('/tmp/ted_shortlist.json'))
try:
    posts_raw = json.load(open('/tmp/ted_linkedin_posts.json'))
except FileNotFoundError:
    posts_raw = []

# Group posts by LinkedIn username
posts_by_username = {}
for p in posts_raw:
    author = p.get('author', {})
    if isinstance(author, dict):
        username = author.get('publicIdentifier', '')
    else:
        username = ''
    if not username:
        # Try extracting from linkedinUrl
        url = p.get('linkedinUrl', '')
        if '/in/' in url:
            username = url.split('/in/')[-1].strip('/').split('?')[0].lower()
    if username:
        posts_by_username.setdefault(username.lower(), []).append(p)

print(f"Posts grouped by {len(posts_by_username)} usernames")
for u, pp in posts_by_username.items():
    print(f"  {u}: {len(pp)} posts")

# Split tiers
tier1 = sorted([s for s in shortlist if s.get('tier') == 1], key=lambda x: -x['boosted_score'])
tier2 = sorted([s for s in shortlist if s.get('tier') == 2], key=lambda x: -x['boosted_score'])
tier3 = sorted([s for s in shortlist if s.get('tier') == 3], key=lambda x: -x['boosted_score'])

print(f"\nTier 1: {len(tier1)}, Tier 2: {len(tier2)}, Tier 3: {len(tier3)}")

# ── Helper Functions ───────────────────────────────────────────────────

def h(text):
    """HTML escape."""
    if not text:
        return ''
    return html.escape(str(text))

def get_initials(person):
    fn = person.get('ted_firstname', '')
    ln = person.get('ted_lastname', '')
    return (fn[0] if fn else '') + (ln[0] if ln else '')

def get_photo_html(person, size=56):
    """Get photo HTML — use LinkedIn photo if available, then TED, then initials."""
    li_photo = person.get('li_photo', '')
    ted_photo = person.get('ted_photo', '')

    photo_url = ''
    if li_photo:
        if isinstance(li_photo, dict):
            photo_url = li_photo.get('url', '')
        elif isinstance(li_photo, str) and li_photo.startswith('http'):
            photo_url = li_photo
    if not photo_url and ted_photo and ted_photo.startswith('http'):
        photo_url = ted_photo

    if photo_url:
        return f'<img src="{h(photo_url)}" alt="{h(person.get("ted_name",""))}" style="width:{size}px;height:{size}px;border-radius:50%;object-fit:cover;flex-shrink:0" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">\n    <div class="avatar-placeholder" style="display:none">{h(get_initials(person))}</div>'
    return f'<div class="avatar-placeholder">{h(get_initials(person))}</div>'

def format_followers(count):
    if not count:
        return ''
    count = int(count)
    if count >= 1000:
        return f"{count/1000:.1f}K"
    return str(count)

def get_education_str(person):
    edu = person.get('li_education', [])
    if not edu or not isinstance(edu, list):
        return ''
    schools = []
    for e in edu[:3]:
        if isinstance(e, dict):
            school = e.get('schoolName', '')
            if school:
                schools.append(school)
    return ' | '.join(schools)

def get_experience_str(person):
    exp = person.get('li_experience', [])
    if not exp or not isinstance(exp, list):
        return ''
    items = []
    for e in exp[:3]:
        if isinstance(e, dict):
            pos = e.get('position', '')
            company = e.get('companyName', '')
            if pos and company:
                items.append(f"{pos} at {company}")
            elif company:
                items.append(company)
    return ' → '.join(items)

def get_volunteering_str(person):
    vol = person.get('li_volunteering', [])
    if not vol or not isinstance(vol, list):
        return ''
    items = []
    for v in vol[:3]:
        if isinstance(v, dict):
            role = v.get('role', v.get('position', ''))
            org = v.get('companyName', v.get('company', ''))
            if role and org:
                items.append(f"{role} at {org}")
            elif org:
                items.append(org)
    return ', '.join(items)

def get_causes_str(person):
    causes = person.get('li_causes', [])
    if not causes or not isinstance(causes, list):
        return ''
    return ', '.join(causes[:5])

def get_posts_for_person(person):
    username = person.get('ted_linkedin', '').lower()
    if not username:
        return []
    return posts_by_username.get(username, [])

def format_post_text(text, max_len=200):
    if not text:
        return ''
    text = text.replace('\n', ' ').strip()
    if len(text) > max_len:
        return text[:max_len] + '...'
    return text

def partnership_badge(ptype):
    colors = {
        'funding': ('background:#dcfce7;color:#166534;', 'Funding'),
        'media_storytelling': ('background:#fef3c7;color:#92400e;', 'Media & Storytelling'),
        'programmatic': ('background:#dbeafe;color:#1e40af;', 'Programmatic'),
        'multiple': ('background:#fae8ff;color:#86198f;', 'Multiple'),
        'unlikely': ('background:#f3f4f6;color:#6b7280;', 'Unlikely'),
    }
    style, label = colors.get(ptype, ('background:#f3f4f6;color:#6b7280;', ptype))
    return f'<span class="tag" style="{style}">{h(label)}</span>'

def partnership_types_badges(person):
    ptypes = person.get('partnership_types', [])
    if not ptypes:
        ptypes = [person.get('partnership_type', '')]
    badges = []
    for pt in ptypes:
        if pt:
            badges.append(partnership_badge(pt))
    return ' '.join(badges)

def warm_lead_badges(person):
    badges = []
    if person.get('justin_connection'):
        badges.append('<span class="tier-badge badge-relationship">Justin\'s Connection</span>')
    if person.get('sally_connection'):
        badges.append('<span class="tier-badge" style="background:#dcfce7;color:#166534;font-size:9px;margin-left:4px">Sally\'s Connection</span>')
    return ' '.join(badges)

def relationship_summary(person):
    parts = []
    closeness = person.get('db_closeness', '')
    momentum = person.get('db_momentum', '')
    last_date = person.get('db_last_date', '')
    donor_tier = person.get('db_donor_tier', '')
    outdoorithm_fit = person.get('db_outdoorithm_fit', '')

    if closeness and closeness != 'no_history':
        parts.append(f"<strong>Closeness:</strong> {h(closeness)}")
    if momentum and momentum != 'inactive':
        parts.append(f"<strong>Momentum:</strong> {h(momentum)}")
    if last_date:
        parts.append(f"<strong>Last contact:</strong> {h(last_date)}")
    if donor_tier:
        parts.append(f"<strong>Donor tier:</strong> {h(donor_tier)}")
    if outdoorithm_fit:
        parts.append(f"<strong>Outdoorithm fit:</strong> {h(outdoorithm_fit)}")

    return ' · '.join(parts)

# ── Build Bio / Background ────────────────────────────────────────────

def build_background(person):
    """Build a background paragraph from available data."""
    parts = []

    # Title + org
    title = person.get('ted_title', '')
    org = person.get('ted_org', '')
    if title and org:
        parts.append(f"{title} at {org}.")
    elif org:
        parts.append(f"At {org}.")

    # TED bio
    about = person.get('ted_about', '')
    if about:
        parts.append(about[:300])

    # LinkedIn about (if different / more detailed)
    li_about = person.get('li_about', '')
    if li_about and li_about != about and len(li_about) > len(about or ''):
        # Add only the LinkedIn about if it's richer
        if not about or li_about[:50] != about[:50]:
            parts.append(li_about[:300])

    # DB summary as fallback
    if not about and not li_about:
        db_summary = person.get('db_summary', '')
        if db_summary:
            parts.append(db_summary[:300])

    return ' '.join(parts)

# ── Card Generators ────────────────────────────────────────────────────

def generate_full_card(person, tier_num):
    tier_class = f"tier{tier_num}"
    tier_label = {1: 'Must-Connect', 2: 'High Value', 3: 'Worth a Chat'}[tier_num]
    badge_class = {1: 'badge-tier1', 2: 'badge-tier2', 3: 'badge-tier3'}[tier_num]
    co_class = {1: 'tier1-co', 2: 'tier2-co', 3: ''}[tier_num]

    name = person.get('ted_name', '')
    org = person.get('ted_org', '')
    title = person.get('ted_title', '')
    city = person.get('ted_city', '')
    country = person.get('ted_country', '')
    location = f"{city}, {country}" if city and country else city or country or ''
    followers = format_followers(person.get('li_followers', 0))
    education = get_education_str(person)
    is_speaker = person.get('ted_is_speaker', False)
    is_fellow = person.get('ted_is_fellow', False)

    # Meta row
    meta_items = []
    if followers:
        meta_items.append(f'<span>followers {followers}</span>')
    if location:
        meta_items.append(f'<span>{h(location)}</span>')
    if education:
        meta_items.append(f'<span>{h(education)}</span>')

    role_tags = []
    if is_speaker:
        role_tags.append('TED Speaker')
    if is_fellow:
        role_tags.append('TED Fellow')
    role_str = ' · '.join(role_tags)

    title_line = title
    if role_str:
        title_line = f"{title} · {role_str}" if title else role_str

    # Background
    background = build_background(person)

    # Relationship
    rel = relationship_summary(person)

    # Outdoorithm connection — use deep write-up if available
    deep = DEEP_WRITEUPS.get(name)
    reasoning = person.get('reasoning', '')
    key_signal = person.get('key_signal', '')
    deep_vision = deep[0] if deep else ''
    ted_app_message = deep[1] if deep else ''

    # Conversation hook
    convo_hook = person.get('conversation_hook', '')

    # Posts
    person_posts = get_posts_for_person(person)
    recent_posts = []
    for pp in person_posts[:3]:
        text = pp.get('content', pp.get('text', ''))
        if text:
            recent_posts.append(format_post_text(text, 180))

    # Volunteering
    vol_str = get_volunteering_str(person)
    causes_str = get_causes_str(person)

    # TED fields
    idea = person.get('ted_idea', '')
    passion = person.get('ted_passion', '')
    ask_me = person.get('ted_ask_me_about', '')

    safe_id = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())

    card_html = f'''<div class="card" id="card-{safe_id}" data-contact="{h(name)}">
  <div class="card-top">
    {get_photo_html(person)}
    <div>
      <div class="card-name">{h(name)} <span class="tier-badge {badge_class}">{tier_label}</span> {warm_lead_badges(person)}
        <span class="outreach-toggle" data-contact="{h(name)}" onclick="toggleOutreach(this)"><span class="uncheck">&#9744;</span><span class="check">&#9745;</span> Reached out</span>
      </div>
      <div class="card-company {co_class}">{h(org)}</div>
      <div class="card-title">{h(title_line)}</div>
    </div>
  </div>
  <div class="meta-row">
    {"".join(f"    {item}" for item in meta_items)}
  </div>'''

    if background:
        card_html += f'''
  <div class="section-label">Background</div>
  <div class="bio">{h(background)}</div>'''

    if idea:
        card_html += f'''
  <div style="font-size:13px;color:#166534;margin:4px 0"><strong>Idea Worth Spreading:</strong> {h(idea)}</div>'''

    if passion:
        card_html += f'''
  <div style="font-size:13px;color:var(--text-muted);margin:4px 0"><strong>Passions:</strong> {h(passion)}</div>'''

    if ask_me:
        card_html += f'''
  <div style="font-size:13px;color:var(--text-muted);margin:4px 0"><strong>Ask me about:</strong> {h(ask_me)}</div>'''

    if vol_str:
        card_html += f'''
  <div style="font-size:13px;color:var(--text-muted);margin:4px 0"><strong>Volunteer:</strong> {h(vol_str)}</div>'''

    if causes_str:
        card_html += f'''
  <div style="font-size:13px;color:var(--text-muted);margin:4px 0"><strong>Causes:</strong> {h(causes_str)}</div>'''

    # Relationship box (only if we have data)
    if rel:
        card_html += f'''
  <div class="relationship-box">
    <strong>YOUR RELATIONSHIP</strong><br>
    {rel}
  </div>'''

    # Outdoorithm connection box — deep vision for Tier 1, triage for others
    if deep_vision:
        # Convert paragraphs to HTML
        vision_paragraphs = [p.strip() for p in deep_vision.strip().split('\n\n') if p.strip()]
        # Process bold: find **text** and replace with <strong>text</strong>
        vision_parts = []
        for p in vision_paragraphs:
            # Replace **text** with <strong>text</strong>
            formatted = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', p.replace('\n', ' '))
            vision_parts.append(h(formatted).replace('&lt;strong&gt;', '<strong>').replace('&lt;/strong&gt;', '</strong>'))
        vision_html = '</p><p style="margin-top:8px">'.join(vision_parts)
        card_html += f'''
  <div class="highlight-box" style="border-left-width:4px">
    <strong>OUTDOORITHM PARTNERSHIP VISION</strong>
    <p style="margin-top:8px">{vision_html}</p>
  </div>'''
    elif reasoning:
        oc_text = h(reasoning)
        if key_signal:
            oc_text += f'<br><strong>Key signal:</strong> {h(key_signal)}'
        card_html += f'''
  <div class="highlight-box">
    <strong>OUTDOORITHM CONNECTION</strong><br>
    {oc_text}
  </div>'''

    # TED App Message (for contacts with deep write-ups)
    if ted_app_message:
        card_html += f'''
  <div class="ted-message-box">
    <strong>DRAFT TED APP MESSAGE</strong>
    <div class="message-bubble">{h(ted_app_message.strip())}</div>
    <div style="font-size:11px;color:#94a3b8;margin-top:4px;font-style:italic">Tap to copy. Edit to make it yours.</div>
  </div>'''

    # Justin's context box (only for Justin's connections)
    if person.get('justin_connection'):
        card_html += f'''
  <div class="justin-context-box">
    <strong>JUSTIN'S CONTEXT</strong>
    <textarea data-contact="{h(name)}" placeholder="Add relationship context, notes, or history..." oninput="saveContext(this)"></textarea>
    <div class="char-count"><span class="ctx-count">0</span> chars</div>
  </div>'''

    # Conversation hook (skip if we have a deep write-up — the message replaces this)
    if convo_hook and not deep_vision:
        card_html += f'''
  <div class="convo-starters">
    <strong>CONVERSATION STARTER</strong>
    <ul>
      <li>{h(convo_hook)}</li>
    </ul>
  </div>'''

    # Recent posts
    if recent_posts:
        posts_html = '\n'.join(f'      <li style="margin-bottom:8px">{h(p)}</li>' for p in recent_posts)
        card_html += f'''
  <div style="background:#f8fafc;border-left:3px solid #94a3b8;border-radius:0 8px 8px 0;padding:10px 12px;margin:10px 0;font-size:12px">
    <strong style="color:#475569">RECENT LINKEDIN POSTS</strong>
    <ul style="margin:4px 0 0 16px">
{posts_html}
    </ul>
  </div>'''

    # Tags
    tags = [partnership_types_badges(person)]
    score = person.get('relevance_score', 0)
    tags.append(f'<span class="tag">Score: {score}</span>')
    if person.get('db_contact_id'):
        tags.append(f'<span class="tag">DB #{person["db_contact_id"]}</span>')
    if person_posts:
        tags.append(f'<span class="tag">{len(person_posts)} posts</span>')

    card_html += f'''
  <div class="tags">
    {" ".join(tags)}
  </div>'''

    # LinkedIn link
    linkedin = person.get('ted_linkedin', '')
    if linkedin:
        card_html += f'''
  <a href="https://www.linkedin.com/in/{h(linkedin)}" target="_blank" class="linkedin-link">View LinkedIn Profile &rarr;</a>'''

    # TED Connect link
    ted_id = person.get('ted_id', '')
    if ted_id:
        card_html += f'''
  <a href="https://connect.ted.com/attendees/{h(str(ted_id))}" target="_blank" class="linkedin-link" style="margin-left:12px;color:#e04040">View TED Connect &rarr;</a>'''

    card_html += '\n</div>'
    return card_html


def generate_compact_card(person):
    name = person.get('ted_name', '')
    org = person.get('ted_org', '')
    title = person.get('ted_title', '')
    followers = format_followers(person.get('li_followers', 0))
    reasoning = person.get('reasoning', '')
    convo_hook = person.get('conversation_hook', '')

    compact_bio = f"{h(title)} at {h(org)}" if title and org else h(title or org)
    if followers:
        compact_bio += f" · followers {followers}"

    linkedin = person.get('ted_linkedin', '')
    ted_id = person.get('ted_id', '')

    card_html = f'''<div class="compact-card">
  <div class="card-top">
    {get_photo_html(person, 48)}
    <div>
      <div class="card-name">{h(name)} <span class="tier-badge badge-tier3">Worth a Chat</span> {warm_lead_badges(person)}</div>
      <div class="card-company">{h(org)}</div>
      <div class="card-title">{h(title)}</div>
    </div>
  </div>
  <div class="compact-bio">{compact_bio}</div>'''

    if reasoning:
        card_html += f'''
  <div style="font-size:12px;color:var(--text-muted);margin:4px 0">{h(reasoning[:150])}</div>'''

    if convo_hook:
        card_html += f'''
  <div style="font-size:12px;color:#166534;margin:4px 0"><strong>Hook:</strong> {h(convo_hook[:150])}</div>'''

    # Partnership type + score
    card_html += f'''
  <div class="tags" style="margin-top:4px">
    {partnership_types_badges(person)}
    <span class="tag">Score: {person.get("relevance_score", 0)}</span>
  </div>'''

    links = []
    if linkedin:
        links.append(f'<a href="https://www.linkedin.com/in/{h(linkedin)}" target="_blank" class="linkedin-link">LinkedIn &rarr;</a>')
    if ted_id:
        links.append(f'<a href="https://connect.ted.com/attendees/{h(str(ted_id))}" target="_blank" class="linkedin-link" style="color:#e04040;margin-left:8px">TED Connect &rarr;</a>')
    if links:
        card_html += '\n  ' + ' '.join(links)

    card_html += '\n</div>'
    return card_html


def generate_quick_ref_row(person, tier_num):
    tier_labels = {1: ('dot-t1', 'Must'), 2: ('dot-t2', 'High'), 3: ('dot-t3', 'Chat')}
    dot_class, label = tier_labels.get(tier_num, ('', ''))

    name = person.get('ted_name', '')
    org = person.get('ted_org', '')
    ptype = person.get('partnership_type', '')
    score = person.get('relevance_score', 0)
    followers = format_followers(person.get('li_followers', 0))
    linkedin = person.get('ted_linkedin', '')

    li_cell = f'<a href="https://www.linkedin.com/in/{h(linkedin)}" target="_blank">Profile</a>' if linkedin else '<em>No LinkedIn</em>'
    warm = ''
    if person.get('justin_connection'):
        warm += 'J'
    if person.get('sally_connection'):
        warm += 'S'

    return f'<tr><td><span class="tier-dot {dot_class}"></span>{label}</td><td>{h(name)}</td><td>{h(org)}</td><td>{h(ptype.replace("_"," ").title())}</td><td>{score}</td><td>{followers or "-"}</td><td>{warm or "-"}</td><td>{li_cell}</td></tr>'


# ── Stats ──────────────────────────────────────────────────────────────

total_shortlisted = len(tier1) + len(tier2) + len(tier3)
warm_count = sum(1 for s in shortlist if s.get('justin_connection') or s.get('sally_connection'))
funding_count = sum(1 for s in tier1 + tier2 if 'funding' in (s.get('partnership_types', []) + [s.get('partnership_type','')]))
media_count = sum(1 for s in tier1 + tier2 if 'media_storytelling' in (s.get('partnership_types', []) + [s.get('partnership_type','')]))
prog_count = sum(1 for s in tier1 + tier2 if 'programmatic' in (s.get('partnership_types', []) + [s.get('partnership_type','')]))

# ── Generate HTML ──────────────────────────────────────────────────────

html_parts = []

# Head
html_parts.append(f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TED 2026 — Outdoorithm Networking Brief</title>
<style>:root {{
    --oc-green: #166534;
    --oc-green-light: #166534;
    --oc-light: #f0fdf4;
    --tier1: #166534;
    --tier2: #92400e;
    --tier3: #6b7280;
    --bg: #fafaf5;
    --card-bg: #ffffff;
    --text: #1e293b;
    --text-muted: #64748b;
    --border: #e2e8f0;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.6; padding: 0 0 60px 0;
  }}
  .header {{
    background: linear-gradient(135deg, #166534 0%, #365314 50%, #1a2e05 100%);
    color: white; padding: 32px 20px; text-align: center;
  }}
  .header h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; }}
  .header .subtitle {{ font-size: 14px; opacity: 0.9; }}
  .header .date {{ font-size: 13px; opacity: 0.75; margin-top: 8px; }}
  .header .stats {{ font-size: 12px; opacity: 0.7; margin-top: 4px; }}
  .event-bar {{
    background: #f0fdf4; border-bottom: 1px solid #86efac;
    padding: 12px 20px; font-size: 13px; color: #166534;
  }}
  .event-bar strong {{ color: #14532d; }}
  .section-header {{
    padding: 20px 20px 8px; font-size: 11px; font-weight: 700;
    letter-spacing: 1.5px; text-transform: uppercase;
  }}
  .tier1-header {{ color: var(--tier1); }}
  .tier2-header {{ color: var(--tier2); }}
  .tier3-header {{ color: var(--tier3); }}
  .section-count {{ font-weight: 400; opacity: 0.7; text-transform: none; letter-spacing: normal; }}
  .card {{
    background: var(--card-bg); border: 1px solid var(--border);
    border-radius: 12px; margin: 8px 16px; padding: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }}
  .card-top {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }}
  .avatar-placeholder {{
    width: 56px; height: 56px; border-radius: 50%;
    background: linear-gradient(135deg, #166534, #365314);
    display: flex; align-items: center; justify-content: center;
    color: white; font-weight: 700; font-size: 20px; flex-shrink: 0;
  }}
  .card-name {{ font-size: 17px; font-weight: 700; }}
  .card-title {{ font-size: 13px; color: var(--text-muted); }}
  .card-company {{ font-size: 14px; font-weight: 600; }}
  .card-company.tier1-co {{ color: var(--tier1); }}
  .card-company.tier2-co {{ color: var(--tier2); }}
  .tier-badge {{
    display: inline-block; font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 10px; letter-spacing: 0.5px;
    text-transform: uppercase; margin-left: 8px; vertical-align: middle;
  }}
  .badge-tier1 {{ background: #dcfce7; color: #166534; }}
  .badge-tier2 {{ background: #fef3c7; color: #92400e; }}
  .badge-tier3 {{ background: #f3f4f6; color: #4b5563; }}
  .badge-relationship {{ background: #fef3c7; color: #92400e; font-size: 9px; margin-left: 4px; }}
  .meta-row {{
    display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 10px;
    font-size: 12px; color: var(--text-muted);
  }}
  .meta-row span {{ white-space: nowrap; }}
  .section-label {{
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.8px; color: var(--text-muted); margin: 10px 0 4px;
  }}
  .bio {{ font-size: 14px; margin-bottom: 8px; }}
  .highlight-box {{
    background: #f0fdf4; border-left: 3px solid #22c55e;
    border-radius: 0 8px 8px 0; padding: 10px 12px; margin: 10px 0; font-size: 13px;
  }}
  .highlight-box strong {{ color: #166534; }}
  .relationship-box {{
    background: #fefce8; border-left: 3px solid #eab308;
    border-radius: 0 8px 8px 0; padding: 10px 12px; margin: 10px 0; font-size: 13px;
  }}
  .relationship-box strong {{ color: #a16207; }}
  .convo-starters {{
    background: #eff6ff; border-left: 3px solid #3b82f6;
    border-radius: 0 8px 8px 0; padding: 10px 12px; margin: 10px 0; font-size: 13px;
  }}
  .convo-starters strong {{ color: #1d4ed8; }}
  .convo-starters ul {{ margin: 4px 0 0 16px; }}
  .convo-starters li {{ margin-bottom: 6px; }}
  .tags {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }}
  .tag {{ font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #f1f5f9; color: #475569; }}
  .linkedin-link {{
    display: inline-block; margin-top: 8px; font-size: 13px;
    color: #0077b5; text-decoration: none; font-weight: 600;
  }}
  .strategy-bar {{
    background: #14532d; color: white; padding: 16px 20px;
    margin: 16px; border-radius: 12px; font-size: 13px; line-height: 1.7;
  }}
  .strategy-bar h3 {{ font-size: 15px; margin-bottom: 8px; }}
  .strategy-bar ul {{ margin-left: 16px; }}
  .strategy-bar li {{ margin-bottom: 4px; }}
  .compact-card {{
    background: var(--card-bg); border: 1px solid var(--border);
    border-radius: 12px; margin: 8px 16px; padding: 14px;
  }}
  .compact-card .card-top {{ margin-bottom: 8px; }}
  .compact-bio {{ font-size: 13px; color: var(--text-muted); }}
  .quick-ref {{ margin: 16px; font-size: 12px; overflow-x: auto; }}
  .quick-ref table {{ width: 100%; border-collapse: collapse; min-width: 600px; }}
  .quick-ref th, .quick-ref td {{ padding: 6px 8px; border-bottom: 1px solid var(--border); text-align: left; }}
  .quick-ref th {{
    background: #f1f5f9; font-weight: 700; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.5px; position: sticky; top: 0;
  }}
  .quick-ref a {{ color: #0077b5; text-decoration: none; }}
  .ted-message-box {{
    background: #faf5ff; border-left: 3px solid #a855f7;
    border-radius: 0 8px 8px 0; padding: 10px 12px; margin: 10px 0; font-size: 13px;
  }}
  .ted-message-box strong {{ color: #7c3aed; }}
  .message-bubble {{
    background: #f3e8ff; border-radius: 12px; padding: 12px 14px;
    margin-top: 8px; font-size: 14px; line-height: 1.5; color: #1e1b4b;
    cursor: pointer; position: relative;
  }}
  .message-bubble:active {{ background: #e9d5ff; }}
  .tier-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }}
  .dot-t1 {{ background: var(--tier1); }}
  .dot-t2 {{ background: var(--tier2); }}
  .dot-t3 {{ background: var(--tier3); }}
  .card.reached-out {{ border-left: 4px solid #22c55e; }}
  .outreach-toggle {{
    display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
    font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 10px;
    border: 1.5px solid #d1d5db; color: #6b7280; margin-left: 8px;
    vertical-align: middle; user-select: none; transition: all 0.15s;
  }}
  .outreach-toggle.active {{
    background: #dcfce7; border-color: #22c55e; color: #166534;
  }}
  .outreach-toggle .check {{ display: none; }}
  .outreach-toggle.active .check {{ display: inline; }}
  .outreach-toggle.active .uncheck {{ display: none; }}
  .justin-context-box {{
    background: #fffbeb; border-left: 3px solid #f59e0b;
    border-radius: 0 8px 8px 0; padding: 10px 12px; margin: 10px 0; font-size: 13px;
  }}
  .justin-context-box strong {{ color: #b45309; }}
  .justin-context-box textarea {{
    width: 100%; min-height: 48px; max-height: 200px; border: 1px solid #e5e7eb;
    border-radius: 6px; padding: 8px 10px; font-size: 13px; font-family: inherit;
    line-height: 1.5; resize: vertical; margin-top: 6px; background: #fffef7;
    color: var(--text);
  }}
  .justin-context-box textarea:focus {{ outline: none; border-color: #f59e0b; }}
  .justin-context-box .char-count {{
    font-size: 10px; color: #9ca3af; text-align: right; margin-top: 2px;
  }}
  .outreach-counter {{
    display: inline-block; background: rgba(255,255,255,0.15);
    padding: 4px 12px; border-radius: 8px; font-size: 12px; margin-top: 6px;
  }}
  /* Search bar */
  .search-container {{
    padding: 16px; background: #f8fafc; border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 100;
  }}
  .search-row {{
    display: flex; gap: 8px; max-width: 700px; margin: 0 auto;
  }}
  .search-input {{
    flex: 1; padding: 10px 14px; font-size: 15px; border: 2px solid #e2e8f0;
    border-radius: 10px; outline: none; font-family: inherit;
  }}
  .search-input:focus {{ border-color: #166534; }}
  .search-input::placeholder {{ color: #94a3b8; }}
  .btn-add-new {{
    padding: 10px 16px; background: #166534; color: white; border: none;
    border-radius: 10px; font-size: 13px; font-weight: 600; cursor: pointer;
    white-space: nowrap;
  }}
  .btn-add-new:hover {{ background: #14532d; }}
  .search-results {{
    max-width: 700px; margin: 8px auto 0; background: white;
    border: 1px solid var(--border); border-radius: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1); display: none;
    max-height: 400px; overflow-y: auto;
  }}
  .search-results.active {{ display: block; }}
  .search-result {{
    padding: 12px 14px; border-bottom: 1px solid #f1f5f9;
    display: flex; justify-content: space-between; align-items: center;
    gap: 12px;
  }}
  .search-result:last-child {{ border-bottom: none; }}
  .search-result:hover {{ background: #f0fdf4; }}
  .sr-info {{ flex: 1; min-width: 0; }}
  .sr-name {{ font-weight: 700; font-size: 14px; }}
  .sr-meta {{ font-size: 12px; color: var(--text-muted); margin-top: 2px; }}
  .sr-reasoning {{ font-size: 12px; color: #475569; margin-top: 4px; }}
  .sr-score {{
    display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 8px;
    border-radius: 10px; background: #dcfce7; color: #166534; margin-right: 6px;
  }}
  .btn-pin {{
    padding: 6px 14px; background: #166534; color: white; border: none;
    border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer;
    white-space: nowrap; flex-shrink: 0;
  }}
  .btn-pin:hover {{ background: #14532d; }}
  .btn-pin.already {{ background: #e2e8f0; color: #64748b; cursor: default; }}
  .search-empty {{
    padding: 16px; text-align: center; color: var(--text-muted); font-size: 13px;
  }}
  /* Sally's Picks section */
  .picks-section {{ display: none; }}
  .picks-section.active {{ display: block; }}
  .picks-header {{
    color: #7c3aed; padding: 20px 20px 8px; font-size: 11px; font-weight: 700;
    letter-spacing: 1.5px; text-transform: uppercase;
  }}
  .picks-header .section-count {{ font-weight: 400; opacity: 0.7; text-transform: none; letter-spacing: normal; }}
  .badge-pick {{ background: #f3e8ff; color: #7c3aed; }}
  .btn-remove {{
    font-size: 11px; color: #ef4444; cursor: pointer; border: none;
    background: none; font-weight: 600; padding: 2px 6px; margin-left: 8px;
  }}
  .btn-remove:hover {{ text-decoration: underline; }}
  .pick-notes textarea {{
    width: 100%; min-height: 40px; max-height: 150px; border: 1px solid #e5e7eb;
    border-radius: 6px; padding: 8px 10px; font-size: 13px; font-family: inherit;
    line-height: 1.5; resize: vertical; margin-top: 6px; background: #faf5ff;
  }}
  .pick-notes textarea:focus {{ outline: none; border-color: #a855f7; }}
  /* Modal */
  .modal-overlay {{
    display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5); z-index: 200; align-items: center; justify-content: center;
  }}
  .modal-overlay.active {{ display: flex; }}
  .modal {{
    background: white; border-radius: 16px; padding: 24px; max-width: 480px;
    width: 90%; box-shadow: 0 8px 32px rgba(0,0,0,0.2);
  }}
  .modal h3 {{ font-size: 17px; margin-bottom: 12px; }}
  .modal input {{
    width: 100%; padding: 10px 14px; font-size: 14px; border: 2px solid #e2e8f0;
    border-radius: 10px; outline: none; font-family: inherit; margin-bottom: 12px;
  }}
  .modal input:focus {{ border-color: #166534; }}
  .modal-btns {{ display: flex; gap: 8px; justify-content: flex-end; }}
  .modal-btns button {{
    padding: 8px 18px; border-radius: 8px; font-size: 13px; font-weight: 600;
    cursor: pointer; border: none;
  }}
  .btn-cancel {{ background: #f1f5f9; color: #475569; }}
  .btn-enrich {{ background: #166534; color: white; }}
  .btn-enrich:disabled {{ background: #94a3b8; cursor: not-allowed; }}
  .enrich-status {{
    font-size: 13px; color: #166534; text-align: center; padding: 8px;
    display: none;
  }}
  .enrich-status.active {{ display: block; }}</style>
</head>
<body>
''')

# Header
html_parts.append(f'''<div class="header">
  <h1>TED 2026 — Outdoorithm Networking Brief</h1>
  <div class="subtitle">Prepared for Sally Steele, Co-Founder & CEO</div>
  <div class="date">April 14-18 | Vancouver, BC</div>
  <div class="stats">{len(shortlist):,} attendees triaged · {len(tier1)} must-connect · {len(tier2)} high value · {len(tier3)} worth a chat · {warm_count} warm leads</div>
  <div class="outreach-counter" id="outreach-counter">Sally's outreach: <strong><span id="outreach-count">0</span>/{len(tier1) + len(tier2)}</strong> contacted</div>
</div>
''')

# Event context bar
html_parts.append(f'''<div class="event-bar">
  <strong>You are:</strong> Co-Founder & CEO of Outdoorithm Collective, attending as a TED attendee<br>
  <strong>Justin is:</strong> Your co-founder. His 1st-degree LinkedIn connections are flagged throughout.<br>
  <strong>What we do:</strong> 48-hour guided group camping trips where families across class and race lines build authentic connections in nature
</div>
''')

# Strategy bar
html_parts.append('''<div class="strategy-bar">
  <h3>Outdoorithm Networking Strategy</h3>
  <p style="margin-bottom:8px;opacity:0.9"><strong>Pitch line:</strong> "Outdoorithm Collective transforms public lands into spaces of belonging. We run 48-hour camping trips where families across class and race lines form the cross-class friendships that research shows are the #1 predictor of economic mobility."</p>
  <p style="margin-bottom:8px;opacity:0.8"><strong>Your story angles:</strong> CEO &amp; Co-Founder of Outdoorithm Collective · Former Co-Executive Director, City Hope SF ($1.9M budget) · Ordained faith leader · Oakland mom of four · 107 family camping trips · 94% BIPOC participants · Come Alive 2026 campaign ($120K goal)</p>
  <ul>
    <li><strong>For funders:</strong> "We&#x27;re raising $120K for Come Alive 2026 to serve 100 new families. Every $1,200 sends a family camping. We have a 94% BIPOC participation rate and 100% retention."</li>
    <li><strong>For media/storytelling partners:</strong> "Our families&#x27; stories are incredible. Parents who&#x27;ve never slept outside watching their kids fall in love with nature. We&#x27;re looking for filmmakers and storytellers to help us share this."</li>
    <li><strong>For programmatic partners:</strong> "We need gear partners, public lands allies, and community orgs who want to bring their families on our trips. We&#x27;re scaling from California to national."</li>
    <li><strong>Key concept to drop:</strong> john powell&#x27;s "bridging" framework. Our camping trips create the exact cross-class, cross-race social ties that bridge divided communities.</li>
  </ul>
</div>
''')

# Search bar
html_parts.append('''<div class="search-container">
  <div class="search-row">
    <input type="text" class="search-input" id="search-input" placeholder="Search all 1,883 TED attendees by name, org, or title..." autocomplete="off">
    <button class="btn-add-new" onclick="openAddModal()">+ Add New</button>
  </div>
  <div class="search-results" id="search-results"></div>
</div>
''')

# Sally's Picks section (dynamically populated from Supabase)
html_parts.append('''<div class="picks-section" id="picks-section">
  <div class="picks-header">SALLY'S PICKS <span class="section-count" id="picks-count">(0)</span></div>
  <div id="picks-cards"></div>
</div>
''')

# Add New Person modal
html_parts.append('''<div class="modal-overlay" id="add-modal">
  <div class="modal">
    <h3>Add someone new</h3>
    <p style="font-size:13px;color:#64748b;margin-bottom:12px">Paste their LinkedIn URL. We'll scrape the profile and score them for Outdoorithm fit (~30 seconds).</p>
    <input type="text" id="linkedin-url-input" placeholder="https://www.linkedin.com/in/username">
    <div class="enrich-status" id="enrich-status">Scraping profile and scoring...</div>
    <div class="modal-btns">
      <button class="btn-cancel" onclick="closeAddModal()">Cancel</button>
      <button class="btn-enrich" id="btn-enrich" onclick="enrichAndAdd()">Enrich + Add</button>
    </div>
  </div>
</div>
''')

# Tier 1
html_parts.append(f'<div class="section-header tier1-header">TIER 1 — MUST-CONNECT <span class="section-count">({len(tier1)} people)</span></div>')
for person in tier1:
    html_parts.append(generate_full_card(person, 1))

# Tier 2
html_parts.append(f'\n<div class="section-header tier2-header">TIER 2 — HIGH VALUE <span class="section-count">({len(tier2)} people)</span></div>')
for person in tier2:
    html_parts.append(generate_full_card(person, 2))

# Tier 3
html_parts.append(f'\n<div class="section-header tier3-header">TIER 3 — WORTH A CHAT <span class="section-count">({len(tier3)} people)</span></div>')
for person in tier3:
    html_parts.append(generate_compact_card(person))

# Quick reference table
html_parts.append('\n<div class="section-header" style="color:#334155">QUICK REFERENCE — ALL SHORTLISTED</div>')
html_parts.append('''<div class="quick-ref">
<table>
<tr><th>Tier</th><th>Name</th><th>Organization</th><th>Type</th><th>Score</th><th>Followers</th><th>Warm</th><th>LinkedIn</th></tr>''')

for person in tier1:
    html_parts.append(generate_quick_ref_row(person, 1))
for person in tier2:
    html_parts.append(generate_quick_ref_row(person, 2))
for person in tier3:
    html_parts.append(generate_quick_ref_row(person, 3))

html_parts.append('</table>\n</div>')

# Footer
html_parts.append(f'''
<div style="text-align:center;padding:20px;font-size:11px;color:#94a3b8">
  Generated by Claude · LinkedIn profiles &amp; posts via Apify · Relationship data from Supabase · {datetime.now().strftime('%B %d, %Y')}
</div>
<script>
const SB_URL = 'https://ypqsrejrsocebnldicke.supabase.co';
const SB_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlwcXNyZWpyc29jZWJubGRpY2tlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYzMTk1NDQsImV4cCI6MjA1MTg5NTU0NH0.MdnHIyb_0GwQpTJjaBUx8g4kGizPRuAdPNFQhhqRQP8';

async function sbFetch(path, opts = {{}}) {{
  const res = await fetch(SB_URL + '/rest/v1/' + path, {{
    ...opts,
    headers: {{
      'apikey': SB_KEY,
      'Authorization': 'Bearer ' + SB_KEY,
      'Content-Type': 'application/json',
      'Prefer': opts.prefer || 'return=minimal',
      ...(opts.headers || {{}})
    }}
  }});
  if (opts.prefer === 'return=representation') return res.json();
  return res;
}}

// Copy message on click
document.querySelectorAll('.message-bubble').forEach(el => {{
  el.addEventListener('click', () => {{
    navigator.clipboard.writeText(el.textContent.trim()).then(() => {{
      const orig = el.style.background;
      el.style.background = '#d8b4fe';
      el.insertAdjacentHTML('beforeend', '<span class="copy-toast" style="position:absolute;right:8px;top:8px;font-size:11px;color:#7c3aed">Copied!</span>');
      setTimeout(() => {{
        el.style.background = orig;
        const toast = el.querySelector('.copy-toast');
        if (toast) toast.remove();
      }}, 1200);
    }});
  }});
}});

// ── Outreach toggle ──
function toggleOutreach(el) {{
  const name = el.dataset.contact;
  const active = !el.classList.contains('active');
  el.classList.toggle('active');
  const card = el.closest('.card') || el.closest('.compact-card');
  if (card) card.classList.toggle('reached-out', active);
  updateOutreachCounter();
  upsertAttendee(name, {{ sally_reached_out: active }});
}}

function updateOutreachCounter() {{
  let count = 0;
  document.querySelectorAll('.outreach-toggle').forEach(el => {{
    if (el.classList.contains('active')) count++;
  }});
  const counter = document.getElementById('outreach-count');
  if (counter) counter.textContent = count;
}}

// ── Justin's context save with debounce ──
let contextTimers = {{}};
function saveContext(textarea) {{
  const name = textarea.dataset.contact;
  const counter = textarea.parentElement.querySelector('.ctx-count');
  if (counter) counter.textContent = textarea.value.length;
  clearTimeout(contextTimers[name]);
  contextTimers[name] = setTimeout(() => {{
    upsertAttendee(name, {{ justin_context: textarea.value }});
  }}, 800);
}}

// ── Upsert to ted_attendees by name ──
async function upsertAttendee(name, fields) {{
  fields.updated_at = new Date().toISOString();
  await sbFetch('ted_attendees?ted_name=eq.' + encodeURIComponent(name), {{
    method: 'PATCH',
    body: JSON.stringify(fields),
    prefer: 'return=minimal'
  }});
}}

// ── HTML-safe text helper ──
function escH(s) {{ return s ? s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;') : ''; }}

// ── Search ──
let searchTimer;
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
const shortlistedNames = new Set({json.dumps([p['ted_name'] for p in shortlist])});

searchInput.addEventListener('input', () => {{
  clearTimeout(searchTimer);
  const q = searchInput.value.trim();
  if (q.length < 2) {{ searchResults.classList.remove('active'); return; }}
  searchTimer = setTimeout(() => searchAttendees(q), 300);
}});

searchInput.addEventListener('blur', () => {{
  setTimeout(() => searchResults.classList.remove('active'), 200);
}});

async function searchAttendees(q) {{
  const enc = encodeURIComponent('%' + q + '%');
  const url = 'ted_attendees?or=(ted_name.ilike.' + enc + ',ted_org.ilike.' + enc + ',ted_title.ilike.' + enc + ')&order=relevance_score.desc&limit=12&select=ted_id,ted_name,ted_title,ted_org,relevance_score,partnership_type,reasoning,tier,sally_pinned';
  const data = await sbFetch(url, {{ method: 'GET', prefer: 'return=representation' }});
  renderSearchResults(data || []);
}}

function renderSearchResults(results) {{
  const container = searchResults;
  container.textContent = '';
  if (results.length === 0) {{
    const empty = document.createElement('div');
    empty.className = 'search-empty';
    empty.textContent = 'No matches found';
    container.appendChild(empty);
    container.classList.add('active');
    return;
  }}
  for (const r of results) {{
    const row = document.createElement('div');
    row.className = 'search-result';

    const info = document.createElement('div');
    info.className = 'sr-info';

    const nameDiv = document.createElement('div');
    nameDiv.className = 'sr-name';
    const score = r.relevance_score || 0;
    const scoreBg = score >= 80 ? '#dcfce7' : score >= 60 ? '#fef3c7' : '#f3f4f6';
    const scoreFg = score >= 80 ? '#166534' : score >= 60 ? '#92400e' : '#4b5563';
    const scoreSpan = document.createElement('span');
    scoreSpan.className = 'sr-score';
    scoreSpan.style.background = scoreBg;
    scoreSpan.style.color = scoreFg;
    scoreSpan.textContent = score;
    nameDiv.appendChild(scoreSpan);
    nameDiv.appendChild(document.createTextNode(r.ted_name));
    info.appendChild(nameDiv);

    const meta = [r.ted_title, r.ted_org].filter(Boolean).join(' at ');
    if (meta) {{
      const metaDiv = document.createElement('div');
      metaDiv.className = 'sr-meta';
      metaDiv.textContent = meta;
      info.appendChild(metaDiv);
    }}

    if (r.reasoning) {{
      const reasonDiv = document.createElement('div');
      reasonDiv.className = 'sr-reasoning';
      reasonDiv.textContent = r.reasoning.substring(0, 120);
      info.appendChild(reasonDiv);
    }}

    row.appendChild(info);

    const inBrief = shortlistedNames.has(r.ted_name);
    const btn = document.createElement('button');
    btn.className = 'btn-pin';
    if (inBrief) {{
      btn.classList.add('already');
      btn.textContent = 'In brief';
    }} else if (r.sally_pinned) {{
      btn.classList.add('already');
      btn.textContent = 'Pinned';
    }} else {{
      btn.textContent = '+ Sally\\'s Picks';
      btn.addEventListener('click', () => pinContact(r.ted_id, btn));
    }}
    row.appendChild(btn);

    container.appendChild(row);
  }}
  container.classList.add('active');
}}

// ── Pin / Unpin ──
async function pinContact(tedId, btn) {{
  btn.textContent = 'Pinning...';
  btn.disabled = true;
  await sbFetch('ted_attendees?ted_id=eq.' + tedId, {{
    method: 'PATCH',
    body: JSON.stringify({{ sally_pinned: true, updated_at: new Date().toISOString() }}),
    prefer: 'return=minimal'
  }});
  btn.textContent = 'Pinned';
  btn.classList.add('already');
  loadPicks();
}}

async function unpinContact(tedId) {{
  await sbFetch('ted_attendees?ted_id=eq.' + tedId, {{
    method: 'PATCH',
    body: JSON.stringify({{ sally_pinned: false, updated_at: new Date().toISOString() }}),
    prefer: 'return=minimal'
  }});
  loadPicks();
}}

// ── Sally's Picks ──
async function loadPicks() {{
  const data = await sbFetch('ted_attendees?sally_pinned=eq.true&order=updated_at.desc&select=*', {{ method: 'GET', prefer: 'return=representation' }});
  const section = document.getElementById('picks-section');
  const container = document.getElementById('picks-cards');
  const countEl = document.getElementById('picks-count');
  const picks = data || [];
  countEl.textContent = '(' + picks.length + ')';
  if (picks.length === 0) {{
    section.classList.remove('active');
    container.textContent = '';
    return;
  }}
  section.classList.add('active');
  container.textContent = '';

  for (const p of picks) {{
    const card = document.createElement('div');
    card.className = 'compact-card';
    card.id = 'pick-' + p.ted_id;

    const score = p.relevance_score || 0;
    const scoreBg = score >= 80 ? '#dcfce7' : score >= 60 ? '#fef3c7' : '#f3f4f6';
    const scoreFg = score >= 80 ? '#166534' : score >= 60 ? '#92400e' : '#4b5563';
    const ptype = (p.partnership_type || '').replace('_', ' ');
    const meta = [p.ted_title, p.ted_org].filter(Boolean).join(' at ');
    const li = p.ted_linkedin ? 'https://www.linkedin.com/in/' + p.ted_linkedin : '';

    // Build card using DOM methods
    const top = document.createElement('div');
    top.className = 'card-top';
    const avatar = document.createElement('div');
    avatar.className = 'avatar-placeholder';
    avatar.textContent = (p.ted_firstname || '?')[0];
    top.appendChild(avatar);

    const nameWrap = document.createElement('div');
    const nameLine = document.createElement('div');
    nameLine.className = 'card-name';
    nameLine.textContent = p.ted_name + ' ';
    const badge = document.createElement('span');
    badge.className = 'tier-badge badge-pick';
    badge.textContent = "Sally's Pick";
    nameLine.appendChild(badge);
    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn-remove';
    removeBtn.textContent = 'Remove';
    removeBtn.addEventListener('click', () => unpinContact(p.ted_id));
    nameLine.appendChild(removeBtn);
    nameWrap.appendChild(nameLine);

    const titleDiv = document.createElement('div');
    titleDiv.className = 'card-title';
    titleDiv.textContent = meta;
    nameWrap.appendChild(titleDiv);
    top.appendChild(nameWrap);
    card.appendChild(top);

    const metaRow = document.createElement('div');
    metaRow.className = 'meta-row';
    const scoreBadge = document.createElement('span');
    scoreBadge.style.cssText = 'background:' + scoreBg + ';color:' + scoreFg + ';padding:1px 6px;border-radius:6px;font-weight:700';
    scoreBadge.textContent = score + ' ' + ptype;
    metaRow.appendChild(scoreBadge);
    card.appendChild(metaRow);

    if (p.reasoning) {{
      const bio = document.createElement('div');
      bio.className = 'bio';
      bio.textContent = p.reasoning;
      card.appendChild(bio);
    }}

    if (p.conversation_hook) {{
      const hook = document.createElement('div');
      hook.className = 'highlight-box';
      const strong = document.createElement('strong');
      strong.textContent = 'Conversation hook: ';
      hook.appendChild(strong);
      hook.appendChild(document.createTextNode(p.conversation_hook));
      card.appendChild(hook);
    }}

    if (li) {{
      const link = document.createElement('a');
      link.className = 'linkedin-link';
      link.href = li;
      link.target = '_blank';
      link.textContent = 'LinkedIn Profile';
      card.appendChild(link);
    }}

    const notesDiv = document.createElement('div');
    notesDiv.className = 'pick-notes';
    const notesLabel = document.createElement('strong');
    notesLabel.style.cssText = 'font-size:11px;color:#7c3aed';
    notesLabel.textContent = "SALLY'S NOTES";
    notesDiv.appendChild(notesLabel);
    const textarea = document.createElement('textarea');
    textarea.dataset.tid = p.ted_id;
    textarea.placeholder = 'Add notes about this conversation...';
    textarea.value = p.sally_notes || '';
    textarea.addEventListener('input', function() {{ savePickNotes(this); }});
    notesDiv.appendChild(textarea);
    card.appendChild(notesDiv);

    container.appendChild(card);
  }}
}}

let pickTimers = {{}};
function savePickNotes(textarea) {{
  const tid = textarea.dataset.tid;
  clearTimeout(pickTimers[tid]);
  pickTimers[tid] = setTimeout(async () => {{
    await sbFetch('ted_attendees?ted_id=eq.' + tid, {{
      method: 'PATCH',
      body: JSON.stringify({{ sally_notes: textarea.value, updated_at: new Date().toISOString() }}),
      prefer: 'return=minimal'
    }});
  }}, 800);
}}

// ── Add New Person (LinkedIn enrichment) ──
function openAddModal() {{
  document.getElementById('add-modal').classList.add('active');
  document.getElementById('linkedin-url-input').value = '';
  document.getElementById('enrich-status').classList.remove('active');
  document.getElementById('btn-enrich').disabled = false;
  document.getElementById('btn-enrich').textContent = 'Enrich + Add';
  document.getElementById('linkedin-url-input').focus();
}}

function closeAddModal() {{
  document.getElementById('add-modal').classList.remove('active');
}}

async function enrichAndAdd() {{
  const url = document.getElementById('linkedin-url-input').value.trim();
  if (!url || !url.includes('linkedin.com/in/')) {{
    alert('Please enter a valid LinkedIn URL (e.g. https://www.linkedin.com/in/username)');
    return;
  }}
  const btn = document.getElementById('btn-enrich');
  const status = document.getElementById('enrich-status');
  btn.disabled = true;
  btn.textContent = 'Working...';
  status.textContent = 'Scraping LinkedIn profile and scoring for Outdoorithm fit... (~30 seconds)';
  status.classList.add('active');

  try {{
    const resp = await fetch(SB_URL + '/functions/v1/ted-enrich-contact', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + SB_KEY }},
      body: JSON.stringify({{ linkedin_url: url }})
    }});
    if (!resp.ok) {{
      const err = await resp.json();
      throw new Error(err.error || 'Enrichment failed');
    }}
    const result = await resp.json();
    status.textContent = 'Scored! ' + escH(result.ted_name) + ': ' + result.relevance_score + '/100. Adding...';

    // Insert into ted_attendees
    result.sally_pinned = true;
    result.updated_at = new Date().toISOString();
    result.partnership_types = JSON.stringify(result.partnership_types || []);
    await sbFetch('ted_attendees', {{
      method: 'POST',
      body: JSON.stringify(result),
      headers: {{ 'Prefer': 'resolution=merge-duplicates' }},
      prefer: 'return=minimal'
    }});

    closeAddModal();
    loadPicks();
  }} catch (e) {{
    status.textContent = 'Error: ' + e.message;
    btn.disabled = false;
    btn.textContent = 'Retry';
  }}
}}

// ── Load state on page load ──
document.addEventListener('DOMContentLoaded', async () => {{
  try {{
    // Load state from ted_attendees for shortlisted contacts
    const names = Array.from(shortlistedNames);
    const stateMap = {{}};
    for (let i = 0; i < names.length; i += 50) {{
      const chunk = names.slice(i, i + 50);
      const orClause = chunk.map(n => 'ted_name.eq.' + encodeURIComponent(n)).join(',');
      const data = await sbFetch('ted_attendees?or=(' + orClause + ')&select=ted_name,sally_reached_out,justin_context', {{ method: 'GET', prefer: 'return=representation' }});
      (data || []).forEach(row => {{ stateMap[row.ted_name] = row; }});
    }}

    // Restore outreach toggles
    document.querySelectorAll('.outreach-toggle').forEach(el => {{
      const name = el.dataset.contact;
      const row = stateMap[name];
      if (row && row.sally_reached_out) {{
        el.classList.add('active');
        const card = el.closest('.card') || el.closest('.compact-card');
        if (card) card.classList.add('reached-out');
      }}
    }});
    updateOutreachCounter();

    // Restore context textareas
    document.querySelectorAll('.justin-context-box textarea').forEach(ta => {{
      const name = ta.dataset.contact;
      const row = stateMap[name];
      if (row && row.justin_context) {{
        ta.value = row.justin_context;
        const counter = ta.parentElement.querySelector('.ctx-count');
        if (counter) counter.textContent = row.justin_context.length;
      }}
    }});

    // Load Sally's Picks
    await loadPicks();
  }} catch (e) {{
    console.error('Failed to load state:', e);
  }}
}});
</script>
</body>
</html>''')

# Write output
output_path = '/Users/Justin/Code/TrueSteele/contacts/docs/TED2026/TED_2026_Outdoorithm_Networking_Brief.html'
with open(output_path, 'w') as f:
    f.write('\n'.join(html_parts))

print(f"\nLookbook generated: {output_path}")
print(f"  File size: {len(''.join(html_parts)):,} bytes")
print(f"  Tier 1 cards: {len(tier1)}")
print(f"  Tier 2 cards: {len(tier2)}")
print(f"  Tier 3 compact cards: {len(tier3)}")
print(f"  Quick ref rows: {len(tier1) + len(tier2) + len(tier3)}")
