#!/usr/bin/env python3
"""
Config-driven conference lookbook HTML generator.

Produces a self-contained HTML networking brief from a conference config file.
All conference/org-specific strings come from the config — no hardcoded values.

Usage:
  python scripts/conference/generate_lookbook.py --config conferences/ted-2026/config.yaml
"""

import argparse
import importlib
import json
import html as html_mod
import re
import sys
from datetime import datetime
from pathlib import Path

# Add repo root to sys.path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
from scripts.conference.config import ConferenceConfig


def main():
    parser = argparse.ArgumentParser(description="Generate conference networking lookbook HTML")
    parser.add_argument("--config", required=True, help="Path to conference config YAML")
    parser.add_argument("--output", help="Output HTML path (default: {deploy_dir}/index.html)")
    args = parser.parse_args()

    config = ConferenceConfig(args.config)
    prefix = config.conference.field_prefix

    def pf(field):
        """Prefix a field name with the conference field prefix."""
        return f"{prefix}_{field}" if prefix else field

    # ── Config-derived values ─────────────────────────────────────────────

    primary = config.users.primary
    support = config.users.support
    org = config.organization
    conf = config.conference
    sb = config.supabase

    # User column names from config
    pinned_col = primary.columns.get('pinned', f'{primary.name.lower()}_pinned')
    reached_col = primary.columns.get('reached_out', f'{primary.name.lower()}_reached_out')
    notes_col = primary.columns.get('notes', f'{primary.name.lower()}_notes')
    context_col = support.columns.get('context', f'{support.name.lower()}_context')

    # Connection field names
    primary_conn = primary.connection_field or f"{primary.name.lower()}_connection"
    support_conn = support.connection_field or f"{support.name.lower()}_connection"

    # ── Load Data ─────────────────────────────────────────────────────────

    shortlist = json.load(open(config.data_paths.shortlist))

    # Load LinkedIn posts
    posts_by_username = {}
    if config.data_paths.linkedin_posts:
        try:
            posts_raw = json.load(open(config.data_paths.linkedin_posts))
            for p in posts_raw:
                author = p.get('author', {})
                if isinstance(author, dict):
                    username = author.get('publicIdentifier', '')
                else:
                    username = ''
                if not username:
                    url = p.get('linkedinUrl', '')
                    if '/in/' in url:
                        username = url.split('/in/')[-1].strip('/').split('?')[0].lower()
                if username:
                    posts_by_username.setdefault(username.lower(), []).append(p)
        except FileNotFoundError:
            pass

    print(f"Posts grouped by {len(posts_by_username)} usernames")
    for u, pp in posts_by_username.items():
        print(f"  {u}: {len(pp)} posts")

    # Load deep writeups module
    deep_writeups = {}
    if config.data_paths.deep_writeups_module:
        try:
            intel_dir = str(REPO_ROOT / "scripts" / "intelligence")
            if intel_dir not in sys.path:
                sys.path.insert(0, intel_dir)
            mod = importlib.import_module(config.data_paths.deep_writeups_module)
            deep_writeups = getattr(mod, 'DEEP_WRITEUPS', {})
            print(f"Loaded {len(deep_writeups)} deep writeups")
        except ImportError as e:
            print(f"Warning: Could not load deep writeups module: {e}")

    # Split tiers
    tiers_data = {}
    for tier_num in sorted(config.tiers.keys()):
        tiers_data[tier_num] = sorted(
            [s for s in shortlist if s.get('tier') == tier_num],
            key=lambda x: -x.get('boosted_score', 0)
        )

    print("\n" + " | ".join(f"Tier {t}: {len(ppl)}" for t, ppl in tiers_data.items()))

    # ── Helper Functions ──────────────────────────────────────────────────

    def h(text):
        if not text:
            return ''
        return html_mod.escape(str(text))

    def get_initials(person):
        fn = person.get(pf('firstname'), '')
        ln = person.get(pf('lastname'), '')
        return (fn[0] if fn else '') + (ln[0] if ln else '')

    def get_photo_html(person, size=56):
        li_photo = person.get('li_photo', '')
        conf_photo = person.get(pf('photo'), '')
        photo_url = ''
        if li_photo:
            if isinstance(li_photo, dict):
                photo_url = li_photo.get('url', '')
            elif isinstance(li_photo, str) and li_photo.startswith('http'):
                photo_url = li_photo
        if not photo_url and conf_photo and conf_photo.startswith('http'):
            photo_url = conf_photo
        if photo_url:
            return f'<img src="{h(photo_url)}" alt="{h(person.get(pf("name"),""))}" style="width:{size}px;height:{size}px;border-radius:50%;object-fit:cover;flex-shrink:0" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">\n    <div class="avatar-placeholder" style="display:none">{h(get_initials(person))}</div>'
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

    def get_volunteering_str(person):
        vol = person.get('li_volunteering', [])
        if not vol or not isinstance(vol, list):
            return ''
        items = []
        for v in vol[:3]:
            if isinstance(v, dict):
                role = v.get('role', v.get('position', ''))
                vorg = v.get('companyName', v.get('company', ''))
                if role and vorg:
                    items.append(f"{role} at {vorg}")
                elif vorg:
                    items.append(vorg)
        return ', '.join(items)

    def get_causes_str(person):
        causes = person.get('li_causes', [])
        if not causes or not isinstance(causes, list):
            return ''
        return ', '.join(causes[:5])

    def get_posts_for_person(person):
        username = person.get(pf('linkedin'), '').lower()
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
        pt_cfg = org.partnership_types.get(ptype, {})
        if pt_cfg:
            style = f"background:{pt_cfg.get('color_bg', '#f3f4f6')};color:{pt_cfg.get('color_fg', '#6b7280')};"
            label = pt_cfg.get('label', ptype)
        else:
            style = 'background:#f3f4f6;color:#6b7280;'
            label = ptype
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
        if person.get(support_conn):
            badges.append(f'<span class="tier-badge badge-relationship">{h(support.name)}\'s Connection</span>')
        if person.get(primary_conn):
            badges.append(f'<span class="tier-badge" style="background:#dcfce7;color:#166534;font-size:9px;margin-left:4px">{h(primary.name)}\'s Connection</span>')
        return ' '.join(badges)

    def relationship_summary(person):
        parts = []
        closeness = person.get('db_closeness', '')
        momentum = person.get('db_momentum', '')
        last_date = person.get('db_last_date', '')
        donor_tier = person.get('db_donor_tier', '')
        org_fit = person.get('db_outdoorithm_fit', '')
        if closeness and closeness != 'no_history':
            parts.append(f"<strong>Closeness:</strong> {h(closeness)}")
        if momentum and momentum != 'inactive':
            parts.append(f"<strong>Momentum:</strong> {h(momentum)}")
        if last_date:
            parts.append(f"<strong>Last contact:</strong> {h(last_date)}")
        if donor_tier:
            parts.append(f"<strong>Donor tier:</strong> {h(donor_tier)}")
        if org_fit:
            parts.append(f"<strong>{h(org.name)} fit:</strong> {h(org_fit)}")
        return ' &middot; '.join(parts)

    def build_background(person):
        parts = []
        title = person.get(pf('title'), '')
        porg = person.get(pf('org'), '')
        if title and porg:
            parts.append(f"{title} at {porg}.")
        elif porg:
            parts.append(f"At {porg}.")
        about = person.get(pf('about'), '')
        if about:
            parts.append(about[:300])
        li_about = person.get('li_about', '')
        if li_about and li_about != about and len(li_about) > len(about or ''):
            if not about or li_about[:50] != about[:50]:
                parts.append(li_about[:300])
        if not about and not li_about:
            db_summary = person.get('db_summary', '')
            if db_summary:
                parts.append(db_summary[:300])
        return ' '.join(parts)

    def make_connect_url(person):
        connect_id = person.get(pf('id'), '')
        if connect_id and conf.connect_url_template:
            return conf.connect_url_template.replace(f'{{{pf("id")}}}', str(connect_id))
        return ''

    # ── Card Generators ───────────────────────────────────────────────────

    def generate_full_card(person, tier_num):
        tc = config.tiers.get(tier_num)
        tier_label = tc.label if tc else f'Tier {tier_num}'
        badge_class = tc.badge_class if tc else f'badge-tier{tier_num}'
        co_class = tc.company_class if tc else ''

        name = person.get(pf('name'), '')
        porg = person.get(pf('org'), '')
        title = person.get(pf('title'), '')
        city = person.get(pf('city'), '')
        country = person.get(pf('country'), '')
        location = f"{city}, {country}" if city and country else city or country or ''
        followers = format_followers(person.get('li_followers', 0))
        education = get_education_str(person)

        # Role badges from config
        role_tags = []
        for role_def in conf.roles:
            if person.get(role_def['field'], False):
                role_tags.append(role_def['label'])
        role_str = ' &middot; '.join(role_tags)

        meta_items = []
        if followers:
            meta_items.append(f'<span>followers {followers}</span>')
        if location:
            meta_items.append(f'<span>{h(location)}</span>')
        if education:
            meta_items.append(f'<span>{h(education)}</span>')

        title_line = title
        if role_str:
            title_line = f"{title} &middot; {role_str}" if title else role_str

        background = build_background(person)
        rel = relationship_summary(person)

        # Deep write-up
        deep = deep_writeups.get(name)
        reasoning = person.get('reasoning', '')
        key_signal = person.get('key_signal', '')
        deep_vision = deep[0] if deep else ''
        app_message = deep[1] if deep else ''

        convo_hook = person.get('conversation_hook', '')
        person_posts = get_posts_for_person(person)
        recent_posts = []
        for pp in person_posts[:3]:
            text = pp.get('content', pp.get('text', ''))
            if text:
                recent_posts.append(format_post_text(text, 180))

        vol_str = get_volunteering_str(person)
        causes_str = get_causes_str(person)
        idea = person.get(pf('idea'), '')
        passion = person.get(pf('passion'), '')
        ask_me = person.get(pf('ask_me_about'), '')

        safe_id = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())

        card = f'''<div class="card" id="card-{safe_id}" data-contact="{h(name)}">
  <div class="card-top">
    {get_photo_html(person)}
    <div>
      <div class="card-name">{h(name)} <span class="tier-badge {badge_class}">{tier_label}</span> {warm_lead_badges(person)}
        <span class="outreach-toggle" data-contact="{h(name)}" onclick="toggleOutreach(this)"><span class="uncheck">&#9744;</span><span class="check">&#9745;</span> Reached out</span>
      </div>
      <div class="card-company {co_class}">{h(porg)}</div>
      <div class="card-title">{title_line}</div>
    </div>
  </div>
  <div class="meta-row">
    {"".join(f"    {item}" for item in meta_items)}
  </div>'''

        if background:
            card += f'''
  <div class="section-label">Background</div>
  <div class="bio">{h(background)}</div>'''

        if idea:
            card += f'''
  <div style="font-size:13px;color:{org.color_primary};margin:4px 0"><strong>Idea Worth Spreading:</strong> {h(idea)}</div>'''

        if passion:
            card += f'''
  <div style="font-size:13px;color:var(--text-muted);margin:4px 0"><strong>Passions:</strong> {h(passion)}</div>'''

        if ask_me:
            card += f'''
  <div style="font-size:13px;color:var(--text-muted);margin:4px 0"><strong>Ask me about:</strong> {h(ask_me)}</div>'''

        if vol_str:
            card += f'''
  <div style="font-size:13px;color:var(--text-muted);margin:4px 0"><strong>Volunteer:</strong> {h(vol_str)}</div>'''

        if causes_str:
            card += f'''
  <div style="font-size:13px;color:var(--text-muted);margin:4px 0"><strong>Causes:</strong> {h(causes_str)}</div>'''

        if rel:
            card += f'''
  <div class="relationship-box">
    <strong>YOUR RELATIONSHIP</strong><br>
    {rel}
  </div>'''

        # Org partnership vision / connection box
        if deep_vision:
            vision_paragraphs = [p.strip() for p in deep_vision.strip().split('\n\n') if p.strip()]
            vision_parts = []
            for p in vision_paragraphs:
                formatted = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', p.replace('\n', ' '))
                vision_parts.append(h(formatted).replace('&lt;strong&gt;', '<strong>').replace('&lt;/strong&gt;', '</strong>'))
            vision_html = '</p><p style="margin-top:8px">'.join(vision_parts)
            card += f'''
  <div class="highlight-box" style="border-left-width:4px">
    <strong>{h(org.name).upper()} PARTNERSHIP VISION</strong>
    <p style="margin-top:8px">{vision_html}</p>
  </div>'''
        elif reasoning:
            oc_text = h(reasoning)
            if key_signal:
                oc_text += f'<br><strong>Key signal:</strong> {h(key_signal)}'
            card += f'''
  <div class="highlight-box">
    <strong>{h(org.name).upper()} CONNECTION</strong><br>
    {oc_text}
  </div>'''

        # Conference app message
        if app_message:
            card += f'''
  <div class="ted-message-box">
    <strong>DRAFT {h(conf.name).upper()} APP MESSAGE</strong>
    <div class="message-bubble">{h(app_message.strip())}</div>
    <div style="font-size:11px;color:#94a3b8;margin-top:4px;font-style:italic">Tap to copy. Edit to make it yours.</div>
  </div>'''

        # Support user's context box
        if person.get(support_conn):
            card += f'''
  <div class="justin-context-box">
    <strong>{h(support.name).upper()}'S CONTEXT</strong>
    <textarea data-contact="{h(name)}" placeholder="Add relationship context, notes, or history..." oninput="saveContext(this)"></textarea>
    <div class="char-count"><span class="ctx-count">0</span> chars</div>
  </div>'''

        # Conversation hook
        if convo_hook and not deep_vision:
            card += f'''
  <div class="convo-starters">
    <strong>CONVERSATION STARTER</strong>
    <ul>
      <li>{h(convo_hook)}</li>
    </ul>
  </div>'''

        # Recent posts
        if recent_posts:
            posts_html = '\n'.join(f'      <li style="margin-bottom:8px">{h(p)}</li>' for p in recent_posts)
            card += f'''
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

        card += f'''
  <div class="tags">
    {" ".join(tags)}
  </div>'''

        # LinkedIn link
        linkedin = person.get(pf('linkedin'), '')
        if linkedin:
            card += f'''
  <a href="https://www.linkedin.com/in/{h(linkedin)}" target="_blank" class="linkedin-link">View LinkedIn Profile &rarr;</a>'''

        # Conference connect link
        connect_url = make_connect_url(person)
        if connect_url:
            card += f'''
  <a href="{h(connect_url)}" target="_blank" class="linkedin-link" style="margin-left:12px;color:#e04040">View {h(conf.name)} Connect &rarr;</a>'''

        card += '\n</div>'
        return card

    def generate_compact_card(person):
        name = person.get(pf('name'), '')
        porg = person.get(pf('org'), '')
        title = person.get(pf('title'), '')
        followers = format_followers(person.get('li_followers', 0))
        reasoning = person.get('reasoning', '')
        convo_hook = person.get('conversation_hook', '')

        compact_bio = f"{h(title)} at {h(porg)}" if title and porg else h(title or porg)
        if followers:
            compact_bio += f" &middot; followers {followers}"

        linkedin = person.get(pf('linkedin'), '')

        tc3 = config.tiers.get(3)
        tier3_label = tc3.label if tc3 else 'Worth a Chat'
        tier3_badge = tc3.badge_class if tc3 else 'badge-tier3'

        card = f'''<div class="compact-card">
  <div class="card-top">
    {get_photo_html(person, 48)}
    <div>
      <div class="card-name">{h(name)} <span class="tier-badge {tier3_badge}">{tier3_label}</span> {warm_lead_badges(person)}</div>
      <div class="card-company">{h(porg)}</div>
      <div class="card-title">{h(title)}</div>
    </div>
  </div>
  <div class="compact-bio">{compact_bio}</div>'''

        if reasoning:
            card += f'''
  <div style="font-size:12px;color:var(--text-muted);margin:4px 0">{h(reasoning[:150])}</div>'''

        if convo_hook:
            card += f'''
  <div style="font-size:12px;color:{org.color_primary};margin:4px 0"><strong>Hook:</strong> {h(convo_hook[:150])}</div>'''

        card += f'''
  <div class="tags" style="margin-top:4px">
    {partnership_types_badges(person)}
    <span class="tag">Score: {person.get("relevance_score", 0)}</span>
  </div>'''

        links = []
        if linkedin:
            links.append(f'<a href="https://www.linkedin.com/in/{h(linkedin)}" target="_blank" class="linkedin-link">LinkedIn &rarr;</a>')
        connect_url = make_connect_url(person)
        if connect_url:
            links.append(f'<a href="{h(connect_url)}" target="_blank" class="linkedin-link" style="color:#e04040;margin-left:8px">{h(conf.name)} Connect &rarr;</a>')
        if links:
            card += '\n  ' + ' '.join(links)

        card += '\n</div>'
        return card

    def generate_quick_ref_row(person, tier_num):
        tc = config.tiers.get(tier_num)
        dot_class = f'dot-t{tier_num}'
        label = tc.label.split()[0].rstrip('-') if tc else str(tier_num)

        name = person.get(pf('name'), '')
        porg = person.get(pf('org'), '')
        ptype = person.get('partnership_type', '')
        score = person.get('relevance_score', 0)
        followers = format_followers(person.get('li_followers', 0))
        linkedin = person.get(pf('linkedin'), '')

        li_cell = f'<a href="https://www.linkedin.com/in/{h(linkedin)}" target="_blank">Profile</a>' if linkedin else '<em>No LinkedIn</em>'
        warm = ''
        if person.get(support_conn):
            warm += support.name[0]
        if person.get(primary_conn):
            warm += primary.name[0]

        return f'<tr><td><span class="tier-dot {dot_class}"></span>{label}</td><td>{h(name)}</td><td>{h(porg)}</td><td>{h(ptype.replace("_"," ").title())}</td><td>{score}</td><td>{followers or "-"}</td><td>{warm or "-"}</td><td>{li_cell}</td></tr>'

    # ── Stats ─────────────────────────────────────────────────────────────

    total_shortlisted = sum(len(t) for t in tiers_data.values())
    warm_count = sum(1 for s in shortlist if s.get(support_conn) or s.get(primary_conn))

    # Tier 1+2 people for partnership type stats
    top_tier_people = []
    for t in sorted(tiers_data.keys()):
        if t <= 2:
            top_tier_people.extend(tiers_data[t])

    # ── Generate HTML ─────────────────────────────────────────────────────

    parts = []
    page_title = f"{conf.name} — {org.name} Networking Brief"

    # Tier counts for stats line
    tier_stats = []
    for t in sorted(tiers_data.keys()):
        tc = config.tiers.get(t)
        lbl = tc.label.lower() if tc else f'tier {t}'
        tier_stats.append(f"{len(tiers_data[t])} {lbl}")

    # Head + CSS
    parts.append(f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{h(page_title)}</title>
<style>:root {{
    --oc-green: {org.color_primary};
    --oc-green-light: {org.color_primary};
    --oc-light: #f0fdf4;
    --tier1: {org.color_primary};
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
    background: linear-gradient(135deg, {org.color_primary} 0%, {org.color_accent} 50%, {org.color_dark} 100%);
    color: white; padding: 32px 20px; text-align: center;
  }}
  .header h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; }}
  .header .subtitle {{ font-size: 14px; opacity: 0.9; }}
  .header .date {{ font-size: 13px; opacity: 0.75; margin-top: 8px; }}
  .header .stats {{ font-size: 12px; opacity: 0.7; margin-top: 4px; }}
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
    background: linear-gradient(135deg, {org.color_primary}, {org.color_accent});
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
  .badge-tier1 {{ background: #dcfce7; color: {org.color_primary}; }}
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
  .highlight-box strong {{ color: {org.color_primary}; }}
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
    background: #dcfce7; border-color: #22c55e; color: {org.color_primary};
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
  .search-input:focus {{ border-color: {org.color_primary}; }}
  .search-input::placeholder {{ color: #94a3b8; }}
  .btn-add-new {{
    padding: 10px 16px; background: {org.color_primary}; color: white; border: none;
    border-radius: 10px; font-size: 13px; font-weight: 600; cursor: pointer;
    white-space: nowrap;
  }}
  .btn-add-new:hover {{ background: {org.color_dark}; }}
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
    border-radius: 10px; background: #dcfce7; color: {org.color_primary}; margin-right: 6px;
  }}
  .btn-pin {{
    padding: 6px 14px; background: {org.color_primary}; color: white; border: none;
    border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer;
    white-space: nowrap; flex-shrink: 0;
  }}
  .btn-pin:hover {{ background: {org.color_dark}; }}
  .btn-pin.already {{ background: #e2e8f0; color: #64748b; cursor: default; }}
  .search-empty {{
    padding: 16px; text-align: center; color: var(--text-muted); font-size: 13px;
  }}
  /* Primary user's Picks section */
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
  .modal input:focus {{ border-color: {org.color_primary}; }}
  .modal-btns {{ display: flex; gap: 8px; justify-content: flex-end; }}
  .modal-btns button {{
    padding: 8px 18px; border-radius: 8px; font-size: 13px; font-weight: 600;
    cursor: pointer; border: none;
  }}
  .btn-cancel {{ background: #f1f5f9; color: #475569; }}
  .btn-enrich {{ background: {org.color_primary}; color: white; }}
  .btn-enrich:disabled {{ background: #94a3b8; cursor: not-allowed; }}
  .enrich-status {{
    font-size: 13px; color: {org.color_primary}; text-align: center; padding: 8px;
    display: none;
  }}
  .enrich-status.active {{ display: block; }}</style>
</head>
<body>
''')

    # Tier 1+2 count for outreach counter
    t1_count = len(tiers_data.get(1, []))
    t2_count = len(tiers_data.get(2, []))

    # Header
    parts.append(f'''<div class="header">
  <h1>{h(page_title)}</h1>
  <div class="subtitle">Prepared for {h(primary.full_name)}, {h(primary.role)}</div>
  <div class="date">{h(conf.dates)} | {h(conf.venue)}</div>
  <div class="stats">{len(shortlist):,} featured in brief &middot; {" &middot; ".join(tier_stats)} &middot; {warm_count} warm leads &middot; search covers all {conf.attendee_count:,} attendees</div>
  <div class="outreach-counter" id="outreach-counter">{h(primary.name)}'s outreach: <strong><span id="outreach-count">0</span>/{t1_count + t2_count}</strong> contacted</div>
</div>
''')

    # Search bar
    parts.append(f'''<div class="search-container">
  <div class="search-row">
    <input type="text" class="search-input" id="search-input" placeholder="Search all {conf.attendee_count:,} scored {h(conf.name)} attendees by name, org, or title..." autocomplete="off">
    <button class="btn-add-new" onclick="openAddModal()">+ Add New</button>
  </div>
  <div class="search-results" id="search-results"></div>
</div>
''')

    # Primary user's Picks section
    parts.append(f'''<div class="picks-section" id="picks-section">
  <div class="picks-header">{h(primary.name).upper()}'S PICKS <span class="section-count" id="picks-count">(0)</span></div>
  <div id="picks-cards"></div>
</div>
''')

    # Add New Person modal
    parts.append(f'''<div class="modal-overlay" id="add-modal">
  <div class="modal">
    <h3>Add someone new</h3>
    <p style="font-size:13px;color:#64748b;margin-bottom:12px">Paste their LinkedIn URL. We'll scrape the profile and score them for {h(org.name)} fit (~30-90 seconds).</p>
    <input type="text" id="linkedin-url-input" placeholder="https://www.linkedin.com/in/username">
    <div class="enrich-status" id="enrich-status">Scraping profile and scoring...</div>
    <div class="modal-btns">
      <button class="btn-cancel" onclick="closeAddModal()">Cancel</button>
      <button class="btn-enrich" id="btn-enrich" onclick="enrichAndAdd()">Enrich + Add</button>
    </div>
  </div>
</div>
''')

    # Tier sections
    for tier_num in sorted(tiers_data.keys()):
        people = tiers_data[tier_num]
        tc = config.tiers.get(tier_num)
        tier_label = tc.label if tc else f'Tier {tier_num}'
        header_class = f'tier{tier_num}-header'

        parts.append(f'\n<div class="section-header {header_class}">TIER {tier_num} — {tier_label.upper()} <span class="section-count">({len(people)} people)</span></div>')

        if tier_num <= 2:
            for person in people:
                parts.append(generate_full_card(person, tier_num))
        else:
            for person in people:
                parts.append(generate_compact_card(person))

    # Quick reference table
    parts.append('\n<div class="section-header" style="color:#334155">QUICK REFERENCE — ALL SHORTLISTED</div>')
    parts.append('''<div class="quick-ref">
<table>
<tr><th>Tier</th><th>Name</th><th>Organization</th><th>Type</th><th>Score</th><th>Followers</th><th>Warm</th><th>LinkedIn</th></tr>''')

    for tier_num in sorted(tiers_data.keys()):
        for person in tiers_data[tier_num]:
            parts.append(generate_quick_ref_row(person, tier_num))

    parts.append('</table>\n</div>')

    # Footer + JavaScript
    # Build JS config constants from Python config
    js_table = sb.table_name
    js_id = pf('id')
    js_name = pf('name')
    js_firstname = pf('firstname')
    js_title = pf('title')
    js_org = pf('org')
    js_linkedin = pf('linkedin')

    parts.append(f'''
<div style="text-align:center;padding:20px;font-size:11px;color:#94a3b8">
  Generated by Claude &middot; LinkedIn profiles &amp; posts via Apify &middot; Relationship data from Supabase &middot; {datetime.now().strftime('%B %d, %Y')}
</div>
<script>
const SB_URL = {json.dumps(sb.project_url)};
const SB_KEY = {json.dumps(sb.anon_key)};
const TABLE = {json.dumps(js_table)};
const ID_FIELD = {json.dumps(js_id)};
const NAME_FIELD = {json.dumps(js_name)};
const FIRSTNAME_FIELD = {json.dumps(js_firstname)};
const TITLE_FIELD = {json.dumps(js_title)};
const ORG_FIELD = {json.dumps(js_org)};
const LINKEDIN_FIELD = {json.dumps(js_linkedin)};
const PINNED_COL = {json.dumps(pinned_col)};
const REACHED_COL = {json.dumps(reached_col)};
const NOTES_COL = {json.dumps(notes_col)};
const CONTEXT_COL = {json.dumps(context_col)};
const EDGE_FN = {json.dumps(sb.edge_function)};
const PRIMARY_USER = {json.dumps(primary.name)};
const ORG_NAME = {json.dumps(org.name)};

async function readResponseBody(res) {{
  if (res.status === 204 || res.status === 205) return null;
  if (res.headers.get('content-length') === '0') return null;
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return res.json();
  const text = await res.text();
  return text || null;
}}

function responseErrorMessage(payload, fallback) {{
  if (!payload) return fallback;
  if (typeof payload === 'string') return payload;
  return payload.error || payload.message || fallback;
}}

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
  const payload = await readResponseBody(res);
  if (!res.ok) {{
    throw new Error(responseErrorMessage(payload, `Supabase request failed (${{res.status}})`));
  }}
  if (opts.prefer === 'return=representation') {{
    return Array.isArray(payload) ? payload : (payload || []);
  }}
  return payload;
}}

async function readErrorResponse(resp, fallback) {{
  const payload = await readResponseBody(resp);
  return responseErrorMessage(payload, fallback);
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
  const wasActive = el.classList.contains('active');
  const active = !el.classList.contains('active');
  const card = el.closest('.card') || el.closest('.compact-card');
  el.classList.toggle('active', active);
  if (card) card.classList.toggle('reached-out', active);
  updateOutreachCounter();
  const patch = {{}};
  patch[REACHED_COL] = active;
  upsertAttendee(name, patch).catch((error) => {{
    el.classList.toggle('active', wasActive);
    if (card) card.classList.toggle('reached-out', wasActive);
    updateOutreachCounter();
    alert('Could not save outreach status: ' + error.message);
  }});
}}

function updateOutreachCounter() {{
  let count = 0;
  document.querySelectorAll('.outreach-toggle').forEach(el => {{
    if (el.classList.contains('active')) count++;
  }});
  const counter = document.getElementById('outreach-count');
  if (counter) counter.textContent = count;
}}

// ── Support user's context save with debounce ──
let contextTimers = {{}};
function saveContext(textarea) {{
  const name = textarea.dataset.contact;
  const counter = textarea.parentElement.querySelector('.ctx-count');
  if (counter) counter.textContent = textarea.value.length;
  clearTimeout(contextTimers[name]);
  contextTimers[name] = setTimeout(() => {{
    const patch = {{}};
    patch[CONTEXT_COL] = textarea.value;
    upsertAttendee(name, patch).catch((error) => {{
      console.error('Failed to save context for', name, error);
    }});
  }}, 800);
}}

// ── Upsert to table by name ──
async function upsertAttendee(name, fields) {{
  const payload = {{ ...fields, updated_at: new Date().toISOString() }};
  await sbFetch(TABLE + '?' + NAME_FIELD + '=eq.' + encodeURIComponent(name), {{
    method: 'PATCH',
    body: JSON.stringify(payload),
    prefer: 'return=minimal'
  }});
}}

// ── HTML-safe text helper ──
function escH(s) {{ return s ? s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;') : ''; }}

function normalizeLinkedInUrl(raw) {{
  const value = (raw || '').trim();
  if (!value) throw new Error('Please enter a valid LinkedIn URL.');

  const withProtocol = /^https?:\\/\\//i.test(value) ? value : 'https://' + value;
  let parsed;
  try {{
    parsed = new URL(withProtocol);
  }} catch {{
    throw new Error('Please enter a valid LinkedIn URL.');
  }}

  const host = parsed.hostname.replace(/^www\\./i, '').toLowerCase();
  if (host !== 'linkedin.com' && !host.endsWith('.linkedin.com')) {{
    throw new Error('Please use a LinkedIn profile URL.');
  }}

  const segments = parsed.pathname.split('/').filter(Boolean);
  if (segments[0] !== 'in' || !segments[1]) {{
    throw new Error('Please use a LinkedIn profile URL in the /in/username format.');
  }}

  parsed.protocol = 'https:';
  parsed.hostname = 'www.linkedin.com';
  parsed.pathname = '/in/' + segments[1];
  parsed.search = '';
  parsed.hash = '';

  return parsed.toString().replace(/\\/$/, '');
}}

function normalizeLinkedInSlug(raw) {{
  const parsed = new URL(normalizeLinkedInUrl(raw));
  return parsed.pathname.replace(/^\\/in\\//, '').replace(/\\/$/, '');
}}

function linkedinProfileUrl(value) {{
  if (!value) return '';
  if (/^https?:\\/\\//i.test(value)) {{
    try {{
      return normalizeLinkedInUrl(value);
    }} catch {{
      return value;
    }}
  }}
  return 'https://www.linkedin.com/in/' + value.replace(/^\\/+|\\/+$/g, '');
}}

function showSearchMessage(message) {{
  searchResults.textContent = '';
  const empty = document.createElement('div');
  empty.className = 'search-empty';
  empty.textContent = message;
  searchResults.appendChild(empty);
  searchResults.classList.add('active');
}}

async function findExistingAttendee(result) {{
  const filters = [];
  if (result[LINKEDIN_FIELD]) filters.push(LINKEDIN_FIELD + '.eq.' + encodeURIComponent(result[LINKEDIN_FIELD]));
  if (result[NAME_FIELD]) filters.push(NAME_FIELD + '.eq.' + encodeURIComponent(result[NAME_FIELD]));
  if (filters.length === 0) return null;

  const existing = await sbFetch(
    TABLE + '?or=(' + filters.join(',') + ')&select=' + ID_FIELD + ',' + PINNED_COL + '&limit=1',
    {{ method: 'GET', prefer: 'return=representation' }}
  );
  return existing[0] || null;
}}

// ── Search ──
let searchTimer;
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
const shortlistedNames = new Set({json.dumps([p.get(pf('name'), '') for p in shortlist])});

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
  try {{
    const enc = encodeURIComponent('%' + q + '%');
    const url = TABLE + '?or=(' + NAME_FIELD + '.ilike.' + enc + ',' + ORG_FIELD + '.ilike.' + enc + ',' + TITLE_FIELD + '.ilike.' + enc + ')&order=relevance_score.desc&limit=12&select=' + ID_FIELD + ',' + NAME_FIELD + ',' + TITLE_FIELD + ',' + ORG_FIELD + ',relevance_score,partnership_type,reasoning,tier,' + PINNED_COL;
    const data = await sbFetch(url, {{ method: 'GET', prefer: 'return=representation' }});
    renderSearchResults(data || []);
  }} catch (error) {{
    showSearchMessage('Search unavailable: ' + error.message);
  }}
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
    const scoreFg = score >= 80 ? '{org.color_primary}' : score >= 60 ? '#92400e' : '#4b5563';
    const scoreSpan = document.createElement('span');
    scoreSpan.className = 'sr-score';
    scoreSpan.style.background = scoreBg;
    scoreSpan.style.color = scoreFg;
    scoreSpan.textContent = score;
    nameDiv.appendChild(scoreSpan);
    nameDiv.appendChild(document.createTextNode(r[NAME_FIELD]));
    if (r.partnership_type) {{
      const typeSpan = document.createElement('span');
      typeSpan.className = 'tag';
      typeSpan.style.marginLeft = '8px';
      typeSpan.textContent = r.partnership_type.replace(/_/g, ' ');
      nameDiv.appendChild(typeSpan);
    }}
    info.appendChild(nameDiv);

    const meta = [r[TITLE_FIELD], r[ORG_FIELD]].filter(Boolean).join(' at ');
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

    const inBrief = shortlistedNames.has(r[NAME_FIELD]);
    const btn = document.createElement('button');
    btn.className = 'btn-pin';
    if (inBrief) {{
      btn.classList.add('already');
      btn.textContent = 'In brief';
    }} else if (r[PINNED_COL]) {{
      btn.classList.add('already');
      btn.textContent = 'Pinned';
    }} else {{
      btn.textContent = '+ ' + PRIMARY_USER + '\\'s Picks';
      btn.addEventListener('click', () => pinContact(r[ID_FIELD], btn));
    }}
    row.appendChild(btn);

    container.appendChild(row);
  }}
  container.classList.add('active');
}}

// ── Pin / Unpin ──
async function pinContact(contactId, btn) {{
  const originalLabel = btn.textContent;
  btn.textContent = 'Pinning...';
  btn.disabled = true;
  try {{
    const patch = {{ updated_at: new Date().toISOString() }};
    patch[PINNED_COL] = true;
    await sbFetch(TABLE + '?' + ID_FIELD + '=eq.' + contactId, {{
      method: 'PATCH',
      body: JSON.stringify(patch),
      prefer: 'return=minimal'
    }});
    btn.textContent = 'Pinned';
    btn.classList.add('already');
    await loadPicks();
  }} catch (error) {{
    btn.textContent = originalLabel;
    btn.disabled = false;
    alert('Could not pin contact: ' + error.message);
  }}
}}

async function unpinContact(contactId) {{
  try {{
    const patch = {{ updated_at: new Date().toISOString() }};
    patch[PINNED_COL] = false;
    await sbFetch(TABLE + '?' + ID_FIELD + '=eq.' + contactId, {{
      method: 'PATCH',
      body: JSON.stringify(patch),
      prefer: 'return=minimal'
    }});
    await loadPicks();
  }} catch (error) {{
    alert('Could not remove pick: ' + error.message);
  }}
}}

// ── Primary User's Picks ──
async function loadPicks() {{
  const data = await sbFetch(TABLE + '?' + PINNED_COL + '=eq.true&order=updated_at.desc&select=*', {{ method: 'GET', prefer: 'return=representation' }});
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
    card.id = 'pick-' + p[ID_FIELD];

    const score = p.relevance_score || 0;
    const scoreBg = score >= 80 ? '#dcfce7' : score >= 60 ? '#fef3c7' : '#f3f4f6';
    const scoreFg = score >= 80 ? '{org.color_primary}' : score >= 60 ? '#92400e' : '#4b5563';
    const ptype = (p.partnership_type || '').replace(/_/g, ' ');
    const meta = [p[TITLE_FIELD], p[ORG_FIELD]].filter(Boolean).join(' at ');
    const li = linkedinProfileUrl(p[LINKEDIN_FIELD]);

    // Build card using DOM methods
    const top = document.createElement('div');
    top.className = 'card-top';
    const avatar = document.createElement('div');
    avatar.className = 'avatar-placeholder';
    avatar.textContent = (p[FIRSTNAME_FIELD] || '?')[0];
    top.appendChild(avatar);

    const nameWrap = document.createElement('div');
    const nameLine = document.createElement('div');
    nameLine.className = 'card-name';
    nameLine.textContent = p[NAME_FIELD] + ' ';
    const badge = document.createElement('span');
    badge.className = 'tier-badge badge-pick';
    badge.textContent = PRIMARY_USER + "'s Pick";
    nameLine.appendChild(badge);
    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn-remove';
    removeBtn.textContent = 'Remove';
    removeBtn.addEventListener('click', () => unpinContact(p[ID_FIELD]));
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
      link.rel = 'noopener noreferrer';
      link.textContent = 'LinkedIn Profile';
      card.appendChild(link);
    }}

    const notesDiv = document.createElement('div');
    notesDiv.className = 'pick-notes';
    const notesLabel = document.createElement('strong');
    notesLabel.style.cssText = 'font-size:11px;color:#7c3aed';
    notesLabel.textContent = PRIMARY_USER.toUpperCase() + "'S NOTES";
    notesDiv.appendChild(notesLabel);
    const textarea = document.createElement('textarea');
    textarea.dataset.tid = p[ID_FIELD];
    textarea.placeholder = 'Add notes about this conversation...';
    textarea.value = p[NOTES_COL] || '';
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
    try {{
      const patch = {{ updated_at: new Date().toISOString() }};
      patch[NOTES_COL] = textarea.value;
      await sbFetch(TABLE + '?' + ID_FIELD + '=eq.' + tid, {{
        method: 'PATCH',
        body: JSON.stringify(patch),
        prefer: 'return=minimal'
      }});
    }} catch (error) {{
      console.error('Failed to save notes for', tid, error);
    }}
  }}, 800);
}}

// ── Add New Person (LinkedIn enrichment) ──
function openAddModal() {{
  document.getElementById('add-modal').classList.add('active');
  document.getElementById('linkedin-url-input').value = '';
  document.getElementById('enrich-status').textContent = '';
  document.getElementById('enrich-status').classList.remove('active');
  document.getElementById('btn-enrich').disabled = false;
  document.getElementById('btn-enrich').textContent = 'Enrich + Add';
  document.getElementById('linkedin-url-input').focus();
}}

function closeAddModal() {{
  document.getElementById('add-modal').classList.remove('active');
}}

async function enrichAndAdd() {{
  let normalizedUrl;
  try {{
    normalizedUrl = normalizeLinkedInUrl(document.getElementById('linkedin-url-input').value);
  }} catch (error) {{
    alert(error.message);
    return;
  }}
  const btn = document.getElementById('btn-enrich');
  const status = document.getElementById('enrich-status');
  btn.disabled = true;
  btn.textContent = 'Working...';
  status.textContent = 'Scraping LinkedIn profile and scoring for ' + ORG_NAME + ' fit... (~30-90 seconds)';
  status.classList.add('active');

  try {{
    const resp = await fetch(SB_URL + '/functions/v1/' + EDGE_FN, {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        'apikey': SB_KEY,
        'Authorization': 'Bearer ' + SB_KEY
      }},
      body: JSON.stringify({{ linkedin_url: normalizedUrl }})
    }});
    if (!resp.ok) {{
      throw new Error(await readErrorResponse(resp, 'Enrichment failed'));
    }}
    const result = await resp.json();
    const attendeePayload = {{
      ...result,
      updated_at: new Date().toISOString(),
      partnership_types: JSON.stringify(result.partnership_types || [])
    }};
    attendeePayload[LINKEDIN_FIELD] = result[LINKEDIN_FIELD] || normalizeLinkedInSlug(normalizedUrl);
    attendeePayload[PINNED_COL] = true;
    status.textContent = 'Scored ' + attendeePayload[NAME_FIELD] + ' (' + attendeePayload.relevance_score + '/100). Saving...';

    const existing = await findExistingAttendee(attendeePayload);
    if (existing) attendeePayload[ID_FIELD] = existing[ID_FIELD];

    if (existing) {{
      await sbFetch(TABLE + '?' + ID_FIELD + '=eq.' + existing[ID_FIELD], {{
        method: 'PATCH',
        body: JSON.stringify(attendeePayload),
        prefer: 'return=minimal'
      }});
    }} else {{
      await sbFetch(TABLE, {{
        method: 'POST',
        body: JSON.stringify(attendeePayload),
        prefer: 'return=minimal'
      }});
    }}

    closeAddModal();
    await loadPicks();
    searchInput.value = attendeePayload[NAME_FIELD];
    await searchAttendees(attendeePayload[NAME_FIELD]);
  }} catch (e) {{
    status.textContent = 'Error: ' + e.message;
    status.classList.add('active');
    btn.disabled = false;
    btn.textContent = 'Retry';
  }}
}}

document.getElementById('add-modal').addEventListener('click', (event) => {{
  if (event.target.id === 'add-modal') closeAddModal();
}});

document.getElementById('linkedin-url-input').addEventListener('keydown', (event) => {{
  if (event.key === 'Enter') {{
    event.preventDefault();
    enrichAndAdd();
  }}
}});

document.addEventListener('keydown', (event) => {{
  if (event.key === 'Escape') {{
    closeAddModal();
    searchResults.classList.remove('active');
  }}
}});

// ── Load state on page load ──
document.addEventListener('DOMContentLoaded', async () => {{
  try {{
    // Load state from table for shortlisted contacts
    const names = Array.from(shortlistedNames);
    const stateMap = {{}};
    for (let i = 0; i < names.length; i += 50) {{
      const chunk = names.slice(i, i + 50);
      const orClause = chunk.map(n => NAME_FIELD + '.eq.' + encodeURIComponent(n)).join(',');
      const data = await sbFetch(TABLE + '?or=(' + orClause + ')&select=' + NAME_FIELD + ',' + REACHED_COL + ',' + CONTEXT_COL, {{ method: 'GET', prefer: 'return=representation' }});
      (data || []).forEach(row => {{ stateMap[row[NAME_FIELD]] = row; }});
    }}

    // Restore outreach toggles
    document.querySelectorAll('.outreach-toggle').forEach(el => {{
      const name = el.dataset.contact;
      const row = stateMap[name];
      if (row && row[REACHED_COL]) {{
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
      if (row && row[CONTEXT_COL]) {{
        ta.value = row[CONTEXT_COL];
        const counter = ta.parentElement.querySelector('.ctx-count');
        if (counter) counter.textContent = row[CONTEXT_COL].length;
      }}
    }});

    // Load Primary User's Picks
    await loadPicks();
  }} catch (e) {{
    console.error('Failed to load state:', e);
  }}
}});
</script>
</body>
</html>''')

    # Write output
    output_path = args.output
    if not output_path:
        deploy_dir = Path(config.vercel.deploy_dir)
        if not deploy_dir.is_absolute():
            deploy_dir = REPO_ROOT / deploy_dir
        deploy_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(deploy_dir / 'index.html')

    with open(output_path, 'w') as f:
        f.write('\n'.join(parts))

    file_size = len('\n'.join(parts))
    print(f"\nLookbook generated: {output_path}")
    print(f"  File size: {file_size:,} bytes")
    for t in sorted(tiers_data.keys()):
        tc = config.tiers.get(t)
        lbl = tc.label if tc else f'Tier {t}'
        card_type = "cards" if t <= 2 else "compact cards"
        print(f"  Tier {t} ({lbl}): {len(tiers_data[t])} {card_type}")
    print(f"  Quick ref rows: {total_shortlisted}")


if __name__ == "__main__":
    main()
