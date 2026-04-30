import { GUARDIAN_SUMMIT } from '@/data/trip'
import { Crown, Clock, Mic2, Award, AlertTriangle } from 'lucide-react'

export default function NOLAPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-medium" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>Guardian Summit</h1>
        <p className="text-stone text-sm">June 8–11 · Four Seasons Hotel, New Orleans</p>
        <p className="text-xs text-stone mt-1 italic">{GUARDIAN_SUMMIT.theme}</p>
      </div>

      {/* Key info card */}
      <div className="bg-gold/10 rounded-lg border border-gold/30 p-4">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle size={15} className="text-gold" />
          <h3 className="text-sm font-semibold text-[#7a6518]">Key dates</h3>
        </div>
        <div className="grid sm:grid-cols-2 gap-2 text-xs text-stone">
          <div><span className="text-ink font-medium">RSVP deadline:</span> {GUARDIAN_SUMMIT.rsvpDeadline}</div>
          <div><span className="text-ink font-medium">Hotel deadline:</span> {GUARDIAN_SUMMIT.hotelDeadline}</div>
          <div><span className="text-ink font-medium">Host:</span> {GUARDIAN_SUMMIT.host}</div>
          <div><span className="text-ink font-medium">Venue:</span> {GUARDIAN_SUMMIT.venue}</div>
        </div>
        <div className="mt-3 text-xs text-olive bg-olive/5 rounded p-2">
          Camelback is booking the room (covers Justin + Sally). Travel stipend processing within 7-9 business days.
        </div>
      </div>

      {/* Schedule */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Clock size={18} className="text-navy" />
          <h2 className="text-lg font-semibold">Schedule</h2>
        </div>
        {GUARDIAN_SUMMIT.scheduleNote && (
          <p className="text-xs text-stone italic mb-3">{GUARDIAN_SUMMIT.scheduleNote}</p>
        )}
        <div className="space-y-4">
          {GUARDIAN_SUMMIT.schedule.map(day => (
            <div key={day.day} className="bg-white rounded-lg border border-sand overflow-hidden">
              <div className="bg-navy/5 px-4 py-2 border-b border-sand">
                <span className="text-sm font-semibold text-navy">{day.day}</span>
                <span className="text-xs text-stone ml-2">{day.label}</span>
              </div>
              <div className="divide-y divide-sand/60">
                {day.sessions.map((session, i) => (
                  <div key={i} className="px-4 py-3 flex gap-3">
                    <span className="text-xs font-mono text-stone shrink-0 w-[120px] pt-0.5">{session.time}</span>
                    <div className="flex-1">
                      <div className="text-sm font-medium">{session.title}</div>
                      {session.note && <div className="text-xs text-stone mt-0.5">{session.note}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Speakers */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Mic2 size={18} className="text-rust" />
          <h2 className="text-lg font-semibold">Featured speakers</h2>
        </div>
        <div className="grid sm:grid-cols-2 gap-2">
          {GUARDIAN_SUMMIT.speakers.map(s => (
            <div key={s.name} className="bg-white rounded-lg border border-sand p-3">
              <div className="text-sm font-medium">{s.name}</div>
              <div className="text-xs text-stone">{s.org}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Honorees */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Award size={18} className="text-gold" />
          <h2 className="text-lg font-semibold">Guardian Award honorees</h2>
          <span className="text-xs text-stone">(10 Years Bold)</span>
        </div>
        <div className="grid sm:grid-cols-3 gap-2">
          {GUARDIAN_SUMMIT.honorees.map(h => (
            <div key={h.name} className="bg-gold/5 rounded-lg border border-gold/20 p-3 text-center">
              <div className="text-sm font-semibold">{h.name}</div>
              <div className="text-xs text-stone">{h.org}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
