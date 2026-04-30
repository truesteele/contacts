import { BUDGET, CANCEL_DEADLINES, bookedCash, totalBudgetCash, totalBudgetPoints } from '@/data/trip'
import { StatusBadge } from '@/components/status-badge'
import { AlertTriangle } from 'lucide-react'

export default function BudgetPage() {
  const booked = BUDGET.filter(b => b.status === 'booked')
  const notBooked = BUDGET.filter(b => b.status !== 'booked')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-medium" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>Trip budget</h1>
        <p className="text-stone text-sm">All-in cash + Bonvoy points (flights, hotels, trains, cars, shows). Excludes meals + Ubers.</p>
      </div>

      {/* Grand total card */}
      <div className="bg-navy rounded-lg p-6 text-white">
        <div className="text-[0.7rem] uppercase tracking-wider opacity-60 mb-1">Total all-in (everything booked + estimated)</div>
        <div className="flex items-baseline gap-4 flex-wrap">
          <span className="text-3xl font-medium" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
            ~${totalBudgetCash().toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </span>
          <span className="text-sm opacity-70">+ {totalBudgetPoints().toLocaleString()} Bonvoy pts</span>
        </div>
        <div className="border-t border-white/20 mt-4 pt-3 text-xs opacity-70 space-y-1">
          <div>Booked so far: <strong>${bookedCash().toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</strong> + 240,000 pts</div>
          <div>Points balance remaining: ~64,054 pts</div>
          <div>NOLA hotel covered by Camelback (Four Seasons) + $1,000 travel stipend</div>
        </div>
      </div>

      {/* Booked items */}
      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-olive mb-2">Booked</h2>
        <div className="bg-white rounded-lg border border-sand divide-y divide-sand/60">
          {booked.map((b, i) => (
            <div key={i} className="flex items-center justify-between p-3">
              <div>
                <span className="text-xs text-stone mr-2">{b.category}</span>
                <span className="text-sm">{b.item}</span>
              </div>
              <div className="text-right shrink-0 ml-4">
                {typeof b.cash === 'number' && <span className="text-sm font-medium">${b.cash.toLocaleString()}</span>}
                {b.points ? <span className="text-xs text-stone ml-2">+ {b.points.toLocaleString()} pts</span> : null}
              </div>
            </div>
          ))}
          <div className="flex items-center justify-between p-3 bg-olive/5">
            <span className="text-sm font-semibold">Booked subtotal</span>
            <div className="text-right">
              <span className="text-sm font-semibold text-olive">${bookedCash().toLocaleString()}</span>
              <span className="text-xs text-stone ml-2">+ 240,000 pts</span>
            </div>
          </div>
        </div>
      </section>

      {/* Not yet booked */}
      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gold mb-2">Still to book (estimated)</h2>
        <div className="bg-white rounded-lg border border-sand divide-y divide-sand/60">
          {notBooked.map((b, i) => (
            <div key={i} className="flex items-center justify-between p-3">
              <div>
                <span className="text-xs text-stone mr-2">{b.category}</span>
                <span className="text-sm">{b.item}</span>
              </div>
              <div className="text-right shrink-0 ml-4">
                {typeof b.cash === 'number' && <span className="text-sm text-stone">~${b.cash.toLocaleString()}</span>}
              </div>
            </div>
          ))}
          <div className="flex items-center justify-between p-3 bg-gold/5">
            <span className="text-sm font-semibold">Estimated remaining</span>
            <span className="text-sm font-semibold text-gold">
              ~${notBooked.reduce((s, b) => s + (typeof b.cash === 'number' ? b.cash : 0), 0).toLocaleString()}
            </span>
          </div>
        </div>
      </section>

      {/* Cancellation deadlines */}
      <section>
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle size={15} className="text-rust" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-rust">Cancellation deadlines</h2>
        </div>
        <div className="bg-white rounded-lg border border-sand divide-y divide-sand/60">
          {CANCEL_DEADLINES.map(d => (
            <div key={d.what} className="flex items-start gap-3 p-3">
              <span className={`font-mono text-xs font-semibold shrink-0 w-14 pt-0.5 ${d.urgent ? 'text-rust' : 'text-stone'}`}>
                {d.date}
              </span>
              <div className="flex-1 text-sm">
                <div>{d.what}</div>
                <div className="text-xs text-stone">{d.penalty}</div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
