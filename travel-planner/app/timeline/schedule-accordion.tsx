'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import {
  ChevronDown,
  Plane,
  Train,
  Car,
  GraduationCap,
  PartyPopper,
  BedDouble,
  MapPin,
  Clock,
  Users,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react'

// ── Schedule Data ────────────────────────────────────────────────────

type EventType = 'flight' | 'train' | 'drive' | 'tour' | 'event' | 'stay'

interface ScheduleEvent {
  time?: string
  title: string
  type: EventType
  status?: 'booked' | 'tbd'
  who?: string
  details?: string[]
  confirmation?: string
  location?: string
}

interface ScheduleDay {
  date: string
  dow: string
  city: string
  cityColor: string
  dotColor: string
  events: ScheduleEvent[]
}

const SCHEDULE: ScheduleDay[] = [
  {
    date: 'May 29', dow: 'Friday', city: 'Oakland → DC → Bruffs Island',
    cityColor: 'bg-[#c8dcd0]', dotColor: 'bg-[#4a8c6a]',
    events: [
      { time: '9:38 AM', title: 'Fly SFO → DCA', type: 'flight', status: 'booked', who: 'All 6', confirmation: 'KJIFEX + UNBWCX', details: ['Alaska AS8 · Boeing 737-800', 'Arrive 5:59 PM · Nonstop · 5h 21m', 'Seats 9A–9F (Premium Class)', 'KJIFEX: Justin + Siena · UNBWCX: Sally + Jaelyn + Zada + Eliza', 'Total: $4,876.22 (air + seat upgrades)'] },
      { time: '6:00 PM', title: 'Pick up rental car at DCA', type: 'drive', status: 'booked', who: 'Justin', confirmation: '11855091US3', details: ['Avis · GMC Yukon Denali', '2600 Richmond Hwy, Arlington VA'] },
      { time: 'Evening', title: 'Drive to Bruffs Island', type: 'drive', who: 'All 6', details: ['Eastern Shore, MD (~1.5 hrs from DCA)', 'Steele family property'] },
    ],
  },
  {
    date: 'May 30', dow: 'Saturday', city: 'Bruffs Island',
    cityColor: 'bg-[#c8dcd0]', dotColor: 'bg-[#4a8c6a]',
    events: [
      { title: 'Knorr Family Reunion', type: 'event', who: 'All 6', details: ['Talbot County, MD (Eastern Shore)', 'Full day with extended family'] },
    ],
  },
  {
    date: 'May 31', dow: 'Sunday', city: 'Bruffs Island',
    cityColor: 'bg-[#c8dcd0]', dotColor: 'bg-[#4a8c6a]',
    events: [
      { title: 'Knorr Family Reunion (cont.)', type: 'event', who: 'All 6', details: ['Last day on Bruffs Island'] },
    ],
  },
  {
    date: 'Jun 1', dow: 'Monday', city: 'Bruffs Island → Boston',
    cityColor: 'bg-olive/15', dotColor: 'bg-olive',
    events: [
      { time: '~8:00 AM', title: 'Leave Bruffs Island for BWI', type: 'drive', who: 'All 6', details: ['Sally drives; ~1.5 hrs to BWI'] },
      { time: '10:40 AM', title: 'Fly BWI → BOS', type: 'flight', status: 'booked', who: 'Justin, Siena, Jaelyn, Zada', confirmation: 'AWDOR6', details: ['Southwest 1062 · Boeing 737-800', 'Arrives 12:10 PM · Nonstop · 1h 30m', 'Seats 5C, 6A, 6B, 6C (Choice Extra)', 'Sally returns car to DCA, heads to Mount Vernon'] },
      { time: '~1:00 PM', title: 'Check in at Le Meridien Cambridge', type: 'stay', status: 'booked', confirmation: '75943096 / 75969264', location: '20 Sidney St, Cambridge MA', details: ['2 rooms · 2 nights (Jun 1–3)', '117K Bonvoy pts + $890.51', 'Platinum Elite: room upgrade + late checkout'] },
      { time: '2:00 PM', title: 'Harvard University tour', type: 'tour', who: 'Justin, Siena, Jaelyn, Zada', location: 'Smith Campus Center, 1350 Massachusetts Ave', details: ['~45–60 min · Free', '5 min walk from hotel', 'Register on Eventbrite (opens Fri before)'] },
    ],
  },
  {
    date: 'Jun 2', dow: 'Tuesday', city: 'Boston',
    cityColor: 'bg-olive/15', dotColor: 'bg-olive',
    events: [
      { time: '10:00 AM', title: 'Boston College Eagle Eye Visit', type: 'tour', who: 'Justin, Siena, Jaelyn, Zada', location: 'Chestnut Hill, MA', details: ['Info session + student-led tour (~2 hrs)', 'Register at bc.edu/admission/visit'] },
      { time: 'Afternoon', title: 'Northeastern University tour', type: 'tour', status: 'tbd', who: 'Justin, Siena, Jaelyn, Zada', location: 'Huntington Ave, Boston', details: ['Info session + campus tour (~1h 45m)', 'Register at apply.northeastern.edu', 'Check portal for available afternoon slots'] },
    ],
  },
  {
    date: 'Jun 3', dow: 'Wednesday', city: 'Boston → New York',
    cityColor: 'bg-navy/15', dotColor: 'bg-navy',
    events: [
      { time: '~8:15 AM', title: 'Uber to South Station', type: 'drive', who: 'Justin, Siena, Jaelyn, Zada', details: ['20 min from Le Meridien'] },
      { time: '9:10 AM', title: 'Acela 2159 BOS → NYC', type: 'train', status: 'booked', who: 'Justin, Siena, Jaelyn, Zada', confirmation: 'E12688', details: ['Arrives 12:51 PM · Moynihan Train Hall', 'Car 3 — Seats 16F, 16D, 16C, 16A', 'Business class · $315 total ($78.75/person)', 'Ticket #1010745612695 · Amex 3005'] },
      { time: '~1:00 PM', title: 'Check in at SpringHill Suites Chelsea', type: 'stay', status: 'booked', confirmation: '76080343 / 76099632', location: '140 W 28th St, New York NY', details: ['2 rooms · 2 nights (Jun 3–5)', '123K Bonvoy pts + $821.33', 'Free hot breakfast · Request floors 26+'] },
      { time: '2:00 PM', title: 'Columbia University tour', type: 'tour', status: 'tbd', who: 'Justin + 3 girls', location: 'Morningside Heights, NYC', details: ['⏳ Waiting for portal — June dates not yet released as of Apr 29', 'Tour scanner monitoring; will alert when bookable', 'Standard slots: 12pm, 2pm, 3pm campus tours', 'Register at apply.college.columbia.edu', '25 min on 1-train from 28th St'] },
      { time: 'Late afternoon', title: 'Pre-show dinner', type: 'event', status: 'tbd', who: 'Justin + 3 girls', details: ['Plan: Joe Allen (326 W 46th St) — book May 4 when 30-day OpenTable opens', 'Backup: Becco (call 212-397-7597 directly, 6-week phone window)', 'Target 5:00 or 5:30 PM'] },
      { time: '7:00 PM', title: 'Hamilton', type: 'event', status: 'booked', who: 'Justin + 3 girls', location: 'Richard Rodgers Theatre, 226 W 46th St', details: ['4 tix · FMEZZ Row C, Seats 111-114 · $998 total', 'Runtime ~2h 45m incl intermission', '15 min walk from SpringHill (28th St) to Richard Rodgers'] },
    ],
  },
  {
    date: 'Jun 4', dow: 'Thursday', city: 'New York',
    cityColor: 'bg-navy/15', dotColor: 'bg-navy',
    events: [
      { time: 'Morning', title: 'Sally: Amtrak DC → NYC', type: 'train', status: 'tbd', who: 'Sally', details: ['Sally booking herself — recommend ~8am Acela for ~10:50 AM Penn arrival', 'Aim to make NYU 3pm tour'] },
      { time: '12:00 PM ET', title: '🎤 bbdevdays speaker session (virtual)', type: 'event', status: 'booked', who: 'Justin', location: 'Present from hotel (SpringHill Suites Chelsea)', details: ['"Shipping at Speed: How AI Tools are Reshaping Software Development"', 'Co-presenter: Brent Chudoba (former CRO SurveyMonkey, COO Calendly) on Grasshopper Signup', 'Justin presents Kindora\'s Raiser\'s Edge NXT integration built with Claude Code in 2 evenings (25 features)', 'Platform: Goldcast'] },
      { time: 'Lunch', title: 'Lunch in Greenwich Village', type: 'event', who: 'All 5 (Sally rejoins)', details: ['Pick up Sally at Penn or hotel', 'Walk down to NYU area for lunch'] },
      { time: '3:00 PM', title: 'NYU campus tour — REGISTERED', type: 'tour', status: 'booked', who: 'All 5', location: 'Bonomi Family Admissions Center, 383 Lafayette St', details: ['~90 min tour', 'Moved from 11am to 3pm to avoid bbdevdays conflict', '1 stop south from 28th St or 20 min walk'] },
      { time: '5:30 PM', title: 'Trecolori dinner — BOOKED', type: 'event', status: 'booked', who: 'All 5', location: 'Trattoria Trecolori, 254 W 47th St', details: ['Italian · 4.7 OpenTable rating', 'Party of 5 · Standard seating', '15 min grace period — call (212) 997-4540 if running late'] },
      { time: '7:00 PM', title: 'Stranger Things: The First Shadow', type: 'event', status: 'booked', who: 'All 5', location: 'Marquis Theatre, 210 W 46th St', details: ['5 tix · Mezzanine F112-F116 · $943.50 total', '1 block from Trecolori, easy walk after dinner', 'Runtime ~2.5 hours', 'Conf 206865969-8196555'] },
    ],
  },
  {
    date: 'Jun 5', dow: 'Friday', city: 'NYC → DC → Charlottesville',
    cityColor: 'bg-rust/12', dotColor: 'bg-rust',
    events: [
      { time: '8:23 AM', title: 'Train NYC → DC (NE Regional 141) — BOOKED', type: 'train', status: 'booked', confirmation: 'E21DD3 + 07F662', who: 'All 5 (whole family on same train)', details: ['Penn Station → Union Station', 'Arrive 11:45 AM · Business class', 'Justin + 3 girls: seats 15D/15F/16D/16F (conf E21DD3, $528)', 'Sally: seat 14F right in front (conf 07F662, $184)', 'Total $712 across both bookings'] },
      { time: '2:00 PM', title: 'Howard University tour', type: 'tour', status: 'tbd', who: 'All 5', location: 'Howard University, Washington DC', details: ['⚠️ Currently FULL — tour scanner monitoring for openings', 'Hoping for Individual & Family Tour Fri Jun 5 at 2:00 PM', 'Will alert via email + SMS (415-844-0345) when bookable', 'Register at applyhu.howard.edu when open'] },
      { time: '12:00 PM', title: 'Pick up Avis Equinox at Union Station', type: 'drive', status: 'booked', confirmation: '11859662US3', who: 'All 5', details: ['Avis · 99 H Street NE, Union Station', 'Chevy Equinox (mid-size SUV)', 'Return at DCA Jun 8 by 11:30 AM · $204.11', '⚠️ May be tight for 5 adults + luggage — consider counter upgrade'] },
      { time: '~3:45 PM', title: 'Drive DC → Charlottesville', type: 'drive', who: 'All 5', details: ['~2.5 hours after Howard tour', 'Or earlier if Howard slot doesn\'t open'] },
      { time: '~6:15 PM', title: 'Check in at Airbnb Penthouse', type: 'stay', status: 'booked', confirmation: 'HMH2AE84QZ', location: '118 W Main St, Charlottesville VA', details: ['2 nights (Jun 5–7) · $2,570.61', '5 guests + 1 child', 'Smart lock check-in (Airbnb opens 4 PM)', 'Overlooks Downtown Mall', 'Justin, Sally & 3 girls reunite here (Eliza already with grandparents)'] },
    ],
  },
  {
    date: 'Jun 6', dow: 'Saturday', city: 'Charlottesville',
    cityColor: 'bg-rust/12', dotColor: 'bg-rust',
    events: [
      { time: '10:20 AM', title: "UVA Dean's Welcome & Tour", type: 'tour', who: 'All 5', location: 'University of Virginia', details: ['Justin is UVA alum (BS ChemE 2000–04)', "Sally's alma mater too (BA 2000–04)", 'Register at admission.virginia.edu/visit'] },
      { time: 'Afternoon', title: 'Explore Charlottesville', type: 'event', who: 'All 5', details: ['Downtown Mall, wineries, restaurants', 'Historic university grounds'] },
    ],
  },
  {
    date: 'Jun 7', dow: 'Sunday', city: 'Charlottesville → Mount Vernon',
    cityColor: 'bg-sand/80', dotColor: 'bg-clay',
    events: [
      { time: '11:00 AM', title: 'Checkout + drive to Mount Vernon', type: 'drive', who: 'All 5', details: ['Charlottesville → Alexandria VA (~2 hrs)', "Sally's parents: 4722 Pole Rd, Alexandria"] },
      { time: 'Afternoon', title: 'Arrive at grandparents\'', type: 'stay', who: 'All 6 (reunite with Eliza)', details: ['Mount Vernon, Alexandria VA', 'Eliza has been here since Jun 1', 'Everyone together again!'] },
    ],
  },
  {
    date: 'Jun 8', dow: 'Monday', city: 'Mount Vernon → New Orleans',
    cityColor: 'bg-gold/20', dotColor: 'bg-gold',
    events: [
      { time: '~9:30 AM', title: 'Drop off rental car at DCA', type: 'drive', status: 'booked', confirmation: '11859662US3', who: 'Justin + Sally', details: ['Avis Equinox return · 2600 Richmond Hwy, Arlington VA', 'Due by 11:30 AM — drop early for flight'] },
      { time: '11:35 AM', title: 'Fly DCA → MSY', type: 'flight', status: 'booked', who: 'Justin + Sally', confirmation: 'AWREFA', details: ['Southwest 311 · Boeing 737-700', 'Arrives 1:10 PM · Nonstop · 2h 35m', 'Seats 2B, 2C (Choice Extra)'] },
      { time: '~2:00 PM', title: 'Check in at Four Seasons NOLA', type: 'stay', status: 'booked', who: 'Justin + Sally', location: 'Four Seasons Hotel, New Orleans', details: ['Room booked automatically by Camelback (per Apr 12 attendance form)', 'Sally also covered as additional registrant', '$1,000 travel stipend processing within 7-9 business days'] },
      { time: 'Before 3:30 PM', title: 'Arrive at Four Seasons (latest)', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel' },
      { time: '4:30 PM CT', title: 'Fireside chat: Shawna Young + Aaron Walker', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel', details: ['Camelback CEO + Ruthless for Good VC fund founder', 'Cohorts 15 & 16 pre-conference programming'] },
      { time: '6:00 – 8:30 PM CT', title: 'Cohort 15 & 16 dinner and networking', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel' },
    ],
  },
  {
    date: 'Jun 9', dow: 'Tuesday', city: 'New Orleans · Guardian Summit Day 1',
    cityColor: 'bg-gold/20', dotColor: 'bg-gold',
    events: [
      { time: '8:00 AM – 4:00 PM CT', title: 'Office Hours', type: 'event', who: 'Justin', location: 'Four Seasons Hotel', details: ['With blackout times'] },
      { time: '10:30 AM – 12:30 PM CT', title: 'Alumni and Fellows Brunch', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel' },
      { time: '1:00 – 4:00 PM CT', title: 'Blueprint Pitch Competition', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel' },
      { time: '7:00 – 10:00 PM CT', title: 'Welcome Reception and Dinner', type: 'event', who: 'Justin + Sally', location: 'River Ballroom, Four Seasons' },
    ],
  },
  {
    date: 'Jun 10', dow: 'Wednesday', city: 'New Orleans · Guardian Summit Day 2',
    cityColor: 'bg-gold/20', dotColor: 'bg-gold',
    events: [
      { time: '8:00 – 10:00 AM CT', title: 'Networking Breakfast', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel' },
      { time: '8:30 – 11:30 AM CT', title: 'Founder Workshop Series', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel', details: ['Panels on fundraising — family foundations, featured Camelback founders, ESO leaders, aligned partners', '45-60 min sessions', 'Topics + facilitators TBA early next week'] },
      { time: '12:00 PM CT', title: 'Opening Plenary + Lunch', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel', details: ['"Guardians of Talent: Unlocking the Founders Poised to Transform the Economy"'] },
      { time: '1:30 – 3:30 PM CT', title: 'Afternoon Workshops', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel', details: ['Topics TBA early next week'] },
      { time: '5:00 – 8:45 PM CT', title: 'Networking Reception + Awards Gala', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel', details: ['Ruthless for Good awards announced', 'Pitch Competition awards announced'] },
      { time: '9:00 – 10:00 PM CT', title: 'After Party w/ DJ', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel' },
    ],
  },
  {
    date: 'Jun 11', dow: 'Thursday', city: 'New Orleans · Guardian Summit Day 3 (closing)',
    cityColor: 'bg-gold/20', dotColor: 'bg-gold',
    events: [
      { time: '8:00 AM – 3:00 PM CT', title: 'Office Hours', type: 'event', who: 'Justin', location: 'Four Seasons Hotel', details: ['Blackouts 9-10:30 AM'] },
      { time: '8:00 – 9:00 AM CT', title: 'Networking Breakfast', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel', details: ['Food until 10 AM'] },
      { time: '9:00 – 11:00 AM CT', title: 'Morning Plenary + sessions', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel', details: ['State of Camelback / Vision for the Future', 'Guardians of Wellness: "Returning to the Well: Water Birthing Your Legacy"', 'Guardians of Venture Philanthropy: New Funding Vehicles for Innovation'] },
      { time: '11:30 AM – 12:30 PM CT', title: 'Concurrent Block 1', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel', details: ['Guardians of Higher Ed: Entrepreneurship + Innovation at HBCUs', 'Building Ecosystems of Innovation and Educational Excellence', 'Start-up to Exit: What it Takes to Build a Venture-Backed Company in 2026'] },
      { time: '12:30 – 2:30 PM CT', title: 'Lunch + Keynote', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel' },
      { time: '3:00 – 4:00 PM CT', title: 'Concurrent Block 2', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel', details: ['Guardians of Partnerships: Wireless and Education — Designing for Larger Access', "Building NOLA's Black Entrepreneurial Backbone", 'Future of Learning: What Do Kids Need to Learn in the Age of AI?'] },
      { time: '4:00 – 5:30 PM CT', title: 'Closing Reception', type: 'event', who: 'Justin + Sally', location: 'Four Seasons Hotel', details: ['⚠️ Early flight tomorrow — 7:30 AM departure'] },
    ],
  },
  {
    date: 'Jun 12', dow: 'Friday', city: 'New Orleans → Mount Vernon',
    cityColor: 'bg-sand/80', dotColor: 'bg-clay',
    events: [
      { time: '7:30 AM', title: 'Fly MSY → DCA', type: 'flight', status: 'booked', who: 'Justin + Sally', confirmation: 'AWREFA', details: ['Southwest 222 · Boeing 737-700', 'Arrives 11:00 AM · Nonstop · 2h 30m', 'Seats 2B, 2C (Choice Extra)'] },
      { time: '~11:30 AM', title: 'Back to Mount Vernon', type: 'drive', who: 'Justin + Sally', details: ['Rejoin girls at grandparents\'', '4722 Pole Rd, Alexandria VA'] },
      { time: 'Afternoon', title: 'Family time + pack for home', type: 'event', who: 'All 6', details: ['Last full day on the East Coast'] },
    ],
  },
  {
    date: 'Jun 13', dow: 'Saturday', city: 'Mount Vernon → Oakland',
    cityColor: 'bg-navy/15', dotColor: 'bg-navy',
    events: [
      { time: '6:59 PM', title: 'Fly DCA → SFO', type: 'flight', status: 'booked', who: 'All 6', confirmation: 'KJIFEX + UNBWCX', details: ['Alaska AS7 · Boeing 737-800', 'Arrive 9:56 PM · Nonstop', 'Seats 9A–9F (Premium Class)', 'Everyone flies home!'] },
    ],
  },
]

// ── Icon helper ──────────────────────────────────────────────────────

function EventIcon({ type }: { type: EventType }) {
  const size = 15
  switch (type) {
    case 'flight': return <Plane size={size} className="text-navy -rotate-45" />
    case 'train': return <Train size={size} className="text-navy" />
    case 'drive': return <Car size={size} className="text-navy" />
    case 'tour': return <GraduationCap size={size} className="text-olive" />
    case 'event': return <PartyPopper size={size} className="text-rust" />
    case 'stay': return <BedDouble size={size} className="text-clay" />
  }
}

// ── Accordion Component ──────────────────────────────────────────────

export function ScheduleAccordion() {
  const [openDays, setOpenDays] = useState<Set<number>>(() => {
    // Start with today's/first upcoming day open, or day 0
    return new Set([0])
  })
  const [openEvents, setOpenEvents] = useState<Set<string>>(new Set())

  function toggleDay(idx: number) {
    setOpenDays(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  function toggleEvent(key: string) {
    setOpenEvents(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  function expandAll() {
    setOpenDays(new Set(SCHEDULE.map((_, i) => i)))
  }

  function collapseAll() {
    setOpenDays(new Set())
    setOpenEvents(new Set())
  }

  return (
    <div>
      {/* Controls */}
      <div className="flex gap-3 mb-3">
        <button onClick={expandAll} className="text-xs text-navy hover:text-ink font-medium transition-colors">
          Expand all
        </button>
        <span className="text-sand">|</span>
        <button onClick={collapseAll} className="text-xs text-navy hover:text-ink font-medium transition-colors">
          Collapse all
        </button>
      </div>

      {/* Day cards */}
      <div className="space-y-2">
        {SCHEDULE.map((day, dayIdx) => {
          const isOpen = openDays.has(dayIdx)
          const bookedCount = day.events.filter(e => e.status === 'booked').length
          const eventCount = day.events.length

          return (
            <div key={dayIdx} className="bg-white rounded-xl border border-sand overflow-hidden shadow-sm">
              {/* Day header */}
              <button
                onClick={() => toggleDay(dayIdx)}
                className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-paper/50 transition-colors text-left"
              >
                {/* City dot */}
                <div className={cn('w-3 h-3 rounded-full shrink-0', day.dotColor)} />

                {/* Day info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-sm">{day.date}</span>
                    <span className="text-xs text-stone">{day.dow}</span>
                  </div>
                  <div className="text-xs text-stone truncate">{day.city}</div>
                </div>

                {/* Meta badges */}
                <div className="flex items-center gap-2 shrink-0">
                  {bookedCount > 0 && (
                    <span className="flex items-center gap-0.5 text-[10px] font-medium text-olive bg-olive/10 px-1.5 py-0.5 rounded">
                      <CheckCircle2 size={10} /> {bookedCount}
                    </span>
                  )}
                  <span className="text-[10px] text-stone">{eventCount} {eventCount === 1 ? 'event' : 'events'}</span>
                  <ChevronDown size={16} className={cn('text-stone transition-transform', isOpen && 'rotate-180')} />
                </div>
              </button>

              {/* Day events (expanded) */}
              {isOpen && (
                <div className="border-t border-sand/60 px-4 pb-4">
                  <div className="relative ml-1.5 pl-5 border-l-2 border-sand/40 mt-3 space-y-0.5">
                    {day.events.map((event, evIdx) => {
                      const eventKey = `${dayIdx}-${evIdx}`
                      const isEventOpen = openEvents.has(eventKey)
                      const hasDetails = !!(event.details?.length || event.confirmation || event.location)

                      return (
                        <div key={evIdx}>
                          {/* Event row */}
                          <button
                            onClick={() => hasDetails && toggleEvent(eventKey)}
                            className={cn(
                              'w-full flex items-start gap-3 py-2.5 px-3 rounded-lg text-left transition-colors -ml-3',
                              hasDetails && 'hover:bg-paper/80 cursor-pointer',
                              !hasDetails && 'cursor-default',
                              isEventOpen && 'bg-paper/60',
                            )}
                          >
                            {/* Timeline dot */}
                            <div className="absolute left-[-5px] mt-[11px]">
                              <div className={cn(
                                'w-2 h-2 rounded-full',
                                event.status === 'booked' ? 'bg-olive' : event.status === 'tbd' ? 'bg-gold' : 'bg-sand',
                              )} />
                            </div>

                            {/* Icon */}
                            <div className="mt-0.5 shrink-0">
                              <EventIcon type={event.type} />
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-sm font-medium text-ink">{event.title}</span>
                                {event.status === 'booked' && <CheckCircle2 size={13} className="text-olive shrink-0" />}
                                {event.status === 'tbd' && <AlertCircle size={13} className="text-gold shrink-0" />}
                              </div>
                              <div className="flex items-center gap-3 mt-0.5 text-xs text-stone">
                                {event.time && <span className="flex items-center gap-1"><Clock size={10} />{event.time}</span>}
                                {event.who && <span className="flex items-center gap-1"><Users size={10} />{event.who}</span>}
                              </div>
                            </div>

                            {/* Expand indicator */}
                            {hasDetails && (
                              <ChevronDown size={14} className={cn('text-stone/50 mt-1 shrink-0 transition-transform', isEventOpen && 'rotate-180')} />
                            )}
                          </button>

                          {/* Event details (expanded) */}
                          {isEventOpen && hasDetails && (
                            <div className="ml-8 mb-2 pl-3 border-l-2 border-olive/20 space-y-1.5 text-xs text-stone">
                              {event.location && (
                                <div className="flex items-start gap-1.5">
                                  <MapPin size={11} className="mt-0.5 text-rust shrink-0" />
                                  <span>{event.location}</span>
                                </div>
                              )}
                              {event.confirmation && (
                                <div className="flex items-center gap-1.5">
                                  <CheckCircle2 size={11} className="text-olive shrink-0" />
                                  <span>Conf: <span className="font-mono font-medium text-olive">{event.confirmation}</span></span>
                                </div>
                              )}
                              {event.details?.map((d, i) => (
                                <div key={i} className="pl-[17px]">{d}</div>
                              ))}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
