#!/usr/bin/env python3
"""
Seed the ff_ic_judges table with all 33 researched judge candidates
for the Flourish Fund Innovation Challenge.

Usage:
  python scripts/intelligence/seed_ff_judges.py
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

JUDGES = [
    # ── TIER 1: READY TO GO ──────────────────────────────────────────
    {
        "name": "Michael Allen",
        "organization": "Together Chicago / Together South Florida",
        "category": "donor_stakeholder",
        "tier": "tier_1_ready",
        "linkedin_url": "https://www.linkedin.com/in/michael-allen-a2358243/",
        "role_title": "Co-Founder & Senior Advisor, Together Chicago; Co-Founder & CEO, Together South Florida; Flourish Fund Board Member",
        "relationship": "FF Board Member — already asked to serve as judge",
        "foster_care_connection": "Together Chicago's work on empowering inner-city families intersects with foster care prevention. Board member of Flourish Fund with institutional knowledge of the Innovation Challenge.",
        "outreach_hook": "He already requested to judge. Just confirm and formalize.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 1,
        "first_round_ask": True,
        "research_profile": {
            "bio": "Born in Kingston, Jamaica; immigrated to Florida 1977; became U.S. citizen 1986. Former Assistant Pastor at The Moody Church (1997-2002). Senior Pastor at Uptown Baptist Church, Chicago (2005-2020). Vice Chairman of Pacific Garden Mission board since 1998. Praxis community member.",
            "foster_care_relevance": "Together Chicago focuses on violence reduction, economic development, gospel justice, education, and faith community mobilization — all intersecting with foster care prevention.",
            "recent_activity": "Leading Together South Florida as new venture. Active in Praxis community for social innovation."
        }
    },
    {
        "name": "Mike Winters",
        "organization": None,
        "category": "donor_stakeholder",
        "tier": "tier_1_ready",
        "linkedin_url": None,
        "role_title": "Philanthropist / Donor",
        "relationship": "Justin/Mike had a great conversation — he wanted to know more about the IC. Verbal $200K commitment pending.",
        "foster_care_connection": "Engaged enough with foster care innovation to consider a $200K investment in the Innovation Challenge.",
        "outreach_hook": "Already warm, pending $200K commitment. Judging deepens engagement and likely solidifies financial commitment.",
        "recommended_sender": "Justin Steele",
        "outreach_wave": 1,
        "first_round_ask": True,
        "research_profile": {
            "bio": "Philanthropist with verbal commitment of $200,000 to the Flourish Fund Innovation Challenge (not yet finalized), which would bring the total from $600K to $800K.",
            "foster_care_relevance": "Direct financial supporter of foster care innovation.",
            "recent_activity": "Had productive conversation with Justin about the Innovation Challenge; expressed interest in deeper involvement."
        }
    },
    {
        "name": "Nathan Aleman",
        "organization": "Bridgespan Group",
        "category": "donor_stakeholder",
        "tier": "tier_1_ready",
        "linkedin_url": None,
        "role_title": "Consultant, The Bridgespan Group (formerly Seneca Family of Agencies)",
        "relationship": "DV has a call with Nathan on 2/24",
        "foster_care_connection": "Spent seven years at Seneca Family of Agencies working directly with foster care children and families in wraparound programs and therapeutic behavioral services. Now at Bridgespan advising philanthropies on deploying capital effectively.",
        "outreach_hook": "Combination of direct foster care service experience and strategic consulting is exactly the lens needed. He's seen the system from the inside and understands what it takes for an intervention to work at scale.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 1,
        "first_round_ask": True,
        "research_profile": {
            "bio": "Seven years at Seneca Family of Agencies working directly with foster care children and families. Now consulting at The Bridgespan Group advising philanthropies on effective capital deployment.",
            "foster_care_relevance": "Direct service experience in wraparound programs and therapeutic behavioral services for foster children. Strategic consulting on philanthropic capital deployment.",
            "recent_activity": "Scheduled call with DV on 2/24."
        }
    },
    {
        "name": "Wes Hartley",
        "organization": "Eagle Ventures",
        "category": "donor_stakeholder",
        "tier": "tier_1_ready",
        "linkedin_url": None,
        "role_title": "Eagle Ventures Partner",
        "relationship": "Per partnership MOU, Eagle Ventures has a judging seat",
        "foster_care_connection": "Eagle Ventures is funding the $100K social enterprise track of the Innovation Challenge.",
        "outreach_hook": "MOU-guaranteed seat. Just confirm which EV partner (Wes, Vip, or Wade) will fill it.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 1,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Partner at Eagle Ventures. Funding the social enterprise track ($100K) of the Innovation Challenge.",
            "foster_care_relevance": "Social enterprise funding partner for foster care innovation.",
            "recent_activity": "Active partnership with Flourish Fund per MOU."
        }
    },

    # ── TIER 2: WARM CONNECTIONS ─────────────────────────────────────
    {
        "name": "Tim Tebow",
        "organization": "Tim Tebow Foundation",
        "category": "celebrity",
        "tier": "tier_2_warm",
        "linkedin_url": "https://www.linkedin.com/in/timtebow15/",
        "role_title": "Founder & Chairman, Tim Tebow Foundation; ESPN/SEC Network Analyst",
        "relationship": "Wes / Vip (Eagle Ventures connection)",
        "foster_care_connection": "Foundation's Orphan Care program provides care for 2,700+ orphans worldwide. DISRUPT initiative fights human trafficking in 12+ countries. Supported foster care system development in Honduras. Currently championing Renewed Hope Act of 2026. Testified before Congress on child exploitation.",
        "outreach_hook": "Foundation already uses tech in DISRUPT initiative to assist law enforcement. Current legislative push (Renewed Hope Act) shows active engagement in innovation for child welfare.",
        "recommended_sender": "Wes Hartley or Vip",
        "outreach_wave": 3,
        "first_round_ask": True,
        "research_profile": {
            "bio": "Former NFL quarterback, 2x NCAA champion, Heisman winner, CFB Hall of Fame. Founded Tim Tebow Foundation 2010 in Jacksonville, FL. 6x NYT bestselling author. Married to Demi-Leigh Tebow (former Miss Universe 2017).",
            "foster_care_relevance": "Orphan Care: 2,700+ orphans; DISRUPT: anti-trafficking in 12+ countries; Renewed Hope Act 2026; Congressional testimony on child exploitation; Honduras foster care system development.",
            "recent_activity": "Night to Shine 2026 (Feb 13) expanded to 975 churches in 50 states, 74 countries, 100K+ guests. Actively lobbying for Renewed Hope Act. Washington Times profile Feb 24, 2026.",
            "philanthropy": "ECFA-accredited foundation. Focus: anti-trafficking, orphan care, Night to Shine (special needs), Timmy's Playrooms (children's hospitals)."
        }
    },
    {
        "name": "Chris Tomlin",
        "organization": "For Others",
        "category": "celebrity",
        "tier": "tier_2_warm",
        "linkedin_url": None,
        "role_title": "Worship Leader / Recording Artist; Co-Founder & Chairman, For Others",
        "relationship": "DV to ask Jared",
        "foster_care_connection": "Founded For Others (originally Angel Armies) in 2019 with wife Lauren — dedicated to ending the child welfare crisis in America. 2nd Annual Troubadour For Others Vision Gathering raised over $12 million. Good Friday Nashville is now the largest faith-driven benefit concert (Bridgestone Arena, 10th year). Partners include CHOSEN, MyFloridaMyFamily. NEEDTOBREATHE donates $1/ticket to For Others.",
        "outreach_hook": "For Others is the most directly relevant organization on the list. The Innovation Challenge is a direct extension of For Others' mission — evaluating technologies that could accelerate what they're trying to accomplish.",
        "recommended_sender": "Jared (via DV)",
        "outreach_wave": 3,
        "first_round_ask": True,
        "research_profile": {
            "bio": "One of the most prolific worship songwriters in history. ASCAP recognized as one of the most-sung songwriters in the world. Multiple Grammy/Dove Award winner. Lives in Nashville with wife Lauren and daughters. Founded Troubadour Golf & Field Club.",
            "foster_care_relevance": "Founded For Others — largest faith-based foster care nonprofit collective. Raised $12M+. Good Friday Nashville (10th year). Board: Chris Tomlin (Chairman), Lauren Tomlin, Colt McCoy, David Nasser (President).",
            "recent_activity": "Good Friday Nashville 2025 sold out Bridgestone Arena (largest ticketed Christian concert ever). GFN 2026 (April 3) already 60% sold. Released 'Jesus Saves' EP. 2026 tour with For Others integrations.",
            "philanthropy": "For Others (primary), Compassion International, World Vision partnerships."
        }
    },
    {
        "name": "Connie Ballmer",
        "organization": "Ballmer Group",
        "category": "donor_stakeholder",
        "tier": "tier_2_warm",
        "linkedin_url": None,
        "role_title": "Co-Founder, Ballmer Group",
        "relationship": "Justin on an ongoing thread with Ballmer leaders",
        "foster_care_connection": "Foster care is the ORIGIN of Ballmer Group's philanthropic work. First grants centered on child welfare. Funded Child Well-Being Portal. Co-founded Partners for Our Children in 2006 with $10M. Deep investments in child welfare, behavioral health, education in Washington state. 2025: committed additional $1 billion for early childhood education.",
        "outreach_hook": "Ballmer Group's emphasis on data-driven, technology-enabled approaches is exactly the lens this panel needs. May designate a senior Ballmer Group program officer rather than serving personally.",
        "recommended_sender": "Justin Steele",
        "outreach_wave": 5,
        "first_round_ask": True,
        "research_profile": {
            "bio": "Native of Oregon; BS journalism. Wife of Steve Ballmer (former Microsoft CEO). Co-founded Ballmer Group 2015. Founding investor/GP at Blue Meridian Partners. Obama Foundation board member. Co-Founder of Rainier Climate.",
            "foster_care_relevance": "Foster care is Ballmer Group's founding cause. Partners for Our Children ($10M), Child Well-Being Portal, $1B early childhood commitment 2025.",
            "recent_activity": "$1 billion commitment for Washington state early childhood education (2025). Ongoing Blue Meridian Partners and Ballmer Group grantmaking."
        }
    },
    {
        "name": "JooYeun Chang",
        "organization": "The Aviv Foundation",
        "category": "donor_stakeholder",
        "tier": "tier_2_warm",
        "linkedin_url": "https://www.linkedin.com/in/jooyeun-chang/",
        "role_title": "Managing Director, The Aviv Foundation",
        "relationship": None,
        "foster_care_connection": "Child welfare is her entire career. Ran Michigan's Children's Services Agency (state child welfare system) where she launched a comprehensive child welfare technology system. Acting Assistant Secretary at ACF/HHS overseeing $72.2B in pandemic relief. Director of Child Well-Being at Doris Duke Foundation. Senior Director at Casey Family Programs. At Aviv: manages Springboard Prize for Child Welfare ($400K award). Aviv-Doris Duke $33M joint prevention initiative.",
        "outreach_hook": "Most substantively qualified person on the list. Has run innovation challenges (Springboard Prize), managed child welfare tech system builds (Michigan), and operated at federal policy level. Her participation gives the IC enormous credibility.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 2,
        "first_round_ask": True,
        "research_profile": {
            "bio": "Emigrated from Korea at age 3. BA from NC State; JD from University of Miami. 20+ years transforming child welfare systems. Career: Casey Family Programs → Doris Duke Foundation → Michigan Children's Services Agency Director → ACF/HHS Acting Assistant Secretary → Aviv Foundation Managing Director.",
            "foster_care_relevance": "Entire career in child welfare. Launched child welfare tech system in Michigan. $72.2B pandemic relief oversight. Springboard Prize ($400K). Aviv-Doris Duke $33M prevention initiative.",
            "recent_activity": "Aviv-Doris Duke $33M joint initiative. Testified before U.S. Senate Finance Committee on child welfare transformation."
        }
    },
    {
        "name": "Sixto Cancel",
        "organization": "Think of Us",
        "category": "lived_experience",
        "tier": "tier_2_warm",
        "linkedin_url": "https://www.linkedin.com/in/sixto-cancel-92425233/",
        "role_title": "CEO, Think of Us",
        "relationship": "Justin has had several conversations with Sixto over the years — Dan saw him at the White House in November",
        "foster_care_connection": "Former foster youth. Founded Think of Us — leading child welfare technology nonprofit reshaping how federal and state agencies approach child welfare data and technology. Advised the White House, HHS, and multiple states on foster care technology modernization. Dual perspective: lived experience plus deep systems knowledge.",
        "outreach_hook": "Most innovation challenges get evaluated by people who've never been in the system. Sixto has. Plus he's built an organization reshaping federal/state approaches to child welfare tech. Fostering the Future EO aligns with this challenge.",
        "recommended_sender": "Justin Steele or Dan Vander Ploeg",
        "outreach_wave": 3,
        "first_round_ask": True,
        "research_profile": {
            "bio": "Former foster youth. Founded Think of Us to push child welfare sector to listen to the people it serves. Has advised White House, HHS, multiple state agencies on child welfare technology modernization.",
            "foster_care_relevance": "Former foster youth. CEO of leading child welfare tech nonprofit. Federal policy advisor. Lived experience + systems expertise.",
            "recent_activity": "Dan saw him at the White House in November 2025. Fostering the Future EO aligns with Think of Us mission."
        }
    },
    {
        "name": "Bill Haslam",
        "organization": "Bill and Crissy Haslam Foundation",
        "category": "subject_matter_expert",
        "tier": "tier_2_warm",
        "linkedin_url": "https://www.linkedin.com/in/bill-haslam-02bb1590/",
        "role_title": "Former Governor of Tennessee; Majority Owner, Nashville Predators; Philanthropist",
        "relationship": "They are sponsors of the Understory and will be there in May",
        "foster_care_connection": "As governor, made foster care a signature policy priority. Launched TNFosters with Crissy — resulted in 40.8% increase in certified foster families, 116 children placed in forever families in first year. Made TN first state to offer comprehensive help to every aging-out youth (YVLifeSet expansion). TNFosters became national model.",
        "outreach_hook": "Proved in Tennessee that government-private-faith partnerships can transform foster care at scale. Already planning to be at The Understory on May 17. Can evaluate from both policy implementation and business sustainability angles.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 2,
        "first_round_ask": True,
        "research_profile": {
            "bio": "49th Governor of Tennessee (2011-2019). Mayor of Knoxville. Billionaire (Pilot Flying J family). Author of 'Faithful Presence' (2021). Honorary Chair of The Adoption Project Founder's Committee. $1M endowed scholarship at Belmont's Frist College of Medicine (Feb 2025).",
            "foster_care_relevance": "TNFosters: 40.8% increase in certified foster families, 116 placements year 1. YVLifeSet statewide expansion. Every Child TN legacy. Dave Thomas Foundation involvement.",
            "recent_activity": "Became majority owner of Nashville Predators (July 2025). Active philanthropy through Haslam Foundation."
        }
    },
    {
        "name": "Crissy Haslam",
        "organization": "Bill and Crissy Haslam Foundation",
        "category": "subject_matter_expert",
        "tier": "tier_2_warm",
        "linkedin_url": None,
        "role_title": "Former First Lady of Tennessee; Philanthropist; Board Member, Tennessee Kids Belong",
        "relationship": "Sponsors of the Understory, will be there in May",
        "foster_care_connection": "Co-launched TNFosters. Public face of the initiative. Continues on Tennessee Kids Belong board. Priorities: parent engagement, reading proficiency, foster care advocacy, empowering women/families/orphans. Collaborated with Chris Tomlin on TNFosters promotion.",
        "outreach_hook": "Was the driving force behind TNFosters and continued through Tennessee Kids Belong and The Adoption Project. Understands what it takes to mobilize communities around foster care.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 2,
        "first_round_ask": True,
        "research_profile": {
            "bio": "First Lady of Tennessee 2011-2019. Board: Tennessee Kids Belong, UT Medical Center, Dollywood Foundation, Knoxville Education Foundation, Redeemer City to City. Chair, TN Executive Residence Foundation. Honorary Chair, The Adoption Project Policy Committee.",
            "foster_care_relevance": "Co-led TNFosters. Tennessee Kids Belong board. Collaborated with Chris Tomlin on promotion.",
            "recent_activity": "Active board service. $1M scholarship at Belmont medical school (Feb 2025) through Haslam Foundation."
        }
    },
    {
        "name": "Josh Yates",
        "organization": "Belmont Innovation Labs / Belmont University",
        "category": "donor_stakeholder",
        "tier": "tier_2_warm",
        "linkedin_url": "https://www.linkedin.com/in/josh-yates-12188016a/",
        "role_title": "VP for Strategy and Innovation, Belmont University; Executive Director, Belmont Innovation Labs; Founder & CEO, Thriving Cities Group",
        "relationship": "Given how they included us in their judging panel, would we want to reciprocate?",
        "foster_care_connection": "Launched Reconstruct Challenge: Thriving Youth — $1M+ venture philanthropy initiative for aging-out foster youth in Tennessee. 2026 challenge selected 6 orgs from 58 applicants across 11 states, each receiving $100K. Developed through Thriving Youth Executive Leadership Council with TN DCS, Governor's Faith-Based Initiative.",
        "outreach_hook": "Reciprocity: Flourish was included in Belmont's Reconstruct Challenge judging. He's literally just run a $1M foster care innovation challenge. Concept of 'traditioned innovation' describes exactly what FF is looking for.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 2,
        "first_round_ask": False,
        "research_profile": {
            "bio": "PhD from UVA; MA from UVA; BA from University of Montana. Cultural/community sociologist with two decades of research and practice. Promoted to VP at Belmont 2025. Developed Human Ecology Framework and Community Craft curriculum.",
            "foster_care_relevance": "Reconstruct Challenge: $1M+ for aging-out foster youth. 6 winners selected 2026. Foster Care Lab at Belmont. Landscape study: 70-80% of aging-out youth face homelessness, addiction, incarceration within 3 years.",
            "recent_activity": "2026 Reconstruct Challenge winners announced. Promoted to VP for Strategy and Innovation at Belmont."
        }
    },
    {
        "name": "Tom Baldwin",
        "organization": "Belmont Innovation Labs / Belmont University",
        "category": "donor_stakeholder",
        "tier": "tier_2_warm",
        "linkedin_url": "https://www.linkedin.com/in/tombbaldwin/",
        "role_title": "Director of Strategy & Development, Belmont Innovation Labs",
        "relationship": "Reciprocity opportunity (Belmont included Flourish in their panel)",
        "foster_care_connection": "Led landscape study on aging-out foster youth in Tennessee. Operational driver of Belmont's foster care work. Left corporate world (Mars, Stanley Black & Decker) to join Belmont Innovation Lab, driven by passion for foster youth. Direct conversations with former foster youth.",
        "outreach_hook": "Corporate innovation background (Mars, SBD) means he can evaluate scalability. Conversations with foster youth give ground-level credibility. Already supported Reconstruct Challenge from application review through winner selection.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 2,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Two decades of business leadership at Mars and Stanley Black & Decker. MBA from Loyola College; BA Marketing from Texas Tech (student athlete). Left corporate to join Belmont Innovation Lab. Based in Nashville.",
            "foster_care_relevance": "Led TN foster care landscape study. Direct conversations with foster youth. Operational driver of Reconstruct Challenge.",
            "recent_activity": "Published 2025 Belmont Innovation Labs impact case on foster care. Supporting 2026 Reconstruct Challenge winners as they begin pilots."
        }
    },
    {
        "name": "Audrey Haque",
        "organization": "Haque Family Foundation",
        "category": "donor_stakeholder",
        "tier": "tier_2_warm",
        "linkedin_url": None,
        "role_title": "Principal, Haque Family Foundation (likely)",
        "relationship": "Inviting Audrey to judge could be a great way to deepen our relationship with her",
        "foster_care_connection": "Not publicly documented. Donor cultivation opportunity — Haque Family Foundation provides $3M/year in grants. Family's Silicon Valley tech background (Promod Haque at Norwest Venture Partners) means deep understanding of technology and innovation.",
        "outreach_hook": "Donor cultivation play. Silicon Valley tech background brings product-market fit, scalability, and technical feasibility lens. $3M/year foundation. Judge role deepens relationship.",
        "recommended_sender": "Dan Vander Ploeg or Justin Steele",
        "outreach_wave": 2,
        "first_round_ask": True,
        "research_profile": {
            "bio": "Associated with Saratoga, CA. Haque Family Foundation: $3M in grants (2023). Connected to Promod Haque — Senior Managing Partner at Norwest Venture Partners, Forbes Midas List #1 (2004), $40B+ in portfolio exits.",
            "foster_care_relevance": "Not direct — but family's VC/tech background brings valuable evaluation lens for tech innovation challenge.",
            "recent_activity": "Haque Family Foundation continues active grantmaking at $3M/year level."
        }
    },
    {
        "name": "Sarah Gesiriech",
        "organization": "Office of the First Lady",
        "category": "subject_matter_expert",
        "tier": "tier_2_warm",
        "linkedin_url": "https://www.linkedin.com/in/sarahgesiriech/",
        "role_title": "Special Assistant to the President / Director of Policy, Office of the First Lady",
        "relationship": None,
        "foster_care_connection": "25+ years in child and family policy. Architect of the Fostering the Future executive order (Nov 2025). Career: legislative assistant for Sen. Grassley → U.S. Special Advisor on Children in Adversity → Casey Family Programs → Dave Thomas Foundation → Faith to Action Initiative → ACF/HHS → Office of the First Lady. The EO specifically calls for technology and public-private partnerships for foster youth.",
        "outreach_hook": "The Fostering the Future EO she helped craft calls for harnessing technology and public-private partnerships — almost a word-for-word description of the Innovation Challenge. 25 years of navigating the full policy/philanthropy/advocacy landscape.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 2,
        "first_round_ask": True,
        "research_profile": {
            "bio": "BA International Relations, Drake University. Career began with Sen. Chuck Grassley. U.S. Special Advisor on Children in Adversity. Co-authored 'A Child's Journey Through the Child Welfare System'. Founded 127 Global Strategies consultancy.",
            "foster_care_relevance": "Architect of Fostering the Future EO. 25+ years across Casey Family Programs, Dave Thomas Foundation, USAID, ACF/HHS, White House.",
            "recent_activity": "Fostering the Future EO signed Nov 13, 2025 — most significant federal foster care policy action in recent memory. HUD and Treasury now building on the initiative."
        }
    },
    {
        "name": "Steve Moore",
        "organization": "M.J. Murdock Charitable Trust",
        "category": "subject_matter_expert",
        "tier": "tier_2_warm",
        "linkedin_url": "https://www.linkedin.com/in/steve-moore-80b4154/",
        "role_title": "CEO Emeritus, M.J. Murdock Charitable Trust",
        "relationship": None,
        "foster_care_connection": "Led Murdock Trust 16 years. Oversaw 4,400+ grants totaling $771 million to 2,000+ organizations. Trust has funded foster care orgs including Olive Crest (2nd largest child placement agency in WA). Fall 2025 grants: $30.8M across 112 grants.",
        "outreach_hook": "After evaluating thousands of grant applications, he can distinguish between a compelling pitch and a genuinely sustainable organization. Instinct for spotting the difference between ideas that sound good on paper vs. ones that deliver impact over time.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 2,
        "first_round_ask": True,
        "research_profile": {
            "bio": "PhD. Prior career in academia: Texas Tech, Baylor, Seattle Pacific, Asbury Theological Seminary. Led Murdock Trust 16 years as CEO/Executive Director. Trust serves Pacific Northwest (AK, ID, MT, OR, WA). Received honorary degree from University of Portland.",
            "foster_care_relevance": "4,400+ grants, $771M. Funded Olive Crest and other foster care organizations. Focus on faith/innovation intersection.",
            "recent_activity": "CEO Emeritus capacity. Murdock Trust remains one of largest Pacific NW foundations."
        }
    },

    # ── TIER 3: WARM INTROS NEEDED ───────────────────────────────────
    {
        "name": "David Platt",
        "organization": "McLean Bible Church / Radical",
        "category": "celebrity",
        "tier": "tier_3_intro_needed",
        "linkedin_url": None,
        "role_title": "Lead Pastor, McLean Bible Church; Founder, Radical",
        "relationship": "Cold outreach / or through Project Belong? Christian Pinkston or Jedd could help",
        "foster_care_connection": "Four of six children are adopted (Kazakhstan, China, others). Called Shelby County DHR, asked how many families needed — they said 150 — and 160+ families signed up from his congregation. Former President of International Mission Board (SBC). Counter Culture book addresses orphan care as core Christian calling.",
        "outreach_hook": "Most personally invested person on the list. Has mobilized an entire church to cover a county's foster care needs. Four adopted children. Technology can help scale the kind of church mobilization he pioneered.",
        "recommended_sender": "Christian Pinkston, Jedd, or DV",
        "outreach_wave": 3,
        "first_round_ask": True,
        "research_profile": {
            "bio": "BA from UGA; MDiv, ThM, PhD from NOBTS. Author: Radical, Counter Culture, Something Needs to Change, Don't Hold Back. At 26, became youngest megachurch pastor in America (Brook Hills, Birmingham). Lives in D.C. metro with wife Heather and six children.",
            "foster_care_relevance": "4 adopted children. Mobilized 160+ families in Shelby County for foster care. Orphan care theology through Radical.",
            "recent_activity": "Continues leading McLean Bible Church. Active through Radical.net publishing podcasts and adoption theology."
        }
    },
    {
        "name": "Simone Biles",
        "organization": "Friends of the Children",
        "category": "celebrity",
        "tier": "tier_3_intro_needed",
        "linkedin_url": "https://www.linkedin.com/in/simone-biles-4bbb43221/",
        "role_title": "Olympic Gymnast; National Ambassador, Friends of the Children",
        "relationship": "Spent time in foster care as a child",
        "foster_care_connection": "Lived in foster care from age 3 to 6. Biological mother struggled with addiction. Adopted by grandparents at age 6. CNN op-ed: 'I went from foster care to the Olympics.' National ambassador for Friends of the Children. Hosts foster youth at her gym. Most recognizable name with lived foster care experience.",
        "outreach_hook": "Most people evaluating foster care technology have studied the system from the outside. She was in it. Can assess whether solutions would have actually helped a kid like her. Name brings mainstream media attention beyond faith community.",
        "recommended_sender": "Through management/agent",
        "outreach_wave": 4,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Born March 14, 1997, Columbus OH. 37 Olympic and World Championship medals (most decorated gymnast ever). 2024 Paris: 3 golds, 1 silver. SI 2024 Sportsperson of the Year. Married to Jonathan Owens (NFL). World Champions Centre gym in Spring, TX.",
            "foster_care_relevance": "Lived in foster care ages 3-6. Adopted by grandparents. National ambassador for Friends of the Children. CNN op-ed on foster care.",
            "recent_activity": "FOTC ambassador: hosted youth at gym, gifted Olympic medal. HIMSS25 keynote (March 2025). Joined Religion of Sports as creative partner/board member (Feb 2025). National Mentoring Month spotlight (Jan 2025)."
        }
    },
    {
        "name": "Bear Rinehart",
        "organization": "NEEDTOBREATHE / NEEDTOBREATHE Cares",
        "category": "celebrity",
        "tier": "tier_3_intro_needed",
        "linkedin_url": None,
        "role_title": "Lead Singer & Guitarist, NEEDTOBREATHE; Solo Artist (Wilder Woods)",
        "relationship": None,
        "foster_care_connection": "Active partner with For Others (Chris Tomlin's nonprofit). Donated $1.1M+ to For Others through ticket sales ($1/ticket). Speaks about foster care from stage. Families have started licensing process after hearing him speak at concerts. NEEDTOBREATHE Cares has raised $10M+ for charitable causes since 2014.",
        "outreach_hook": "Brings audience most people in child welfare can't reach: young families open to fostering. Already deeply embedded in For Others ecosystem. Connection to Chris Tomlin makes this natural.",
        "recommended_sender": "Through For Others / Chris Tomlin network",
        "outreach_wave": 4,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Born William Stanley 'Bear' Rinehart III, Sep 6, 1980, Seneca SC. Former Furman University football WR. Co-founded NEEDTOBREATHE with brother Bo. Grammy-nominated. Launched Wilder Woods solo career 2019. Married to Reames Rinehart.",
            "foster_care_relevance": "$1.1M+ donated to For Others. Speaks from stage about foster care. Inspired families to become foster parents. Attended For Others Founder's Retreat.",
            "recent_activity": "The Barely Elegant Acoustic Tour (2026) with $1/ticket to For Others. Private Concerts for a Cause benefiting For Others and OneWorld Health."
        }
    },
    {
        "name": "Kirk Franklin",
        "organization": "The Franklin Imagine Group",
        "category": "celebrity",
        "tier": "tier_3_intro_needed",
        "linkedin_url": None,
        "role_title": "Gospel Musician, Producer; Founder, The Franklin Imagine Group",
        "relationship": None,
        "foster_care_connection": "Personal lived experience: abandoned by teenage mother at age 3, adopted by great-aunt Gertrude Franklin (64-year-old widow who collected aluminum cans for piano lessons). BET Ultimate Icon Award 2025 speech honored 'a 64-year-old woman who chose to adopt a boy nobody wanted.' Named publishing company Aunt Gertrude Music Publishing. Documentary 'Father's Day' about reuniting with biological father after 53 years.",
        "outreach_hook": "Most emotionally powerful adoption narrative on the list. His BET Awards speech honoring Gertrude resonated with millions. 400,000+ kids need their own Aunt Gertrude. His story reminds every innovator why this work matters.",
        "recommended_sender": "Through management/agent",
        "outreach_wave": 4,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Born Kirk Smith, Jan 26, 1970, Fort Worth TX. Adopted by great-aunt Gertrude at age 4. Church choir leader at 11. Multiple Grammy winner. Most commercially successful gospel artist of all time. Documentary: 'Father's Day: A Kirk Franklin Story' (2023).",
            "foster_care_relevance": "Adopted from foster/kinship care. Entire life narrative is transformation through one committed adult. Youth mentoring through TFIG.",
            "recent_activity": "BET Ultimate Icon Award (June 2025). Compassion International collaboration: 'Lean on Me' re-release with 120+ youth from 25 countries. TFIG youth arts camps continue."
        }
    },
    {
        "name": "Christian Bale",
        "organization": "Together California",
        "category": "celebrity",
        "tier": "tier_3_intro_needed",
        "linkedin_url": None,
        "role_title": "Actor; Co-Founder, Together California",
        "relationship": None,
        "foster_care_connection": "Co-founded Together California with Tim McCormick and Dr. Eric Esrailian. Spent 16 years building a $22M foster care village in Palmdale, CA. Designed to keep siblings in foster care together. 12 townhouse foster homes, 2 studio apartments for aging-out youth, 7,000 sq ft community center. Broke ground Feb 2024. First homes opening late 2025/early 2026.",
        "outreach_hook": "Deepest, most hands-on involvement in foster care infrastructure of anyone on the list. 16 years building a physical solution. Not a celebrity lending his name — a practitioner. He's built the physical infrastructure; this challenge is about the digital/systemic infrastructure.",
        "recommended_sender": "Through representatives or Dr. Esrailian / Tim McCormick",
        "outreach_wave": 4,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Born Jan 30, 1974, Haverfordwest, Wales. Academy Award winner (The Fighter). Dark Knight trilogy, American Hustle, Vice, The Big Short. Very private personal life. Passion for foster care since daughter's birth in 2005.",
            "foster_care_relevance": "16 years developing Together California. $22M foster village in Palmdale to keep siblings together. CBS Sunday Morning profiled. First homes opening late 2025/early 2026.",
            "recent_activity": "Together California pilot launch: first homes expected Dec 2025/Jan 2026. CBS Sunday Morning profile. TikTok went viral."
        }
    },
    {
        "name": "Debra Waller",
        "organization": "Jockey International / Jockey Being Family Foundation",
        "category": "donor_stakeholder",
        "tier": "tier_3_intro_needed",
        "linkedin_url": None,
        "role_title": "Chairman & CEO, Jockey International Inc.",
        "relationship": None,
        "foster_care_connection": "Adopted as infant. Founded Jockey Being Family Foundation in 2005 to strengthen adoptive families. Impacted 350,000+ families with post-adoption support. Board member of Dave Thomas Foundation for Adoption. Named to Top 100 Adoption-Friendly Workplaces 5+ years. Jockey joined the For Others network (WinShape/Chick-fil-A ecosystem).",
        "outreach_hook": "Rare combination: Fortune-level CEO who can evaluate scalability + personally adopted, so she can evaluate whether solutions actually serve the child. Most judges bring one lens; she brings both.",
        "recommended_sender": "DV or through For Others / WinShape network",
        "outreach_wave": 3,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Adopted as infant into family owning Cooper's Underwear Co. (now Jockey International). Former teacher. Joined Jockey 1982 as admin assistant; rose to Chairman & CEO 2001. Founded Jockey Being Family 2005. Wisconsin's 275 Most Influential.",
            "foster_care_relevance": "Personal adoption story. Jockey Being Family: 350,000+ families served. Dave Thomas Foundation board. Joined For Others network.",
            "recent_activity": "Cancer Research Foundation honoree (2025). Jockey Being Family continues active programming."
        }
    },
    {
        "name": "Tamika Tasby",
        "organization": "William Julius Wilson Institute / Harlem Children's Zone",
        "category": "subject_matter_expert",
        "tier": "tier_3_intro_needed",
        "linkedin_url": "https://www.linkedin.com/in/tamikatasby/",
        "role_title": "Senior Advisor, William Julius Wilson Institute, Harlem Children's Zone",
        "relationship": "Akilah's friend and former colleague at Gates Foundation",
        "foster_care_connection": "HCZ's cradle-to-career model is recognized by CEBC as a child welfare intervention. Addresses same root causes (poverty, instability) that drive children into foster care. Former Interim Deputy Director, K-12 Education at Gates Foundation. Part of The Broad Network (900+ educational equity leaders). WJW Institute launched Place-Based Education Design Fellowship reaching 1.3M students.",
        "outreach_hook": "Career arc from Gates Foundation to HCZ demonstrates expertise in scaling what works for vulnerable children. Foster care tech doesn't exist in a vacuum — needs to connect to schools, healthcare, housing, community support. That systems-level thinking is what she brings.",
        "recommended_sender": "Akilah (warm intro)",
        "outreach_wave": 3,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Ed.D. in Education Leadership/Policy, UMD College Park. Former Interim Deputy Director, K-12 Education at Gates Foundation. The Broad Network member. Based in Atlanta, GA.",
            "foster_care_relevance": "HCZ model is CEBC-recognized child welfare intervention. Place-based solutions addressing root causes of foster care involvement.",
            "recent_activity": "Continued advisory work at WJW Institute. Expanding field-building and community support programs nationally."
        }
    },
    {
        "name": "Lesli Snyder",
        "organization": "In-N-Out Burger",
        "category": "donor_stakeholder",
        "tier": "tier_3_intro_needed",
        "linkedin_url": None,
        "role_title": "Unknown (connected to In-N-Out Burger Foundation)",
        "relationship": "Link to the In and Out team — ask through Howard Booker",
        "foster_care_connection": "In-N-Out Burger Foundation established 1984 to fight child abuse. 2024: $2.8M to ~110 nonprofits. Supports ~400 organizations in residential treatment, emergency shelter, foster care, early intervention. Lynsi Snyder serves as board president. Slave 2 Nothing Foundation addresses trafficking and substance abuse.",
        "outreach_hook": "In-N-Out Foundation has funded hundreds of child welfare organizations — they've seen what works, what struggles to scale, where the gaps are. Need judges who know which ideas will still be standing in five years.",
        "recommended_sender": "Howard Booker (introduction)",
        "outreach_wave": 5,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Connected to In-N-Out Burger. May be foundation officer or family connection. Route through Howard Booker.",
            "foster_care_relevance": "In-N-Out Foundation: $2.8M/year to 110+ child welfare nonprofits. Fight child abuse since 1984. Faith-based orientation aligns with Innovation Challenge.",
            "recent_activity": "Foundation continues active grantmaking. Lynsi Snyder increasingly public about faith-driven leadership."
        }
    },
    {
        "name": "Ty Montgomery",
        "organization": "Next Legacy Partners",
        "category": "lived_experience",
        "tier": "tier_3_intro_needed",
        "linkedin_url": "https://www.linkedin.com/in/tymontgomerynfl/",
        "role_title": "Managing Partner, Next Legacy Partners; Former NFL Running Back",
        "relationship": None,
        "foster_care_connection": "Grew up with 17 foster siblings. Former NFL running back (Packers, Ravens, Jets, Saints, Patriots). Founded Next Legacy Partners (Palo Alto VC, Series A). Board member of Eye Heart World (anti-trafficking). Launched foster parent recruitment campaign in Wisconsin with mother. Partnered with Life Church in Green Bay for foster care teen programs.",
        "outreach_hook": "Rare combination: lived experience (17 foster siblings), NFL platform, and now professional VC evaluating early-stage ventures. Can evaluate from the heart (what families need) and the head (is this venture viable?).",
        "recommended_sender": "DV or Justin",
        "outreach_wave": 4,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Former NFL RB: Packers, Ravens, Jets, Saints, Patriots. Stanford graduate. Managing Partner at Next Legacy Partners (Palo Alto VC). Board: Eye Heart World.",
            "foster_care_relevance": "Grew up with 17 foster siblings. Foster parent recruitment campaign in Wisconsin. Life Church partnership for foster care teens.",
            "recent_activity": "Next Legacy has invested in 7 companies with 5 new investments in past 12 months (as of Nov 2025)."
        }
    },
    {
        "name": "Maggie Lin",
        "organization": "Foster Nation",
        "category": "lived_experience",
        "tier": "tier_3_intro_needed",
        "linkedin_url": "https://www.linkedin.com/in/maggieisabellelin/",
        "role_title": "Executive Director & Co-Founder, Foster Nation",
        "relationship": None,
        "foster_care_connection": "Entered foster care in LA County due to physical abuse. Moved between foster homes. Dartmouth graduate. Co-founded Foster Nation to rally young professionals in support of aging-out foster youth. Created Sparks program matching volunteer career coaches 1-on-1 with foster youth for 6 months. Featured on Tamron Hall Show, FOX 11.",
        "outreach_hook": "Work focuses on transition to adulthood — most underserved part of foster care. Lived experience + organization building. Can evaluate whether career readiness/financial literacy tools address real gaps or just look good in grant proposals.",
        "recommended_sender": "DV",
        "outreach_wave": 4,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Born in Taiwan; grandmother immigrated to CA. Entered foster care due to physical abuse. Dartmouth graduate. Based in Austin, TX (previously LA). Visionary Award from LACC Foundation.",
            "foster_care_relevance": "Former foster youth. Founded Foster Nation for aging-out youth. Sparks program: 1-on-1 career coaching for 6 months.",
            "recent_activity": "Foster Nation continues Sparks mentorship program. Expanding volunteer career coach network."
        }
    },
    {
        "name": "Byron Johnson",
        "organization": "Institute for Global Human Flourishing / Baylor University",
        "category": "subject_matter_expert",
        "tier": "tier_3_intro_needed",
        "linkedin_url": None,
        "role_title": "Distinguished Professor, Baylor University; Director, Institute for Global Human Flourishing; Faculty Affiliate, Harvard Human Flourishing Program",
        "relationship": None,
        "foster_care_connection": "Leading authority on scientific study of religion and faith-based organization efficacy. Co-PI of Global Flourishing Study (~200K participants, 22 countries, Harvard/Gallup/COS partnership). Research shows children in faith-based care are significantly safer. Studied Harvest of Hope faith-based foster parent intermediary. Open Table model of government/faith-based collaboration.",
        "outreach_hook": "Provides definitive academic evidence that faith-based child welfare organizations produce better outcomes. Dual Baylor/Harvard affiliation signals rigor to both faith-based and secular audiences. Can evaluate whether solutions are grounded in evidence.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 3,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Author of 250+ articles, multiple books: 'More God, Less Crime', 'The Angola Prison Seminary', 'The Restorative Prison'. Co-executive director, Center for Faith and the Common Good. Visiting Professor at Pepperdine.",
            "foster_care_relevance": "Research on faith-based child welfare (children safer in faith-based care). Harvest of Hope study. Open Table model. Global Flourishing Study.",
            "recent_activity": "Launched Institute for Global Human Flourishing at Baylor (April 2025). Published Global Flourishing Study findings."
        }
    },
    {
        "name": "Greg Jones",
        "organization": "Belmont University",
        "category": "subject_matter_expert",
        "tier": "tier_3_intro_needed",
        "linkedin_url": "https://www.linkedin.com/in/l-gregory-jones/",
        "role_title": "President, Belmont University",
        "relationship": None,
        "foster_care_connection": "Founded Belmont Innovation Labs with dedicated Foster Care Lab. Launched $1M Reconstruct Thriving Youth Challenge (Dec 2025). Partners: TN DCS, Governor's Faith-Based Initiative, Every Child TN, Access Ventures. 2025 Adoption Advocate from Dave Thomas Foundation. Coined 'traditioned innovation.' Contract extended through 2036.",
        "outreach_hook": "Belmont's Reconstruct Challenge is a $1M foster care innovation challenge — he's already doing this work. 'Traditioned innovation' (solutions grounded in enduring values, delivered through modern approaches) describes exactly what FF is looking for.",
        "recommended_sender": "DV or through Josh Yates / Tom Baldwin",
        "outreach_wave": 3,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Former Dean of Duke Divinity School (1997-2010, 2018-2021). Provost/EVP of Baylor (2010-2018). Secured $35M+ in grants/gifts in first year as president. Published author on faith, leadership, innovation.",
            "foster_care_relevance": "Foster Care Lab. $1M Reconstruct Challenge. 2025 Adoption Advocate. Partners: TN DCS, Every Child TN.",
            "recent_activity": "Reconstruct Challenge selected 6 winners (2026). Foster Care Lab continues. Contract extended through 2036."
        }
    },
    {
        "name": "Bishop W.C. Martin",
        "organization": "Bennett Chapel Missionary Baptist Church, Possum Trot, TX",
        "category": "subject_matter_expert",
        "tier": "tier_3_intro_needed",
        "linkedin_url": None,
        "role_title": "Lead Pastor, Bennett Chapel Missionary Baptist Church; National Speaker and Advocate",
        "relationship": None,
        "foster_care_connection": "In 1997, he and wife Donna adopted children 'nobody else wanted.' Inspired entire congregation: 22 families adopted 77 children from Texas foster care. Story became Sound of Hope film (released July 4, 2024, IMDB 7.1). Featured on Oprah, Dateline NBC, GMA, The 700 Club, Mike Rowe's podcast. CarePortal: called on the Church to 'knock the system out.'",
        "outreach_hook": "Most iconic story in American foster care history. Congregation literally emptied their county's foster care system. Can evaluate whether tech empowers communities or just adds more bureaucracy. Name alone draws national attention.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 4,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Lead Pastor since 1985. 22 families, 77 children adopted. Sound of Hope: The Story of Possum Trot (2024 film). National speaker through Ambassador Speakers. Featured on Oprah, Dateline, GMA, Mike Rowe podcast.",
            "foster_care_relevance": "Congregation adopted 77 children. Emptied county's foster care system. Sound of Hope film. 30 years of advocacy.",
            "recent_activity": "Sound of Hope encore on Fox News Lighthouse Faith podcast (Dec 2025). Continued national speaking circuit. Film streaming on Angel Studios."
        }
    },

    # ── TIER 4: COLD OUTREACH / LIMITED INFO ─────────────────────────
    {
        "name": "Steve French",
        "organization": "The Signatry",
        "category": "donor_stakeholder",
        "tier": "tier_4_cold",
        "linkedin_url": "https://www.linkedin.com/in/frenchstephen/",
        "role_title": "President & CEO, The Signatry",
        "relationship": None,
        "foster_care_connection": "No direct foster care involvement. The Signatry has facilitated $3.5B+ to nonprofits since 2018 as a Christian donor-advised fund. Many donors fund foster care organizations. Strategically important as gatekeeper/advisor to high-capacity Christian givers.",
        "outreach_hook": "Represents the donor community. Knows what motivates high-capacity Christian donors and what it takes for a nonprofit to sustain beyond initial funding. Practical sustainability lens for the panel.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 5,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Appointed CEO 2021. Previously founded/ran Quovant (Legal Spend Management, 13+ countries, sold 2015). Speaker at Exit Planning Summit, Faith Driven Investor, Finish Line Pledge. ECFA accredited.",
            "foster_care_relevance": "Indirect — channels billions to nonprofits, many in child welfare. Strategic gatekeeper to Christian donor community.",
            "recent_activity": "Speaking on biblical generosity, business exit planning, faith-driven investing."
        }
    },
    {
        "name": "Brad Fieldhouse",
        "organization": "Kingdom Causes Inc. / City Net / VandeSteeg Foundation",
        "category": "donor_stakeholder",
        "tier": "tier_4_cold",
        "linkedin_url": "https://www.linkedin.com/in/brad-fieldhouse-b8a933a/",
        "role_title": "Co-Founder & CEO, Kingdom Causes Inc.; Executive Director, City Net",
        "relationship": None,
        "foster_care_connection": "Kingdom Causes and City Net focus on homelessness and community development — deeply intersects with foster care (aging-out youth are highest risk for homelessness). Connected to VandeSteeg Foundation (Nick VandeSteeg, Fortune 200 CEO). DMin from Bakke Graduate University. MDiv from Fuller.",
        "outreach_hook": "Practical operational perspective on community-serving nonprofits. A brilliant tech platform doesn't matter if the caseworker or church volunteer can't use it. Bridge between operational reality and VandeSteeg philanthropic resources.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 5,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Southern California native. DMin in Transformational Leadership, Bakke Graduate University. MDiv, Fuller. Founded Kingdom Causes 2003. City Net since 2013. Managing Partner, Barnabas Los Angeles.",
            "foster_care_relevance": "Indirect — homelessness services intersect with aging-out foster youth. Gateway to VandeSteeg Foundation giving.",
            "recent_activity": "City Net expanded into Santa Barbara County. Active in faith-based community development."
        }
    },
    {
        "name": "Matthew Cathy",
        "organization": "WinShape Foundation / Chick-fil-A family",
        "category": "donor_stakeholder",
        "tier": "tier_4_cold",
        "linkedin_url": None,
        "role_title": "Cathy family member (next generation)",
        "relationship": "Route through WinShape (Riley Green or Callie Priest)",
        "foster_care_connection": "Cathy family founded WinShape Foundation 1984. S. Truett Cathy established first WinShape foster home 1987. WinShape Homes operates foster care and group care programs across Southeast and Brazil. Chick-fil-A Foundation True Inspiration Awards fund foster care orgs ($350K to Joy Meadows 2024). Foster Care Collective gatherings hosted by family.",
        "outreach_hook": "Next-generation Cathy family connection. Family legacy in foster care is unmatched. Opportunity for emerging leaders to shape the future of foster care innovation.",
        "recommended_sender": "Through WinShape (Riley Green or Callie Priest)",
        "outreach_wave": 5,
        "first_round_ask": False,
        "research_profile": {
            "bio": "One of six children of Bubba Cathy (EVP & Chairman, STC Brands). Bubba is youngest son of S. Truett Cathy (Chick-fil-A founder, deceased 2014). Bubba is a billionaire (Bloomberg). No public social media presence for Matthew.",
            "foster_care_relevance": "Family legacy: WinShape foster homes since 1987. Foster Care Collective. True Inspiration Awards. Matthew's individual activity not publicly documented.",
            "recent_activity": "WinShape hosted Foster Care Collective with speakers Jason Johnson and Peter Mutabazi."
        }
    },
    {
        "name": "Kirsten Winters",
        "organization": None,
        "category": "donor_stakeholder",
        "tier": "tier_4_cold",
        "linkedin_url": None,
        "role_title": "Unknown (likely connected to Mike Winters)",
        "relationship": "Listed consecutively with Mike Winters in CSV; likely spouse or family member",
        "foster_care_connection": "Likely shares Mike Winters' interest in foster care innovation and Flourish Fund. Possible co-decision-maker in $200K giving.",
        "outreach_hook": "Approach through Mike Winters relationship. Involving both could strengthen the $200K commitment.",
        "recommended_sender": "Justin Steele (through Mike Winters)",
        "outreach_wave": 5,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Very limited public information. Likely connected to Mike Winters (spouse or family). Placement in 'Donors/Stakeholders' category.",
            "foster_care_relevance": "Indirect — through Mike Winters' engagement with the Innovation Challenge.",
            "recent_activity": "No public activity found."
        }
    },
    {
        "name": "Scott Hansen",
        "organization": "CAFO (unverified)",
        "category": "subject_matter_expert",
        "tier": "tier_4_cold",
        "linkedin_url": None,
        "role_title": "Unknown (CAFO connection unverified)",
        "relationship": "CAFO connection needs verification — president is Jedd Medefind, board chair is Dr. Haag",
        "foster_care_connection": "If confirmed at CAFO: network of 150+ organizations, largest mobilization of faith-community resources for orphans and vulnerable children. Annual Summit draws thousands. NOTE: Formal role at CAFO could not be verified in research.",
        "outreach_hook": "Faith community is largest untapped distribution channel for foster care innovation. CAFO perspective would ensure solutions get adopted by churches. NEEDS VERIFICATION before outreach.",
        "recommended_sender": "Dan Vander Ploeg",
        "outreach_wave": 5,
        "first_round_ask": False,
        "research_profile": {
            "bio": "Unable to verify formal role at CAFO. May be board member, member org connection, or slightly different name. CAFO president is Jedd Medefind, board chair is Dr. Haag.",
            "foster_care_relevance": "If CAFO-connected: premier coalition for faith-based foster care and adoption. 150+ organizations. Annual Summit.",
            "recent_activity": "CAFO Summit 2026 at First Baptist Church of Atlanta. CAFO released report on Americans' views on foster care and adoption.",
            "note": "VERIFY AFFILIATION BEFORE OUTREACH"
        }
    },
]


def main():
    print(f"Seeding {len(JUDGES)} judge candidates into ff_ic_judges...")

    success = 0
    errors = 0

    for judge in JUDGES:
        try:
            # Convert research_profile dict to JSON-safe format
            row = {k: v for k, v in judge.items()}
            if row.get("research_profile"):
                row["research_profile"] = json.dumps(row["research_profile"])

            supabase.table("ff_ic_judges").upsert(
                row,
                on_conflict="name"
            ).execute()
            success += 1
            print(f"  + {judge['name']} ({judge['category']}, {judge['tier']})")
        except Exception as e:
            errors += 1
            print(f"  ! {judge['name']}: {e}")

    print(f"\nDone: {success} seeded, {errors} errors")

    # Summary
    result = supabase.table("ff_ic_judges").select("category", count="exact").execute()
    print(f"Total rows in ff_ic_judges: {result.count}")


if __name__ == "__main__":
    main()
