# Flourish Fund Innovation Challenge: Judge Outreach Emails

## Challenge Details

- $600K-$800K competitive funding for foster care technology solutions
- Dual-track: Nonprofit ($500K via Google.org) + Social Enterprise ($100K via Eagle Ventures)
- 12 judges needed
- Winner announced May 17, 2026 at The Understory (Praxis Summit)
- Staging site: https://innovationchallenge-puce.vercel.app/

**How Judging Works:**
- Flourish Fund screens all applications and passes 15 finalists to judges
- FF provides clear scoring criteria and a preliminary analysis of every application
- Judges review and score the 15 applications (can employ staff to support and provide recommendations)
- One 90-minute meeting where judges come together to select the top 8-10
- Judges invited to the final event to celebrate winners in person (optional)
- Judges featured on the Innovation Challenge website

---

## How We Crafted These Messages

This section documents the methodology, voice principles, and research process behind these outreach emails so that anyone writing similar invitations in the future can follow the same playbook.

### The Flourish Fund Voice

Flourish Fund is **humble, confident, smart, thoughtful, and grounded**. These emails invite people on a journey. They do not sell. There is a critical difference between "Would you help us?" and "Would you want to be part of this?" The first positions judges as doing us a favor. The second positions them as participants in something meaningful. We want the second.

The organization is not loud. It does not need to prove itself through exhaustive credentials or bold claims. It states what it is doing plainly and trusts the work to speak for itself. Confidence comes from clarity, not volume.

### Research Process

Each judge candidate went through a multi-step enrichment pipeline before we drafted their email:

1. **Initial research** (web search via 4 parallel research agents): biography, career history, foster care connections, relationship to FF network, outreach hooks
2. **LinkedIn profile enrichment** (Apify `harvestapi/linkedin-profile-scraper`): headline, about section, employment history, education, volunteering, skills, board positions
3. **LinkedIn posts scraping** (Apify `harvestapi/linkedin-profile-posts`): up to 25 recent posts with engagement metrics
4. **All enrichment stored** in `ff_ic_judges` Supabase table, `research_profile` JSONB column

The LinkedIn data was the most valuable input for personalization. A person's headline tells you their chosen identity. Their about section tells you their narrative. Their posts tell you what they're thinking about right now. These three signals matter more than any third-party bio.

### The "Personify and Pressure-Test" Method

For each judge, we followed this process:

1. **Read their LinkedIn posts.** Not just the headlines, but the actual content and language. What words do they use? What topics do they return to? What gets the most engagement from their network?
2. **Identify their identity anchor.** How do they introduce themselves? Steve French leads with stewardship. Maggie Lin leads with empowerment. Sixto Cancel leads with lived experience and systems change. Ty Montgomery leads with venture capital for positive change. Meet them where they already are.
3. **Ask: "Would this person say yes to this email?"** Put yourself in their chair. Read the email as if you received it. Does it feel like someone who actually knows your work, or someone who Googled you for five minutes? Does the "why them" paragraph land, or does it feel like flattery? Is the ask clear enough that you could say yes without needing a follow-up?
4. **Identify hesitation points.** What would make this person pause? Is it the time commitment? The unfamiliarity with FF? The tone? The length? Remove each friction point.

### Writing Principles

**Lead with what THEY care about, not what WE need.**
The strongest emails open with something the judge is already invested in. JooYeun Chang's opens with her Springboard Prize and Senate testimony. Tom Baldwin's opens with his LinkedIn posts about foster care innovation. Steve French's opens with his adoption story. The weakest possible opening is "Flourish Fund is launching..."

**Don't recite their resume back to them.**
They know where they've worked. Instead of listing credentials, identify the *pattern* in their career that makes them right for this. Tim Tebow's pattern is "moving from caring about a problem to actually doing something about it." Sarah Gesiriech's pattern is navigating the full landscape of child welfare from every angle. Name the pattern, not the bullet points.

**Use their language, not ours.**
If someone talks about "stewardship" (Steve French), use "stewardship." If someone talks about "empowerment" (Maggie Lin), use "empowerment." If someone frames their work as "evidence-based social innovation" (Josh Yates), reflect that language back. This signals genuine familiarity, not surface research.

**Respect how they tell their own story.**
Maggie Lin's LinkedIn leads with empowerment, not trauma. We follow her lead. Steve French shared his adoption story publicly on LinkedIn. We can reference it because he chose to make it part of his public narrative. Never lead with details someone hasn't chosen to put forward themselves.

**Shorten the process paragraph.**
Judges don't need a 100-word description of how judging works in the first email. They need to know it's manageable. Two to three sentences: our team does the heavy lifting, you review 15 finalists and join one 90-minute meeting. Details come later.

**Make it easy to say yes.**
The close should be a 15-minute call, not a commitment. The email should leave the reader thinking "I could do that" rather than "let me think about it." The lighter the first step, the more likely they take it.

### What We Don't Do

- **No em dashes.** They're an AI writing tell. Use periods, commas, and sentence breaks.
- **No symmetric triads.** "Innovation, collaboration, and impact" is filler. Say something specific instead.
- **No "means the world" or "means a lot."** These are empty intensifiers.
- **No "outdoor equity nonprofit" or "underserved communities."** Describe what actually happens.
- **No manufactured urgency.** If there's a real timeline, say so plainly. Otherwise, don't pretend.
- **No over-optimized emails.** The moment it starts to feel "crafted" with strategic quote placement and pronoun ratios, it stops feeling human. Warm and slightly imperfect beats polished and hollow.

### The Simple Test (from OC Fundraising Principles)

Before sending any email, ask:

1. Does this sound like a friend talking?
2. Would I be comfortable if this person showed it to someone else?
3. Am I inviting them into something, or asking them to save something?
4. Is the ask clear?
5. Does this respect their time?
6. Have I made it easy to say yes?

If the answer to any of these is no, rewrite it.

### Key Discoveries from LinkedIn Enrichment

Several LinkedIn profiles revealed information that materially changed the emails:

- **Steve French** (The Signatry): His top post revealed he was **adopted**. This transformed a generic "sustainability lens" email into a deeply personal invitation connecting his life story to the challenge's mission.
- **Maggie Lin** (Foster Nation): Original email led with her abuse history. Her LinkedIn leads with **empowerment**. We rewrote to follow her lead.
- **Ty Montgomery** (Next Legacy): LinkedIn revealed he serves on the **board of Connections Homes** (a foster care org), not just that he grew up with foster siblings. This added a third dimension to his "dual lens."
- **Tom Baldwin** (Belmont): His posts showed active, personal engagement with foster care outcomes (housing projects, application counts), not just institutional management. We referenced his posts directly.
- **Josh Yates** (Belmont): He shared the "Fracture to Flourish" podcast about aging-out foster youth, revealing personal investment beyond his institutional role.
- **Chris Tomlin**: The LinkedIn match was **wrong** (a smoke alert company owner in North Carolina, not the worship leader). This was caught before outreach. Always verify LinkedIn matches against known biographical details.

### Email Structure Template

```
[Greeting],

[Opening: 2-3 sentences about what THEY are building/doing that connects to this work.
Use their language. Reference their posts or public statements when possible.]

[FF paragraph: 2-3 sentences. What we're doing, the two tracks, the focus areas.
State it plainly. Don't oversell.]

[The invitation: 1 sentence. "We're assembling 12 judges and would [love/be honored] to have you."]

[Why them: 3-5 sentences. Not their resume. The PATTERN in their work that makes them
right for this. What question can they answer that nobody else on the panel can?
Connect their specific expertise to what the challenge needs.]

[Process: 2-3 sentences. Our team screens, you review 15 finalists, one 90-minute meeting.
Featured on website, invited to May 17 celebration.]

[Link to overview]

[Close: "Would [X] minutes work for a call?" or equivalent low-friction next step.]

[Sign-off]
```

### Word Count Target

250-350 words for the email body. Err shorter. The emails that work best tend to be closer to 250. The ones that feel like a pitch tend to be closer to 350.

---

## Organizational Capacity Grants for Nonprofit Judge Leaders

### The Policy

Organizations whose leaders serve as judges are excluded from applying to the Innovation Challenge. This is a clean conflict-of-interest rule, not a judgment call. If you judge, your org doesn't apply.

For nonprofit leaders of smaller organizations (under $2M annual budget) whose missions align with the challenge, this exclusion has real cost. They're giving up eligibility for a $500K grant pool by saying yes to judging. We want to acknowledge that.

### The Grant

Flourish Fund will provide a **$10,000 unrestricted capacity grant** to qualifying nonprofit organizations whose leaders serve on the judging panel. This is not compensation for judging. It's an investment in mission-aligned work from organizations we believe in, independent of the challenge.

**Qualifying criteria:**
- Leader serves as a judge on the Innovation Challenge panel
- Organization is a nonprofit with an annual budget under $2M
- Organization's mission aligns with child welfare, foster care, or family flourishing
- Organization would have been a credible applicant to the challenge

**Framing:** "We're investing in your mission" — not "we're making up for what you're missing." The grant is presented as a capacity investment, not a consolation prize. The real value of judging is the network, visibility, and relationship with FF and its funders.

### Who Qualifies

| Judge | Organization | Budget Est. | Grant? | Notes |
|-------|-------------|-------------|--------|-------|
| **Maggie Lin** | Foster Nation | Under $2M (likely) | **Yes, $10K** | Foster youth empowerment. Would have been a strong applicant. Smaller org where $10K is meaningful operating money. |
| **Sixto Cancel** | Think of Us | Over $2M (likely) | **No** | Foster care tech is their mission, but Think of Us is a larger, well-funded org. Exceeds the $2M threshold. However, FF is considering strategic grants for larger aligned organizations longer term. Judging builds the relationship for that future investment. This works to Sixto's advantage. |
| **Brad Fieldhouse** | City Net | Over $2M (likely) | **No** | Homeless services. Adjacent to foster care (aging-out youth) but not core. Larger org. |

### Budget Impact

$10,000 total (one grant to Foster Nation). Approximately 1.5% of the nonprofit prize pool. Clean, defensible, proportional.

---

## TIER 1: READY TO GO

---

### 1. Michael Allen | Donor/Stakeholder (FF Board Member)
**Recommended Sender:** Dan Vander Ploeg (DV)
**Strategy:** Confirmation (he already asked to judge)

**Subject:** You're in. Innovation Challenge judging details

Michael,

You told us you wanted to judge the Innovation Challenge. We took you at your word.

Here's what we're building: a $600K-$800K competitive funding program to find the best technology solutions for child welfare and family flourishing. Two tracks. One focused on nonprofits (backed by Google.org at $500K), the other on social enterprises (backed by Eagle Ventures at $100K). We're expecting applications from teams working on everything from family preservation tech to foster care system tools.

We're assembling a panel of about 12 judges. Given your work with Together Chicago and Together South Florida, and your years on the Flourish Fund board, you already know this space better than most. We need that perspective in the room.

The time commitment is light. Our team screens all the applications and passes 15 finalists to you, along with scoring criteria and our preliminary analysis of each one. You review and score them on your own time (and you're welcome to have staff support you in the review). Then we hold a single 90-minute meeting where the judges come together to select the top 8-10. You'd also be invited to the final celebration event on May 17 at The Understory, and we'll feature you prominently on the challenge website.

You can see the full challenge overview here: https://innovationchallenge-puce.vercel.app/

I'll send over the formal details and calendar holds this week. Let me know if you have questions, but I think we both know you're already in.

Looking forward to this,
Dan

---

### 2. Mike Winters | Donor/Stakeholder
**Recommended Sender:** Justin Steele
**Strategy:** Direct invitation (warm relationship, pending $200K commitment)

**Subject:** Judging the Innovation Challenge, as discussed

Mike,

I've been thinking about our conversation on the Innovation Challenge and wanted to follow up with something specific.

We're putting together the judging panel now. Twelve people total. We're looking for folks who can evaluate technology solutions for child welfare with both a sharp eye and a genuine heart for the work. You came to mind immediately.

The challenge is substantial: $600K-$800K in competitive funding across two tracks, one backed by Google.org and the other by Eagle Ventures. Applications will come from organizations building tools for family preservation, foster youth outcomes, and system efficiency. The judges' evaluations directly determine who gets funded.

The process is straightforward. Our team screens all the applications and passes 15 finalists to the judges, along with clear scoring criteria and a preliminary analysis of each one. You review and score them at your own pace. Then we hold one 90-minute meeting where the panel selects the top 8-10. You're also invited to the final celebration on May 17 at The Understory, and you'd be featured prominently on the challenge website.

You mentioned wanting to understand the Innovation Challenge more deeply. Sitting on the judging panel would give you the fullest possible picture of what's happening in foster care innovation right now. You'd see the strongest teams and the most promising approaches firsthand.

Here's the challenge overview: https://innovationchallenge-puce.vercel.app/

Could we find 15 minutes this week to talk through the details? I'd love to have you on the panel.

Best,
Justin

---

### 3. Nathan Aleman | Donor/Stakeholder
**Recommended Sender:** Dan Vander Ploeg (DV)
**Strategy:** Direct invitation (DV has scheduled call)

**Subject:** Foster care innovation challenge, judge invitation

Nathan,

I wanted to bring something to our conversation that I think will resonate given your background.

Flourish Fund is launching a $600K-$800K Innovation Challenge focused on technology solutions for child welfare and family flourishing. Google.org is backing the nonprofit track at $500K and Eagle Ventures is funding a social enterprise track at $100K. We're looking for the most promising tools across family preservation, foster youth wellbeing, and system efficiency.

We're assembling a judging panel of about 12 people, and I'd like you to be one of them.

Here's why. You spent seven years at Seneca Family of Agencies working directly with foster care children and families in wraparound programs and therapeutic behavioral services. Now you're at Bridgespan advising philanthropies on how to deploy capital effectively. That combination of direct service experience and strategic consulting is exactly the lens we need. You've seen the system from the inside and you understand what it takes for an intervention to actually work at scale.

The process is designed to respect your time. Our team screens all the applications and passes 15 finalists to the judges, with clear scoring criteria and a preliminary analysis of each one. You review and score them at your convenience (staff can support you if helpful). Then we hold a single 90-minute meeting to select the top 8-10. You'd be invited to celebrate the winners in person on May 17 at The Understory, and listed prominently on the challenge website.

Challenge overview: https://innovationchallenge-puce.vercel.app/

I'd love to discuss this when we connect. Would this be something you'd consider?

Dan

---

### 4. Wes Hartley | Donor/Stakeholder (Eagle Ventures)
**Recommended Sender:** Dan Vander Ploeg (DV)
**Strategy:** Confirmation (per partnership MOU, EV granted a judging spot)

**Subject:** Innovation Challenge judging panel, Eagle Ventures seat

Wes,

I'm grateful for this partnership, Wes. Per our agreement, Eagle Ventures has a seat on the Innovation Challenge judging panel. I wanted to confirm the details and see whether you, Vip, or Wade will be the one filling it.

Quick refresh on the setup: $600K-$800K total, with your social enterprise track at $100K and Google.org's nonprofit track at $500K. We're expecting applications across three focus areas: prevention and family preservation, foster youth wellbeing, and system efficiency.

We're finalizing a panel of 12 judges. Our team handles all the initial screening and sends 15 finalists to the judges with scoring criteria and our preliminary analysis. Judges review and score them, then we hold one 90-minute meeting to select the top 8-10. Judges are invited to the final celebration on May 17 at The Understory and featured prominently on the website.

Full challenge overview: https://innovationchallenge-puce.vercel.app/

Let me know who from EV will take the seat and I'll send calendar holds.

Dan

---

## TIER 2: WARM CONNECTIONS (DIRECT INVITATION)

---

### 5. Tim Tebow | Celebrity
**Recommended Sender:** Wes Hartley or Vip (Eagle Ventures connection)
**Strategy:** Direct invitation through Wes/Vip

**Subject:** Judging a foster care innovation challenge

Tim,

I know this work is close to your heart. Flourish Fund is putting $600K-$800K behind the best technology solutions for child welfare and family flourishing. Google.org is backing a $500K nonprofit track, Eagle Ventures is funding a $100K social enterprise track. We're looking for tools that keep families together, protect kids in care, and reduce the barriers that slow everything down.

We're building a judging panel of 12 and would be honored to have you on it.

Your foundation doesn't just raise awareness. Night to Shine creates real dignity. DISRUPT works with law enforcement on real cases. The Renewed Hope Act is real legislation. That pattern of moving from caring about a problem to actually doing something about it is exactly the filter we need on this panel. We'll see applications from teams building technology for everything from family preservation to foster youth outcomes. The question isn't just "is this clever?" It's "will this actually reach the child who needs it?" You can answer that.

Our team screens all applications and passes 15 finalists to each judge with scoring criteria and our analysis. You review and score on your schedule (your team is welcome to support the review). One 90-minute meeting to select the top 8-10. You'd be featured on the challenge website and invited to celebrate the winners May 17 at The Understory.

Overview: https://innovationchallenge-puce.vercel.app/

Would you have 15 minutes for a quick call to discuss?

With gratitude,
[Sender]

---

### 6. Chris Tomlin | Celebrity
**Recommended Sender:** Jared (via DV's connection)
**Strategy:** Direct invitation (strong natural fit through For Others)

**Subject:** For Others + Flourish Fund Innovation Challenge

Chris,

For Others has raised over $12 million for foster care. Good Friday Nashville is now the largest faith-driven benefit concert in the country. You and Lauren have built something that's genuinely changing how the church responds to the child welfare crisis.

Here's something we think fits directly into that mission.

Flourish Fund is launching a $600K-$800K Innovation Challenge to identify the best technology solutions for child welfare and family flourishing. Google.org is backing the nonprofit track at $500K. Eagle Ventures is funding a social enterprise track at $100K. Applications will come from organizations building tools for family preservation, foster youth outcomes, and system efficiency.

We're assembling a judging panel of 12 people and would love to have you on it.

The Innovation Challenge is about finding the technologies and approaches that could accelerate what For Others is already working toward: a world where every child grows up in a loving family. Your experience building a coalition of donors, nonprofits, and government agencies around foster care means you can evaluate not just whether a solution is clever, but whether it can actually be deployed in the real world.

The process is designed to be manageable. Our team screens everything and sends 15 finalists to you with scoring criteria and our analysis. You review and score them on your own time (your team can assist). One 90-minute meeting to pick the top 8-10. Optional appearance at the final celebration on May 17. And you'd be featured prominently on the challenge website.

Overview here: https://innovationchallenge-puce.vercel.app/

Would a brief call work to discuss the details?

With gratitude,
[Sender]

---

### 7. Connie Ballmer | Donor/Stakeholder
**Recommended Sender:** Justin Steele
**Strategy:** Direct invitation (Justin on ongoing thread with Ballmer leaders)

**Subject:** Flourish Fund Innovation Challenge, judging invitation

Connie,

Ballmer Group's commitment to child welfare goes back to the very beginning of your philanthropic work. The Partners for Our Children initiative, the Child Well-Being Portal, and your recent $1 billion early childhood commitment in Washington demonstrate what's possible when serious resources meet serious strategy.

Flourish Fund is launching something we think aligns with how you think about this work: a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Google.org is backing a $500K nonprofit track. Eagle Ventures is funding a $100K social enterprise track. We're looking for tools across three areas: family preservation, foster youth wellbeing, and system efficiency.

We're assembling a judging panel of 12 and would be honored to have you (or a senior Ballmer Group leader you'd designate) serve on it.

Your team's emphasis on data-driven, technology-enabled approaches to social challenges is exactly the lens this panel needs. You've funded the infrastructure that makes child welfare systems visible. This challenge is about funding the tools that make them better.

The commitment is light. Our team screens all applications and passes 15 finalists to the judges with scoring criteria and our preliminary analysis. You review and score at your convenience (staff welcome to support). One 90-minute meeting to select the top 8-10. Optional invitation to the final celebration on May 17 at The Understory. Judges featured prominently on the website.

Challenge overview: https://innovationchallenge-puce.vercel.app/

Would 15 minutes work to discuss? Happy to connect with whoever on your team makes the most sense.

Best,
Justin

---

### 8. JooYeun Chang | Donor/Stakeholder
**Recommended Sender:** Dan Vander Ploeg (DV)
**Strategy:** Direct invitation (strongest subject matter fit on the list)

**Subject:** Innovation Challenge for foster care tech, judge invitation

JooYeun,

I've been wanting to connect with you about this. The Springboard Prize, your Senate testimony on Family First, the Aviv Foundation's investment in prevention. Few people in the country are working on this from as many angles as you are.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Two tracks: $500K from Google.org for nonprofits, $100K from Eagle Ventures for social enterprises. Three focus areas: prevention and family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and I'd like you to be one of them.

You've already built what we're trying to build. The Springboard Prize proved that innovation competitions can drive real change in child welfare when the evaluation criteria are rigorous and the evaluators understand the system. That experience is exactly what we need. You can tell us what works, what to watch out for, and where promising ideas go sideways in implementation.

Our team screens all applications and passes 15 finalists to each judge with scoring criteria and our analysis. You review and score at your convenience. One 90-minute meeting to select the top 8-10. You'd be featured on the challenge website and invited to the celebration May 17.

Full overview: https://innovationchallenge-puce.vercel.app/

Could we set up a brief call to discuss?

Dan

---

### 9. Sixto Cancel | Lived Experience
**Recommended Sender:** Justin Steele or Dan Vander Ploeg
**Strategy:** Direct invitation (Justin has had several conversations over the years)
**Note:** Think of Us likely exceeds the $2M budget threshold for challenge applicants, so judging doesn't cost them eligibility. But the relationship matters. FF is exploring strategic grants for larger aligned organizations, and judging puts Sixto in the room with FF's funders and network. Mention this on the call, not in the email.

**Subject:** Judging a foster care tech challenge

Sixto,

It's been too long since we've talked. Think of Us is working with 22 states to reshape child welfare through technology, data, and design. That's not an organization commenting on the system from the outside. That's an organization building inside it.

Flourish Fund is launching a $600K-$800K Innovation Challenge focused on technology solutions for child welfare and family flourishing. Two tracks: $500K from Google.org for nonprofits, $100K from Eagle Ventures for social enterprises. We're looking for the most promising tools across family preservation, foster youth wellbeing, and system efficiency.

We're building a panel of 12 judges, and your perspective would make this panel fundamentally better.

Most innovation challenges in child welfare get evaluated by people who've never navigated the system. You have. And you've gone further, building an organization that's changing how governments design for the people they serve. When an applicant proposes a new technology for child welfare, you can ask the question nobody else on this panel can: "Would this have actually helped me?"

Dan saw you at the White House in November. The Fostering the Future executive order calls for the kind of technology-driven, partnership-based innovation this challenge is designed to fund. We're part of the same wave.

The ask is manageable: review 15 pre-screened finalists on your schedule (we provide scoring criteria and our analysis), then one 90-minute meeting to pick the top 8-10. You'd be featured on the challenge website and invited to celebrate the winners May 17.

Overview: https://innovationchallenge-puce.vercel.app/

Would 15 minutes work to catch up and discuss?

[Sender]

---

### 10. Bill & Crissy Haslam | Subject Matter Expert
**Recommended Sender:** Dan Vander Ploeg (DV)
**Strategy:** Direct invitation (sponsors of the Understory, will be at May event)

**Subject:** Innovation Challenge judging, a natural fit

Governor Haslam and Crissy,

TNFosters is still the gold standard for what happens when a governor and first lady decide to mobilize an entire state around foster care. A 40% increase in certified foster families. 116 children placed in forever homes in the first year. That's not a talking point. That's a track record.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Google.org is backing a $500K nonprofit track and Eagle Ventures is funding a $100K social enterprise track. We're evaluating tools across family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges, and we'd love to have one or both of you serve on the panel.

You've proven that government, faith communities, and nonprofits can work together to transform foster care outcomes at scale. That's the exact perspective we need judges to bring. Can this innovation actually be deployed? Will churches and communities adopt it? Does it survive contact with the real system? You two can answer those questions better than almost anyone.

The commitment is light. Our team screens all applications and passes 15 finalists to judges with scoring criteria and our analysis. You review and score on your own time. One 90-minute meeting to select the top 8-10. And you're already planning to be at The Understory on May 17 for the final celebration. The timing works well. Judges are featured prominently on the challenge website.

Challenge overview: https://innovationchallenge-puce.vercel.app/

Would a brief call work to talk through the details?

With respect,
Dan

---

### 11. Josh Yates | Donor/Stakeholder (Belmont Innovation Labs)
**Recommended Sender:** Dan Vander Ploeg (DV)
**Strategy:** Direct invitation (reciprocity, they included Flourish in their panel)

**Subject:** Returning the favor, Innovation Challenge judging

Josh,

We were honored to serve on the Reconstruct Challenge panel. Watching 58 organizations raise their hands with ideas to help Tennessee's aging-out youth was a powerful demonstration of what happens when you create the right container for innovation.

We'd like to reciprocate.

Flourish Fund is launching a $600K-$800K Innovation Challenge for technology solutions in child welfare and family flourishing. Google.org backing the nonprofit track at $500K, Eagle Ventures funding a social enterprise track at $100K. Three focus areas: prevention and family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges, and you're one of our first choices.

You've literally just done this. You know what a strong application looks like and where promising ideas break down in execution. Your commitment to evidence-based social innovation, combined with the deep personal investment you clearly have in this issue (I noticed you shared the Fracture to Flourish podcast on the aging-out crisis), tells us you'd push this challenge to fund what actually works, not just what sounds good.

Our team screens everything and passes 15 finalists to judges with scoring criteria and our analysis. Review and score on your time. One 90-minute meeting to select the top 8-10. You'd be featured on the website and invited to celebrate the winners May 17. If your new VP role at Belmont makes bandwidth tight, we'd welcome Tom Baldwin just as warmly.

Overview: https://innovationchallenge-puce.vercel.app/

Can we set up a quick call?

Dan

---

### 12. Tom Baldwin | Donor/Stakeholder (Belmont Innovation Labs)
**Recommended Sender:** Dan Vander Ploeg (DV)
**Strategy:** Direct invitation (reciprocity, complementary to Josh Yates)

**Subject:** Innovation Challenge judge invitation

Tom,

I've been following your posts about the Reconstruct Challenge and the foster care innovation work at Belmont. The affordable housing complex in Knoxville for former foster youth. The 58 applications that came in. The methodology of applying billion-dollar brand strategy to systemic issues for vulnerable people. You're not just managing this work. You're in it.

Flourish Fund is launching a $600K-$800K Innovation Challenge for technology solutions in child welfare and family flourishing. Google.org backing a $500K nonprofit track, Eagle Ventures a $100K social enterprise track. Three focus areas: prevention and family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would like you to be one of them.

Your background gives this panel something it specifically needs. You've led growth from $2B to $7B at Mars, so you can evaluate whether a solution is commercially viable and scalable. And you've spent the last few years deep in foster care innovation at Belmont, so you know whether a proposed tool would actually land in the real world. That combination is rare.

Our team screens all applications and passes 15 finalists to judges with scoring criteria and our analysis. Review and score at your pace. One 90-minute meeting to select the top 8-10. You'd be featured on the website and invited to celebrate the winners May 17.

Overview: https://innovationchallenge-puce.vercel.app/

Would a 15-minute call work to discuss?

Dan

---

### 13. Audrey Haque | Donor/Stakeholder
**Recommended Sender:** Dan Vander Ploeg (DV) or Justin Steele
**Strategy:** Direct invitation (relationship-deepening opportunity)

**Subject:** Invitation to judge a foster care innovation challenge

Audrey,

I wanted to share something we're building that I think you'd find genuinely interesting.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Two tracks: Google.org is backing nonprofits at $500K, Eagle Ventures is funding social enterprises at $100K. We're looking for tools that help keep families together, improve outcomes for children in care, and reduce system inefficiency.

We're assembling a judging panel of 12 people and would love to have you on it.

The Silicon Valley perspective matters for this challenge. We're evaluating technology solutions, and having judges who understand how to assess product-market fit, scalability, and technical feasibility alongside mission alignment makes the panel stronger. The combination of the Haque Family Foundation's philanthropic vision and your family's deep roots in the technology sector is exactly the kind of dual lens we're looking for.

The process is designed to be efficient. Our team screens all applications and passes 15 finalists to judges with clear scoring criteria and our preliminary analysis. You review and score on your own time (staff welcome to assist). One 90-minute meeting to select the top 8-10. You'd be invited to the final celebration on May 17 at The Understory and featured prominently on the challenge website.

You'd be joining a panel that includes leaders from child welfare, philanthropy, government, and the faith community.

Overview: https://innovationchallenge-puce.vercel.app/

Could we find 15 minutes to discuss?

[Sender]

---

### 14. Sarah Gesiriech | Subject Matter Expert
**Recommended Sender:** Dan Vander Ploeg (DV)
**Strategy:** Direct invitation (she's the architect of the Fostering the Future EO)

**Subject:** Your executive order meets our Innovation Challenge

Sarah,

Your fingerprints are all over this work. The Fostering the Future executive order calls for technology, federal support, and public-private partnerships to expand opportunities for foster youth. That's nearly a word-for-word description of what Flourish Fund's Innovation Challenge is designed to do.

We're launching a $600K-$800K competitive funding program for technology solutions in child welfare and family flourishing. Google.org backing a $500K nonprofit track, Eagle Ventures funding a $100K social enterprise track. Prevention, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and I'd like you to be one of them.

Twenty-five years across Casey Family Programs, the Dave Thomas Foundation, ACF, and now the Office of the First Lady. What sets you apart isn't just the breadth of that experience. It's that you've seen what happens when a promising idea meets procurement, regulation, and implementation. You know which innovations survive that gauntlet and which ones don't. That filter is exactly what this panel needs.

Our team screens all applications and passes 15 finalists to judges with scoring criteria and our analysis. Review and score on your schedule. One 90-minute meeting to pick the top 8-10. You'd be featured on the challenge website and invited to the celebration May 17.

Overview: https://innovationchallenge-puce.vercel.app/

Would a quick call work to discuss?

Dan

---

### 15. Steve Moore | Subject Matter Expert
**Recommended Sender:** Dan Vander Ploeg (DV)
**Strategy:** Direct invitation

**Subject:** $750K foster care innovation challenge, judge invitation

Steve,

I hope the emeritus season is treating you well. Sixteen years at the Murdock Trust. Over 4,400 grants. $771 million deployed. That's a career spent making hard calls about what works and what doesn't, including investments in organizations like Olive Crest that serve foster families directly.

Flourish Fund is launching a $600K-$800K Innovation Challenge for the best technology solutions in child welfare and family flourishing. Google.org backing a $500K nonprofit track, Eagle Ventures funding a $100K social enterprise track. Family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would be grateful to have you on the panel.

You bring something this panel specifically needs: the instinct to distinguish between a compelling pitch and a genuinely sustainable organization. After thousands of applications, you know how to spot the difference. That's hard to teach. Your commitment to stewardship, to making sure resources create lasting impact rather than one-time wins, aligns with what we're trying to do here. We want to fund solutions that are still standing in five years.

Our team screens all applications and passes 15 finalists to judges with scoring criteria and our analysis. Review and score at your convenience. One 90-minute meeting to select the top 8-10. You'd be featured on the website and invited to the celebration May 17.

Overview: https://innovationchallenge-puce.vercel.app/

Would a 15-minute call work to discuss?

Dan

---

## TIER 3: WARM INTROS NEEDED

---

### 16. David Platt | Celebrity
**Recommended Sender:** Christian Pinkston, Jedd, or DV (through Project Belong connection)
**Strategy:** Direct invitation through warm intro

**Subject:** Foster care innovation challenge, 12 judges

David,

I keep coming back to a story about you. You once called the local Department of Human Resources in Shelby County and asked how many families it would take to cover all foster and adoption needs. They said 150. You told your congregation, and over 160 families signed up.

That story is why we're writing to you.

Flourish Fund is launching a $600K-$800K Innovation Challenge to identify the best technology solutions for child welfare and family flourishing. Google.org is backing a $500K nonprofit track. Eagle Ventures is funding a $100K social enterprise track. We're looking for tools that help prevent family separation, improve outcomes for children in care, and reduce bureaucratic burden on families and caseworkers.

We're building a panel of 12 judges and would be honored to have you serve.

You and Heather have four adopted children. You've mobilized an entire church to empty a county's foster care waiting list. Through Radical, you've taught millions of Christians that caring for orphans and vulnerable children isn't optional. You don't just talk about this work. You live it. That credibility matters on a judging panel.

The time ask is small. Our team screens all applications and sends 15 finalists to judges with scoring criteria and our analysis. You review and score at your convenience (staff can support). One 90-minute meeting to select the top 8-10. You'd be invited to celebrate the winners on May 17 at The Understory, and featured prominently on the challenge website.

Overview: https://innovationchallenge-puce.vercel.app/

Would 15 minutes work for a call to discuss?

With respect,
[Sender]

---

### 17. Simone Biles | Celebrity
**Recommended Sender:** Through management/agent
**Strategy:** Direct invitation (lean on lived experience angle)

**Subject:** Judge a $750K foster care technology challenge

Simone,

You've said you know "exactly what these kids go through." You lived in foster care from age 3 to 6. That experience shaped everything that came after, and you've channeled it into real work as Friends of the Children's national ambassador.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Two funding tracks backed by Google.org and Eagle Ventures. We're looking for tools that keep families together, improve outcomes for kids in care, and cut through system inefficiency.

We're assembling 12 judges and we'd love to have you on the panel.

Here's what makes your perspective irreplaceable: most people evaluating foster care technology have studied the system from the outside. You were in it. You can assess whether a proposed solution would have actually made a difference for a kid like you, or whether it's just another layer of bureaucracy that sounds good in a pitch deck but misses the reality on the ground.

The commitment is light. Our team screens all applications and sends 15 finalists to you with scoring criteria and our analysis. You review and score on your own time (your team can help). One 90-minute meeting to select the top 8-10. You'd be invited to the final celebration on May 17 and featured prominently on the challenge website.

Overview: https://innovationchallenge-puce.vercel.app/

Would a brief call work to discuss the details?

With admiration,
[Sender]

---

### 18. Bear Rinehart | Celebrity
**Recommended Sender:** Through For Others / Chris Tomlin network
**Strategy:** Direct invitation (connected through For Others ecosystem)

**Subject:** Foster care innovation challenge, NEEDTOBREATHE connection

Bear,

The way NEEDTOBREATHE shows up for foster care is different from what most artists do. Over $1.1 million to For Others through ticket sales. And families have literally started the licensing process because of something you said from stage. That's not a small thing.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Google.org is backing a $500K nonprofit track. Eagle Ventures is funding a $100K social enterprise track. We're looking for the most promising tools across family preservation, foster youth wellbeing, and system efficiency.

We're building a judging panel of 12 and would love to have you join.

You bring an audience that most people in the child welfare space can't reach: young families who are open to fostering and adopting but don't know where to start. That perspective matters when evaluating innovation. Can this tool help a family in Ohio who heard you talk about For Others at a concert and wants to take the next step? Can it connect them to the right agency, the right training, the right support? If you're nodding yes to those questions, we need you in the room.

The commitment is easy. Our team screens everything and sends 15 finalists to you with scoring criteria and our analysis. You review and score on your schedule (your team can assist). One 90-minute meeting to pick the top 8-10. You'd be invited to the final celebration on May 17 and featured prominently on the challenge website.

Overview: https://innovationchallenge-puce.vercel.app/

Could we set up a quick call to discuss?

[Sender]

---

### 19. Kirk Franklin | Celebrity
**Recommended Sender:** Through management/agent
**Strategy:** Direct invitation (lean on personal adoption story)

**Subject:** A $750K foster care tech challenge needs your story

Kirk,

Your story has stayed with me. At the BET Awards, you honored the 64-year-old woman who chose to adopt "a boy nobody wanted." Gertrude Franklin changed the trajectory of your life. You named your publishing company after her. That story carries weight.

There are over 400,000 children in the U.S. foster care system right now who need their own Aunt Gertrude.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Google.org is backing a $500K nonprofit track. Eagle Ventures is funding a $100K social enterprise track. We're looking for tools that connect kids to families faster, support caregivers better, and remove barriers from a system that too often gets in its own way.

We're building a panel of 12 judges, and your story would make every innovator in the room remember why this work matters.

Your experience being adopted, the journey with your biological father documented in "Father's Day," and your youth mentoring work through The Franklin Imagine Group give you a lived understanding of what vulnerable kids actually need. That's not something you can learn from a report.

The process is manageable. Our team screens everything and sends 15 finalists to you with scoring criteria and our analysis. You review and score at your own pace (your team can assist). One 90-minute meeting to pick the top 8-10. You'd be invited to the final celebration on May 17 and featured prominently on the challenge website.

Overview: https://innovationchallenge-puce.vercel.app/

Would a brief call work to talk through the details?

With gratitude,
[Sender]

---

### 20. Christian Bale | Celebrity
**Recommended Sender:** Through representatives or Dr. Eric Esrailian / Tim McCormick (Together California co-founders)
**Strategy:** Direct invitation (highlight his 16-year practitioner credibility)

**Subject:** Foster care innovation challenge, judge invitation

Christian,

You spent 16 years building Together California. You visited foster homes, attended child welfare meetings, and raised $22 million to create a village in Palmdale specifically designed to keep siblings together. The first homes opened earlier this year. That is not a celebrity lending a name. That is someone who has done the work.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Two tracks: $500K from Google.org for nonprofits, $100K from Eagle Ventures for social enterprises. We're looking for tools across family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges, and I'd like to invite you to serve.

You've built the physical infrastructure to keep foster siblings together. This challenge is about building the digital and systemic tools to transform the broader system. Your deep familiarity with the complexity of child welfare (the regulations, the case management, the gaps between what should happen and what does) means you can evaluate solutions with a practitioner's eye. You know what sounds good in a pitch versus what actually survives contact with the system.

The time ask is small. Our team screens all applications and sends 15 finalists to you with scoring criteria and our analysis. You review and score at your convenience (staff can support). One 90-minute meeting to select the top 8-10. You'd be invited to celebrate the winners on May 17 and featured prominently on the challenge website.

Overview: https://innovationchallenge-puce.vercel.app/

Would a conversation make sense? Happy to connect through whatever channel works best.

With respect,
[Sender]

---

### 21. Debra Waller | Donor/Stakeholder
**Recommended Sender:** DV or through For Others / WinShape network
**Strategy:** Direct invitation

**Subject:** Jockey Being Family + foster care innovation

Debra,

Jockey Being Family has reached over 350,000 families with post-adoption support. You've said adoption isn't an event but a lifelong journey, and you've built the programming to match that belief. Your own adoption story gives that work an authenticity that's hard to find.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Google.org is backing a $500K nonprofit track. Eagle Ventures is funding a $100K social enterprise track. We're looking for tools across family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would be grateful to have you on the panel.

You're rare on this list. You run a Fortune-level company, which means you can evaluate whether an innovation can actually scale and sustain itself financially. And you were adopted yourself, which means you can evaluate whether it actually serves the child. Most judges bring one of those lenses. You bring both.

The commitment is minimal. Our team screens all applications and sends 15 finalists to judges with scoring criteria and our analysis. Review and score on your schedule (staff welcome to support). One 90-minute meeting to select the top 8-10. You'd be invited to the final celebration on May 17 and featured prominently on the challenge website.

Overview: https://innovationchallenge-puce.vercel.app/

Would a brief call work to discuss?

[Sender]

---

### 22. Tamika Tasby | Subject Matter Expert
**Recommended Sender:** Akilah (friend and former Gates colleague)
**Strategy:** Direct invitation through warm intro

**Subject:** Foster care innovation challenge, judge invitation

Tamika,

Akilah suggested you might be interested in this, and I think she's right.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Two tracks: $500K from Google.org for nonprofits, $100K from Eagle Ventures for social enterprises. Three focus areas: family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would love to have you on the panel.

The William Julius Wilson Institute's cradle-to-career model at Harlem Children's Zone proves what's possible when you build the right infrastructure around families and communities. That's exactly the kind of thinking this panel needs. Foster care technology doesn't exist in isolation. The best solutions will connect to schools, healthcare, housing, and community support. Your work at Gates Foundation and now at HCZ means you've evaluated interventions at scale and you know what it takes to move from a promising pilot to something that actually holds.

Our team screens all applications and passes 15 finalists to judges with scoring criteria and our analysis. Review and score at your convenience. One 90-minute meeting to select the top 8-10. You'd be featured on the challenge website and invited to the celebration May 17.

Overview: https://innovationchallenge-puce.vercel.app/

Would you have 15 minutes for a call to discuss?

[Sender]

---

### 23. Lesli Snyder | Donor/Stakeholder
**Recommended Sender:** Howard Booker (introduction)
**Strategy:** Direct invitation through Howard Booker

**Subject:** Innovation Challenge judge invitation, In-N-Out connection

Lesli,

Howard Booker suggested I reach out. The In-N-Out Burger Foundation has been fighting child abuse since 1984, and in 2024 alone gave $2.8 million to roughly 110 organizations working in emergency shelter, foster care, and early intervention. That commitment runs deep.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Two tracks: $500K from Google.org for nonprofits, $100K from Eagle Ventures for social enterprises. We're looking for tools that help preserve families, improve outcomes for children in care, and reduce system friction.

We're building a panel of 12 judges and would love to have you on it.

The In-N-Out Foundation has funded hundreds of child welfare organizations. That means you've seen what actually works on the ground, what struggles to scale, and where the gaps are. For an innovation challenge, that perspective is gold. We don't just need judges who can spot a good idea. We need judges who know which ideas will still be standing in five years.

The process is simple. Our team screens all applications and sends 15 finalists to judges with scoring criteria and our analysis. Review and score on your own time. One 90-minute meeting to select the top 8-10. You'd be invited to the final celebration on May 17 and featured prominently on the website.

Overview: https://innovationchallenge-puce.vercel.app/

Could we set up a brief call to discuss?

[Sender]

---

### 24. Ty Montgomery | Lived Experience
**Recommended Sender:** DV or Justin
**Strategy:** Direct invitation

**Subject:** Foster care tech challenge, would value your perspective

Ty,

I came across your story and wanted to reach out. You grew up with 17 foster siblings. You serve on the board of Connections Homes. And through Next Legacy Partners, you evaluate early-stage ventures for a living. I don't think anyone else on our list carries all three of those at once.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Two funding tracks: $500K from Google.org for nonprofits, $100K from Eagle Ventures for social enterprises. Family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would love to have you.

Most innovation challenges in the social sector lack someone who can evaluate from both sides. You know what foster families actually need because you lived it. And you know what a viable venture looks like because you do that work every day at Next Legacy. When an applicant pitches a foster care technology solution, you can assess both whether it would genuinely help a family like yours and whether the team can actually build and sustain it. That dual lens is irreplaceable.

Our team screens all applications and passes 15 finalists with scoring criteria and our analysis. Review and score on your schedule. One 90-minute meeting to pick the top 8-10. You'd be featured on the challenge website and invited to celebrate the winners May 17.

Overview: https://innovationchallenge-puce.vercel.app/

Would 15 minutes work for a call?

[Sender]

---

### 25. Maggie Lin | Lived Experience
**Recommended Sender:** DV
**Strategy:** Direct invitation
**Organizational Grant:** $10,000 unrestricted capacity grant to Foster Nation. Mention on the call after she expresses interest, not in the initial email. Frame as: "Because judging means Foster Nation can't apply to the challenge, we'd like to provide a $10,000 unrestricted capacity grant to invest in your work."

**Subject:** Foster care innovation challenge, judge invitation

Maggie,

You built Foster Nation to help foster youth feel less alone and to empower them to defy the impossible. Seven years later, Sparks is connecting young people to real career paths, and organizations like Box are partnering with you because they see what you're building. That's not a side project. That's a movement.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Google.org backing a $500K nonprofit track, Eagle Ventures funding a $100K social enterprise track. Family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would love to have you serve. Judges' organizations are not eligible to apply to the challenge, and we want to be upfront about that. We believe your perspective on the panel is more valuable than any single application, and we'd like to talk about how Flourish Fund can support Foster Nation's work separately.

Your work focuses on one of the most underserved parts of the system: the transition to adulthood. You know what aging-out youth actually need because you've lived it and built an organization around it. When an applicant pitches a career readiness platform or a mentorship tool, you can tell us whether it addresses the real gaps or just the ones that look good in a grant application. That perspective keeps the panel honest.

Our team screens all applications and passes 15 finalists with scoring criteria and our analysis. Review and score on your schedule. One 90-minute meeting to pick the top 8-10. You'd be featured on the website and invited to the celebration May 17.

Overview: https://innovationchallenge-puce.vercel.app/

Would a brief call work to discuss?

[Sender]

---

### 26. Byron Johnson | Subject Matter Expert
**Recommended Sender:** DV
**Strategy:** Direct invitation

**Subject:** Flourish Fund Innovation Challenge, academic lens

Dr. Johnson,

The Institute for Global Human Flourishing at Baylor is doing something that most academic centers don't: connecting rigorous research to real-world outcomes. Your work on the Global Flourishing Study with Harvard and Gallup, and your earlier research showing that children in faith-based care are significantly safer, has given the field evidence it badly needed.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Google.org is backing a $500K nonprofit track. Eagle Ventures is funding a $100K social enterprise track. Three focus areas: family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would be grateful for your participation.

This panel needs someone who can evaluate whether proposed solutions are grounded in what the evidence actually shows about family stability, community support, and human flourishing. Your research on faith-based child welfare organizations provides a framework that's directly relevant. And your dual affiliation with Baylor and Harvard signals to both faith-based and secular applicants that this challenge takes rigor seriously.

The process is straightforward. Our team screens all applications and sends 15 finalists to judges with scoring criteria and our analysis. Review and score at your convenience. One 90-minute meeting to select the top 8-10. You'd be invited to the final celebration on May 17 and featured prominently on the website.

Overview: https://innovationchallenge-puce.vercel.app/

Would a 15-minute call work to discuss?

Dan

---

### 27. Greg Jones | Subject Matter Expert
**Recommended Sender:** DV or through Josh Yates / Tom Baldwin
**Strategy:** Direct invitation

**Subject:** Innovation Challenge judge, Belmont connection

Greg,

Belmont's commitment to foster care innovation isn't incremental. A $1M Reconstruct Challenge. A dedicated Foster Care Lab. The Dave Thomas Foundation's 2025 Adoption Advocate recognition. And the Hope Transforms campaign signaling that this is part of Belmont's long-term mission, not a one-year experiment.

Flourish Fund is launching a $600K-$800K Innovation Challenge for technology solutions in child welfare and family flourishing. Google.org backing a $500K nonprofit track, Eagle Ventures funding a $100K social enterprise track. Prevention, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would be honored to have you.

Your concept of traditioned innovation describes exactly what we're looking for: solutions that are technologically current but grounded in what actually matters for children and families. Having the president of Belmont on the panel would connect this challenge to the Innovation Labs ecosystem, the Tennessee DCS partnership, and the community of practice you've been building in Nashville.

Our team screens all applications and passes 15 finalists with scoring criteria and our analysis. Review and score on your time. One 90-minute meeting to pick the top 8-10. You'd be featured on the website and invited to the celebration May 17.

Overview: https://innovationchallenge-puce.vercel.app/

Would a call work to discuss?

Dan

---

### 28. Bishop W.C. Martin | Subject Matter Expert
**Recommended Sender:** DV
**Strategy:** Direct invitation

**Subject:** Possum Trot's story and a foster care challenge

Bishop Martin,

Your story continues to move people. Twenty-two families. Seventy-seven children. One small church in East Texas. What happened in Possum Trot proved that when a community decides to act, the system can be transformed. The Sound of Hope film brought that story to millions, and it continues to move people.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Google.org is backing a $500K nonprofit track. Eagle Ventures is funding a $100K social enterprise track. We're looking for tools across family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would be honored to have you on the panel.

Technology is part of the future of child welfare. But you've lived the truth that no technology replaces a family that says yes. We need a judge who will hold innovators accountable to that reality. Can this tool help a church in rural Texas connect families to children who need homes? Does it empower communities or does it add more paperwork? You've spent 30 years answering questions like these. Your presence would remind every applicant that their solution needs to serve real people in real communities, not just look good on a screen.

The commitment is small. Our team screens all applications and sends 15 finalists to you with scoring criteria and our analysis. Review and score on your schedule. One 90-minute meeting to select the top 8-10. You'd be invited to the final celebration on May 17 and featured prominently on the website.

Overview: https://innovationchallenge-puce.vercel.app/

Would a brief call work to discuss?

Dan

---

## TIER 4: COLD OUTREACH / LIMITED INFORMATION

---

### 29. Steve French | Donor/Stakeholder
**Recommended Sender:** DV
**Strategy:** Direct invitation (personal adoption connection discovered via LinkedIn)

**Subject:** Innovation Challenge, a personal connection

Steve,

I read something you shared recently that stopped me. A young farm girl in Missouri facing one of the hardest decisions of her life. Because of her courage, Barbara and Bob French brought you home. That story shapes everything you've built since.

The Signatry has facilitated over $3.5 billion to nonprofits. You've spent your career helping generous families think about stewardship and lasting impact. But I suspect this invitation will resonate at a level beyond professional expertise.

Flourish Fund is launching a $600K-$800K Innovation Challenge for the best technology solutions in child welfare and family flourishing. Google.org backing a $500K nonprofit track, Eagle Ventures funding a $100K social enterprise track. Family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would value your perspective on the panel.

You see the giving landscape from a rare vantage point. You know what motivates generous families, what kinds of organizations they want to invest in, and what it takes for a mission to sustain itself beyond the initial gift. That sustainability lens is something this panel needs. But you also bring something deeper: you know what it means to be on the receiving end of someone's decision to open their home.

Our team screens all applications and passes 15 finalists to judges with scoring criteria and our analysis. Review and score on your time. One 90-minute meeting to select the top 8-10. You'd be featured on the website and invited to celebrate the winners May 17 at The Understory.

Overview: https://innovationchallenge-puce.vercel.app/

Would a call work to discuss?

Dan

---

### 30. Brad Fieldhouse | Donor/Stakeholder
**Recommended Sender:** DV
**Strategy:** Direct invitation

**Subject:** Innovation Challenge judge invitation

Brad,

I've been learning about your work. Two decades of community transformation through Kingdom Causes and City Net, and daily experience with the intersection of homelessness and foster care, because youth aging out of the system are among the most at-risk for ending up in the very situations City Net addresses.

Flourish Fund is launching a $600K-$800K Innovation Challenge for technology solutions in child welfare and family flourishing. Google.org backing a $500K nonprofit track, Eagle Ventures funding a $100K social enterprise track. Family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would appreciate your participation.

This panel needs someone who knows what adoption of a new tool actually looks like on the ground. A technology platform doesn't matter if the caseworker or the community volunteer can't use it. You've built organizations that serve people in crisis every day. That practical lens would complement the philanthropic and policy voices elsewhere on the panel.

Our team screens all applications and passes 15 finalists to judges with scoring criteria and our analysis. Review and score on your time. One 90-minute meeting to select the top 8-10. You'd be featured on the website and invited to the celebration May 17.

Overview: https://innovationchallenge-puce.vercel.app/

Would 15 minutes work for a call?

Dan

---

### 31. Matthew Cathy | Donor/Stakeholder
**Recommended Sender:** Through WinShape (Riley Green or Callie Priest)
**Strategy:** Warm intro through WinShape leadership

**Subject:** Innovation Challenge judge, WinShape connection

Matthew,

Your family's commitment to foster care goes back to your grandfather. S. Truett Cathy established the first WinShape foster home in 1987, and the WinShape Homes program has been caring for children ever since. The Foster Care Collective gatherings that your family hosts have become an important space for leaders working on child welfare innovation.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Two tracks: $500K from Google.org for nonprofits, $100K from Eagle Ventures for social enterprises. We're looking for tools across family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would love to have a member of the next generation of the Cathy family on the panel.

You carry a family legacy in this space that few can match. Bringing that perspective to a technology innovation challenge would honor what WinShape has built while helping shape what comes next. The applicants in this challenge are building tools that could serve the very families WinShape supports.

The commitment is light. Our team screens all applications and sends 15 finalists with scoring criteria and our analysis. Review and score at your convenience. One 90-minute meeting to select the top 8-10. You'd be invited to the final celebration on May 17 and featured prominently on the website.

Overview: https://innovationchallenge-puce.vercel.app/

Would a call work to discuss?

[Sender]

---

### 32. Kirsten Winters | Donor/Stakeholder
**Recommended Sender:** Justin Steele (through Mike Winters relationship)
**Strategy:** Direct invitation alongside Mike

**Subject:** Innovation Challenge judging, alongside Mike

Kirsten,

You may have heard from Mike about Flourish Fund's Innovation Challenge. We've been in conversation with him about the judging panel and wanted to extend the invitation to you as well.

We're launching a $600K-$800K competitive funding program to find the best technology solutions for child welfare and family flourishing. Google.org is backing a $500K nonprofit track. Eagle Ventures is funding a $100K social enterprise track. Three focus areas: family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would welcome your participation, either alongside Mike or independently.

The process is easy. Our team screens all applications and sends 15 finalists to judges with scoring criteria and our preliminary analysis. Review and score on your own time. One 90-minute meeting to select the top 8-10. You'd be invited to the final celebration on May 17 and featured prominently on the website.

Overview: https://innovationchallenge-puce.vercel.app/

Would a brief call work to discuss?

Justin

---

### 33. Scott Hansen | Subject Matter Expert (CAFO connection unverified)
**Recommended Sender:** DV
**Strategy:** Needs verification before outreach
**NOTE:** Research was unable to verify Scott Hansen's formal role at CAFO. The organization's president is Jedd Medefind and the board chair is Dr. Haag. Recommend confirming his exact title and CAFO affiliation before sending.

**Subject:** Innovation Challenge judge, CAFO connection

Scott,

CAFO's network of 150+ organizations represents the largest mobilization of faith-community resources for orphans and vulnerable children in the country. The annual Summit draws thousands, and the coalition's influence on how churches engage with foster care and adoption is unmatched.

Flourish Fund is launching a $600K-$800K Innovation Challenge to find the best technology solutions for child welfare and family flourishing. Google.org is backing a $500K nonprofit track. Eagle Ventures is funding a $100K social enterprise track. Three focus areas: family preservation, foster youth wellbeing, and system efficiency.

We're assembling 12 judges and would value the CAFO perspective on the panel.

The faith community is the largest untapped distribution channel for foster care innovation. Churches that want to help often don't know where to start, and the tools available to them are limited. A judge who understands what churches and faith-based organizations actually need on the ground would help us fund solutions that get adopted, not just built.

The commitment is small. Our team screens all applications and sends 15 finalists with scoring criteria and our analysis. Review and score on your schedule. One 90-minute meeting to select the top 8-10. You'd be invited to the final celebration on May 17 and featured prominently on the website.

Overview: https://innovationchallenge-puce.vercel.app/

Would a call work to discuss?

Dan

---

## ADDITIONAL NOTES

### Judges Not Included (Placeholder Entries in CSV)
The following entries in the original CSV appear to be placeholders or organizational notes rather than specific judge candidates, so no emails were drafted:
- "Elizabeth Pishny? Maab? Megan?" (Google) - needs specific person identified
- "Murdock or Lilly?" - needs specific person identified
- "Former State DCF leads?" / "Aly Brodsky? Rob Geen?" - needs specific person identified
- "Anyone from WinShape? (Riley Green or Callie Priest)" - could be contacted as pathway to Matthew Cathy

### Recommended Outreach Sequence (Domino Strategy)
Based on research, here's the recommended order for sending invitations:

**Wave 1 (Immediate, Warmest Contacts):**
1. Michael Allen (already asked to judge)
2. Wes Hartley (per MOU)
3. Mike Winters (warm, pending $200K)
4. Nathan Aleman (DV has call)

**Wave 2 (After Wave 1 confirmations, use their names):**
5. Josh Yates or Tom Baldwin (reciprocity)
6. JooYeun Chang (strongest substantive fit)
7. Bill & Crissy Haslam (Understory sponsors)
8. Sarah Gesiriech (policy alignment)
9. Steve Moore (philanthropic evaluation expertise)
10. Audrey Haque (donor cultivation)

**Wave 3 (After building panel momentum):**
11. Chris Tomlin (through Jared/DV)
12. Sixto Cancel (Justin relationship)
13. Tim Tebow (Wes/Vip connection)
14. David Platt (through Pinkston/Jedd)
15. Debra Waller (For Others network)
16. Tamika Tasby (through Akilah)
17. Greg Jones (through Belmont connection)
18. Byron Johnson (academic credibility)

**Wave 4 (Harder targets, use full panel for social proof):**
19. Bear Rinehart (through For Others/Tomlin)
20. Kirk Franklin (through management)
21. Simone Biles (through management)
22. Christian Bale (through representatives)
23. Ty Montgomery
24. Maggie Lin
25. Bishop W.C. Martin

**Wave 5 (Lower priority or needs more info):**
26. Connie Ballmer (may designate someone)
27. Brad Fieldhouse
28. Steve French
29. Lesli Snyder (through Howard Booker)
30. Matthew Cathy (through WinShape)
31. Kirsten Winters (through Mike)
32. Scott Hansen (needs verification)

### Key Social Proof Names to Drop (Once Confirmed)
As judges confirm, add their names to subsequent emails. Strongest name-drops by audience:
- For faith community targets: Michael Allen, Bill Haslam, Chris Tomlin
- For policy/government targets: Sarah Gesiriech, Bill Haslam, JooYeun Chang
- For donors/philanthropists: Connie Ballmer, Steve Moore, Audrey Haque
- For lived experience targets: Sixto Cancel, Simone Biles, Kirk Franklin
- For tech/innovation targets: JooYeun Chang, Josh Yates, Ty Montgomery
