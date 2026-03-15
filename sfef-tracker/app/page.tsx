'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { cn } from '@/lib/utils'
import {
  ChevronDown,
  ChevronRight,
  Calendar,
  Users,
  FileText,
  ClipboardList,
  BarChart3,
  MessageSquare,
  HelpCircle,
  Target,
  Clock,
  CheckCircle2,
  Circle,
  Loader2,
  AlertTriangle,
  StickyNote,
  Plus,
  X,
  Search,
  Building2,
  UserCheck,
} from 'lucide-react'

// ── Types ──────────────────────────────────────────────────────────────

interface ProjectTask {
  id: string
  project_id: string
  section: string
  subsection: string | null
  title: string
  description: string | null
  status: 'todo' | 'in_progress' | 'done' | 'blocked'
  owner: string | null
  due_date: string | null
  sort_order: number
  notes: string | null
  created_at: string
  updated_at: string
}

// ── Constants ──────────────────────────────────────────────────────────

const STATUS_CYCLE: ProjectTask['status'][] = ['todo', 'in_progress', 'done', 'blocked']

function isTaskOverdue(task: ProjectTask): boolean {
  if (!task.due_date || task.status === 'done') return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(task.due_date + 'T00:00:00')
  return due < today
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  todo: {
    label: 'To Do',
    color: 'text-slate-500',
    bg: 'bg-slate-100 text-slate-600',
    icon: <Circle className="w-3.5 h-3.5" />,
  },
  in_progress: {
    label: 'In Progress',
    color: 'text-blue-600',
    bg: 'bg-blue-50 text-blue-700',
    icon: <Clock className="w-3.5 h-3.5" />,
  },
  done: {
    label: 'Done',
    color: 'text-emerald-600',
    bg: 'bg-emerald-50 text-emerald-700',
    icon: <CheckCircle2 className="w-3.5 h-3.5" />,
  },
  blocked: {
    label: 'Blocked',
    color: 'text-red-600',
    bg: 'bg-red-50 text-red-700',
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
  },
}

const OWNER_OPTIONS = ['Justin', 'Laura', 'Ann', 'Terrence', 'SFEF Team'] as const

const OWNER_CONFIG: Record<string, { color: string; bg: string; initials: string; ring: string }> = {
  Justin: { color: 'text-teal-700', bg: 'bg-teal-50 border-teal-200', initials: 'JS', ring: 'ring-teal-200' },
  Laura: { color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200', initials: 'LK', ring: 'ring-amber-200' },
  Ann: { color: 'text-violet-700', bg: 'bg-violet-50 border-violet-200', initials: 'AW', ring: 'ring-violet-200' },
  Terrence: { color: 'text-rose-700', bg: 'bg-rose-50 border-rose-200', initials: 'TR', ring: 'ring-rose-200' },
  'SFEF Team': { color: 'text-slate-700', bg: 'bg-slate-50 border-slate-200', initials: 'SF', ring: 'ring-slate-200' },
}

const SECTION_ORDER = [
  'Discovery & Data',
  'Institutional Funders',
  'Individual Donors',
  'Dashboard',
  'Deliverables',
  'Advisory Phase',
  'Meetings',
  'Open Questions',
]

const SECTION_ICONS: Record<string, React.ReactNode> = {
  'Discovery & Data': <Search className="w-4 h-4" />,
  'Institutional Funders': <Building2 className="w-4 h-4" />,
  'Individual Donors': <UserCheck className="w-4 h-4" />,
  Dashboard: <BarChart3 className="w-4 h-4" />,
  Deliverables: <Target className="w-4 h-4" />,
  'Advisory Phase': <ClipboardList className="w-4 h-4" />,
  Meetings: <MessageSquare className="w-4 h-4" />,
  'Open Questions': <HelpCircle className="w-4 h-4" />,
}

const SECTION_LABELS: Record<string, string> = {
  'Discovery & Data': 'Discovery & Data Intake',
  'Institutional Funders': 'SFLC Institutional Funders',
  'Individual Donors': 'Individual Donor Intelligence',
  Dashboard: 'Interactive Dashboard',
  Deliverables: 'Final Deliverables',
  'Advisory Phase': 'Advisory Phase (Apr–May)',
  Meetings: 'Meetings & Events',
  'Open Questions': 'Open Questions',
}

const TEAM_MEMBERS = [
  { name: 'Justin Steele', role: 'True Steele', initials: 'JS', color: 'bg-teal-600' },
  { name: 'Laura King', role: 'Chief Dev & Impact', initials: 'LK', color: 'bg-amber-500' },
  { name: 'Ann Levy Walden', role: 'SFEF', initials: 'AW', color: 'bg-violet-500' },
  { name: 'Terrence Riley', role: 'SFLC', initials: 'TR', color: 'bg-rose-500' },
]

const KEY_DATES = [
  { label: 'Kickoff', date: 'Mar 10-11', past: true },
  { label: 'SXSW', date: 'Mar 12-15', past: false },
  { label: 'SFEF Event', date: 'Mar 18', past: false },
  { label: 'Draft Review', date: 'Mar 20', past: false },
  { label: 'Presentation', date: 'Mar 27', past: false },
  { label: 'Sprint End', date: 'Mar 28', past: false },
]

const SPRINT_WEEKS = [
  { week: 1, label: 'Week 1', dates: 'Mar 10–16', milestone: 'Data Intake & Enrichment' },
  { week: 2, label: 'Week 2', dates: 'Mar 17–21', milestone: 'Analysis & Scoring' },
  { week: 3, label: 'Week 3', dates: 'Mar 24–28', milestone: 'Refinement & Presentation' },
  { week: 4, label: 'Advisory', dates: 'Apr – May', milestone: 'Board Deck + Cultivation' },
]

function getCurrentWeek(): number {
  const now = new Date()
  const w1Start = new Date('2026-03-10')
  const w2Start = new Date('2026-03-17')
  const w3Start = new Date('2026-03-24')
  const w3End = new Date('2026-03-29')
  if (now < w1Start) return 0
  if (now < w2Start) return 1
  if (now < w3Start) return 2
  if (now < w3End) return 3
  return 4
}

// ── Sub-components ─────────────────────────────────────────────────────

function StatusBadge({
  status,
  onClick,
  saving,
}: {
  status: string
  onClick?: () => void
  saving?: boolean
}) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.todo
  return (
    <button
      onClick={(e) => {
        e.stopPropagation()
        onClick?.()
      }}
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-all',
        config.bg,
        onClick && 'cursor-pointer hover:ring-2 hover:ring-offset-1 hover:ring-slate-300 active:scale-95'
      )}
    >
      {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : config.icon}
      {config.label}
    </button>
  )
}

function OwnerPill({
  owner,
  onSelect,
  saving,
}: {
  owner: string | null
  onSelect?: (owner: string | null) => void
  saving?: boolean
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const config = owner
    ? OWNER_CONFIG[owner] || { color: 'text-slate-600', bg: 'bg-slate-50 border-slate-200', initials: owner.slice(0, 2).toUpperCase() }
    : null

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={(e) => {
          e.stopPropagation()
          if (onSelect) setOpen(!open)
        }}
        className={cn(
          'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border transition-all',
          config ? [config.bg, config.color] : 'bg-slate-50 border-dashed border-slate-300 text-slate-400',
          onSelect && 'cursor-pointer hover:ring-2 hover:ring-offset-1 hover:ring-slate-300 active:scale-95'
        )}
      >
        {saving ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : null}
        {owner || 'Assign'}
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 z-50 bg-white border border-border/60 rounded-lg shadow-lg py-1 min-w-[140px]">
          {OWNER_OPTIONS.map((o) => {
            const oc = OWNER_CONFIG[o]
            return (
              <button
                key={o}
                onClick={(e) => {
                  e.stopPropagation()
                  onSelect?.(o)
                  setOpen(false)
                }}
                className={cn(
                  'w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 hover:bg-slate-50 transition-colors',
                  owner === o && 'font-semibold bg-slate-50'
                )}
              >
                <span className={cn('w-5 h-5 rounded-full flex items-center justify-center text-white text-[9px] font-bold',
                  o === 'Justin' ? 'bg-teal-600' :
                  o === 'Laura' ? 'bg-amber-500' :
                  o === 'Ann' ? 'bg-violet-500' :
                  o === 'Terrence' ? 'bg-rose-500' : 'bg-slate-500'
                )}>
                  {oc.initials}
                </span>
                {o}
              </button>
            )
          })}
          {owner && (
            <>
              <div className="border-t border-border/40 my-1" />
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onSelect?.(null)
                  setOpen(false)
                }}
                className="w-full text-left px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-50 transition-colors"
              >
                Unassign
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

function OwnerAvatar({ name, initials, color }: { name: string; initials: string; color: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={cn('w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-semibold shadow-sm', color)}>
        {initials}
      </div>
      <span className="text-[10px] text-muted-foreground leading-tight text-center max-w-[60px] truncate">
        {name.split(' ')[0]}
      </span>
    </div>
  )
}

function ProgressBar({ done, total }: { done: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round((done / total) * 100)
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-teal-500 to-emerald-400 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-sm font-medium text-muted-foreground tabular-nums min-w-[3.5rem] text-right">
        {done}/{total}
      </span>
    </div>
  )
}

function TaskRow({
  task,
  onUpdate,
  saving,
  notesOpen,
  onToggleNotes,
}: {
  task: ProjectTask
  onUpdate: (id: string, updates: Partial<ProjectTask>) => void
  saving: boolean
  notesOpen: boolean
  onToggleNotes: (id: string) => void
}) {
  const [notesValue, setNotesValue] = useState(task.notes || '')
  const [detailOpen, setDetailOpen] = useState(false)
  const notesRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    setNotesValue(task.notes || '')
  }, [task.notes])

  useEffect(() => {
    if (notesOpen && notesRef.current) {
      notesRef.current.focus()
    }
  }, [notesOpen])

  function toggleCheckbox() {
    const newStatus = task.status === 'done' ? 'todo' : 'done'
    onUpdate(task.id, { status: newStatus })
  }

  function cycleStatus() {
    const idx = STATUS_CYCLE.indexOf(task.status)
    const next = STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length]
    onUpdate(task.id, { status: next })
  }

  function changeOwner(owner: string | null) {
    onUpdate(task.id, { owner })
  }

  function saveNotes() {
    if (notesValue !== (task.notes || '')) {
      onUpdate(task.id, { notes: notesValue || null })
    }
  }

  const overdue = isTaskOverdue(task)

  return (
    <div>
      <div className={cn('group flex items-start gap-3 py-2.5 px-3 rounded-lg transition-colors', overdue ? 'bg-red-50/60 hover:bg-red-50/80' : 'hover:bg-slate-50/60')}>
        <button
          onClick={toggleCheckbox}
          className={cn('mt-0.5 flex-shrink-0 transition-colors', STATUS_CONFIG[task.status]?.color || 'text-slate-400',
            'hover:text-teal-600 active:scale-90'
          )}
        >
          {saving ? (
            <Loader2 className="w-[18px] h-[18px] animate-spin" />
          ) : task.status === 'done' ? (
            <CheckCircle2 className="w-[18px] h-[18px]" />
          ) : task.status === 'blocked' ? (
            <AlertTriangle className="w-[18px] h-[18px]" />
          ) : task.status === 'in_progress' ? (
            <Clock className="w-[18px] h-[18px]" />
          ) : (
            <Circle className="w-[18px] h-[18px]" />
          )}
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn('text-sm', task.status === 'done' && 'line-through text-muted-foreground')}>
              {task.title}
            </span>
            {task.description && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setDetailOpen(!detailOpen)
                }}
                className={cn(
                  'inline-flex items-center gap-0.5 text-[11px] font-medium transition-colors',
                  detailOpen
                    ? 'text-teal-600'
                    : 'text-muted-foreground/50 hover:text-muted-foreground/80'
                )}
                title="Show details"
              >
                {detailOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                <span>details</span>
              </button>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onToggleNotes(task.id)
            }}
            className={cn(
              'p-1 rounded transition-all',
              notesOpen || task.notes
                ? 'text-teal-600 bg-teal-50 hover:bg-teal-100'
                : 'text-slate-300 hover:text-slate-500 opacity-0 group-hover:opacity-100'
            )}
            title={task.notes ? 'View notes' : 'Add notes'}
          >
            <StickyNote className="w-3.5 h-3.5" />
          </button>
          {task.due_date && (
            <span className={cn('text-[11px] tabular-nums flex items-center gap-1', overdue ? 'text-red-600 font-semibold' : 'text-muted-foreground')}>
              {new Date(task.due_date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              {overdue && (
                <span className="text-[9px] font-bold uppercase tracking-wider text-red-500 bg-red-100 px-1 py-0.5 rounded">
                  Overdue
                </span>
              )}
            </span>
          )}
          <OwnerPill owner={task.owner} onSelect={changeOwner} saving={saving} />
          <StatusBadge status={task.status} onClick={cycleStatus} saving={saving} />
        </div>
      </div>
      {detailOpen && task.description && (
        <div className="ml-9 mr-3 mb-2 mt-0.5">
          <div className="text-xs text-muted-foreground/80 bg-slate-50/80 border border-border/30 rounded-lg px-3 py-2.5 leading-relaxed whitespace-pre-line">
            {task.description}
          </div>
        </div>
      )}
      {notesOpen && (
        <div className="ml-9 mr-3 mb-2 mt-0.5">
          <textarea
            ref={notesRef}
            value={notesValue}
            onChange={(e) => setNotesValue(e.target.value)}
            onBlur={saveNotes}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                setNotesValue(task.notes || '')
                onToggleNotes(task.id)
              }
            }}
            placeholder="Add a note..."
            className="w-full text-xs text-muted-foreground bg-slate-50 border border-border/40 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-300 placeholder:text-slate-300 transition-all"
            rows={2}
          />
        </div>
      )}
    </div>
  )
}

function AddTaskForm({
  section,
  subsection,
  onAdd,
  onCancel,
}: {
  section: string
  subsection?: string | null
  onAdd: (task: { section: string; subsection?: string | null; title: string }) => void
  onCancel: () => void
}) {
  const [title, setTitle] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  function handleSubmit() {
    const trimmed = title.trim()
    if (!trimmed) return
    onAdd({ section, subsection, title: trimmed })
    setTitle('')
    inputRef.current?.focus()
  }

  return (
    <div className="flex items-center gap-2 py-2 px-3">
      <Plus className="w-[18px] h-[18px] text-slate-300 flex-shrink-0" />
      <input
        ref={inputRef}
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') handleSubmit()
          if (e.key === 'Escape') onCancel()
        }}
        placeholder="Task title..."
        className="flex-1 text-sm bg-transparent border-none outline-none placeholder:text-slate-300"
      />
      <button
        onClick={handleSubmit}
        disabled={!title.trim()}
        className="text-xs font-medium text-teal-700 bg-teal-50 px-2.5 py-1 rounded-md hover:bg-teal-100 disabled:opacity-40 disabled:cursor-default transition-colors"
      >
        Add
      </button>
      <button
        onClick={onCancel}
        className="text-xs text-slate-400 hover:text-slate-600 p-1 transition-colors"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

function CollapsibleSection({
  title,
  icon,
  tasks,
  defaultOpen = true,
  children,
}: {
  title: string
  icon: React.ReactNode
  tasks: ProjectTask[]
  defaultOpen?: boolean
  children?: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  const doneCount = tasks.filter((t) => t.status === 'done').length
  const overdueCount = tasks.filter(isTaskOverdue).length

  return (
    <div className={cn('border rounded-xl bg-white shadow-sm overflow-hidden', overdueCount > 0 ? 'border-red-200' : 'border-border/60')}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-50/50 transition-colors"
      >
        <span className="text-muted-foreground">
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </span>
        <span className="text-muted-foreground/70">{icon}</span>
        <span className="text-sm font-semibold text-foreground flex-1">{title}</span>
        {overdueCount > 0 && (
          <span className="text-[10px] font-bold text-red-600 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded-full">
            {overdueCount} overdue
          </span>
        )}
        <span className="text-xs text-muted-foreground tabular-nums">
          {doneCount}/{tasks.length}
        </span>
        <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-400 rounded-full transition-all duration-300"
            style={{ width: tasks.length > 0 ? `${(doneCount / tasks.length) * 100}%` : '0%' }}
          />
        </div>
      </button>
      {open && (
        <div className="px-5 pb-4 border-t border-border/40">
          {children}
        </div>
      )}
    </div>
  )
}

function SubsectionGroup({
  label,
  tasks,
  onUpdate,
  savingTasks,
  notesOpenId,
  onToggleNotes,
}: {
  label: string
  tasks: ProjectTask[]
  onUpdate: (id: string, updates: Partial<ProjectTask>) => void
  savingTasks: Set<string>
  notesOpenId: string | null
  onToggleNotes: (id: string) => void
}) {
  const doneCount = tasks.filter((t) => t.status === 'done').length
  return (
    <div className="mt-3">
      <div className="flex items-center gap-2 px-3 py-1.5">
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{label}</h4>
        <span className="text-[10px] text-muted-foreground/60 tabular-nums">
          {doneCount}/{tasks.length}
        </span>
      </div>
      {tasks.map((task) => (
        <TaskRow
          key={task.id}
          task={task}
          onUpdate={onUpdate}
          saving={savingTasks.has(task.id)}
          notesOpen={notesOpenId === task.id}
          onToggleNotes={onToggleNotes}
        />
      ))}
    </div>
  )
}

// ── Main Page Component ────────────────────────────────────────────────

export default function SFEFTracker() {
  const [tasks, setTasks] = useState<ProjectTask[]>([])
  const [grouped, setGrouped] = useState<Record<string, ProjectTask[]>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [savingTasks, setSavingTasks] = useState<Set<string>>(new Set())
  const [notesOpenId, setNotesOpenId] = useState<string | null>(null)
  const [addingSection, setAddingSection] = useState<string | null>(null)

  const fetchTasks = useCallback(async () => {
    try {
      const res = await fetch('/api/tasks')
      if (!res.ok) throw new Error('Failed to fetch tasks')
      const data = await res.json()
      setTasks(data.tasks || [])
      setGrouped(data.grouped || {})
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  function regroup(taskList: ProjectTask[]): Record<string, ProjectTask[]> {
    const g: Record<string, ProjectTask[]> = {}
    for (const task of taskList) {
      const section = task.section || 'Uncategorized'
      if (!g[section]) g[section] = []
      g[section].push(task)
    }
    return g
  }

  const updateTask = useCallback(async (id: string, updates: Partial<ProjectTask>) => {
    let prevTasks: ProjectTask[] = []
    let prevGrouped: Record<string, ProjectTask[]> = {}
    setTasks((current) => {
      prevTasks = current
      const updated = current.map((t) => (t.id === id ? { ...t, ...updates } : t))
      return updated
    })
    setGrouped((current) => {
      prevGrouped = current
      return regroup(prevTasks.map((t) => (t.id === id ? { ...t, ...updates } : t)))
    })
    setSavingTasks((prev) => new Set(prev).add(id))

    try {
      const res = await fetch('/api/tasks', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, ...updates }),
      })
      if (!res.ok) throw new Error('Failed to update')
      const data = await res.json()
      const serverTask = data.task
      setTasks((current) => {
        const finalTasks = current.map((t) => (t.id === id ? { ...t, ...serverTask } : t))
        setGrouped(regroup(finalTasks))
        return finalTasks
      })
    } catch {
      setTasks(prevTasks)
      setGrouped(prevGrouped)
    } finally {
      setSavingTasks((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }, [])

  const createTask = useCallback(async (section: string, subsection: string | null, title: string) => {
    try {
      let maxSort = 0
      setTasks((current) => {
        const sectionTasks = current.filter((t) => t.section === section)
        maxSort = sectionTasks.reduce((max, t) => Math.max(max, t.sort_order), 0)
        return current
      })

      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section,
          subsection,
          title,
          sort_order: maxSort + 10,
        }),
      })
      if (!res.ok) throw new Error('Failed to create task')
      const data = await res.json()
      const newTask = data.task as ProjectTask
      setTasks((current) => {
        const updatedTasks = [...current, newTask]
        setGrouped(regroup(updatedTasks))
        return updatedTasks
      })
    } catch {
      setError('Failed to add task. Please try again.')
      setTimeout(() => setError(null), 3000)
    }
  }, [])

  function toggleNotes(id: string) {
    setNotesOpenId((prev) => (prev === id ? null : id))
  }

  const totalTasks = tasks.length
  const doneTasks = tasks.filter((t) => t.status === 'done').length
  const currentWeek = getCurrentWeek()

  function getSubsections(section: string): Record<string, ProjectTask[]> {
    const sectionTasks = grouped[section] || []
    const subs: Record<string, ProjectTask[]> = {}
    for (const task of sectionTasks) {
      const key = task.subsection || '_default'
      if (!subs[key]) subs[key] = []
      subs[key].push(task)
    }
    return subs
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error && tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-3">
        <AlertTriangle className="w-6 h-6 text-red-500" />
        <p className="text-sm text-muted-foreground">{error}</p>
        <button
          onClick={() => { setError(null); setLoading(true); fetchTasks() }}
          className="text-xs font-medium text-teal-700 bg-teal-50 px-3 py-1.5 rounded-md hover:bg-teal-100 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-8 pb-16">
      {error && tasks.length > 0 && (
        <div className="fixed top-4 right-4 z-50 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2 rounded-lg shadow-md animate-in fade-in slide-in-from-top-2">
          {error}
        </div>
      )}

      {/* ── Header ────────────────────────────────────────────────── */}
      <header className="space-y-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground" style={{ fontFamily: 'var(--font-dm-serif)' }}>
              SFEF × True Steele
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              Fundraising Intelligence Sprint · SF Education Fund
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              Active Sprint
            </span>
          </div>
        </div>

        {/* Overall progress */}
        <div className="bg-white border border-border/60 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Overall Progress</span>
            <span className="text-lg font-bold text-foreground tabular-nums">
              {totalTasks > 0 ? Math.round((doneTasks / totalTasks) * 100) : 0}%
            </span>
          </div>
          <ProgressBar done={doneTasks} total={totalTasks} />
        </div>

        {/* Team + Key dates row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white border border-border/60 rounded-xl p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Users className="w-3.5 h-3.5 text-muted-foreground/70" />
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Team</span>
            </div>
            <div className="flex items-center gap-5">
              {TEAM_MEMBERS.map((member) => (
                <OwnerAvatar key={member.initials} {...member} />
              ))}
            </div>
          </div>

          <div className="bg-white border border-border/60 rounded-xl p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-3.5 h-3.5 text-muted-foreground/70" />
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Key Dates</span>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {KEY_DATES.map((d) => (
                <div
                  key={d.label}
                  className={cn(
                    'flex flex-col items-center px-2.5 py-1.5 rounded-lg border text-center min-w-[64px]',
                    d.past
                      ? 'bg-slate-50 border-slate-200 opacity-60'
                      : 'bg-white border-border/60'
                  )}
                >
                  <span className="text-[10px] font-medium text-muted-foreground uppercase">{d.label}</span>
                  <span className="text-xs font-semibold text-foreground">{d.date}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* ── Sprint Timeline ───────────────────────────────────────── */}
      <div className="bg-white border border-border/60 rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-3.5 h-3.5 text-muted-foreground/70" />
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Sprint Timeline</span>
        </div>
        <div className="grid grid-cols-4 gap-2">
          {SPRINT_WEEKS.map((w) => {
            const isCurrent = w.week === currentWeek
            const isPast = w.week < currentWeek
            return (
              <div
                key={w.week}
                className={cn(
                  'relative rounded-lg border p-3 transition-all',
                  isCurrent && 'border-teal-300 bg-teal-50/50 shadow-sm ring-1 ring-teal-200',
                  isPast && 'border-slate-200 bg-slate-50/50 opacity-60',
                  !isCurrent && !isPast && 'border-border/60 bg-white'
                )}
              >
                {isCurrent && (
                  <span className="absolute -top-2 left-3 px-1.5 py-0 text-[9px] font-bold uppercase tracking-widest text-teal-700 bg-teal-50 border border-teal-200 rounded">
                    Now
                  </span>
                )}
                <div className="text-xs font-semibold text-foreground">{w.label}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">{w.dates}</div>
                <div className="text-[10px] text-muted-foreground/80 mt-1 font-medium">{w.milestone}</div>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Sections ──────────────────────────────────────────────── */}
      {SECTION_ORDER.map((sectionKey) => {
        const sectionTasks = grouped[sectionKey] || []
        const subs = getSubsections(sectionKey)
        const subsKeys = Object.keys(subs).sort((a, b) => {
          if (a === '_default') return -1
          if (b === '_default') return 1
          const aMin = Math.min(...(subs[a]?.map((t) => t.sort_order) || [0]))
          const bMin = Math.min(...(subs[b]?.map((t) => t.sort_order) || [0]))
          return aMin - bMin
        })
        const hasSubsections = subsKeys.length > 1 || (subsKeys.length === 1 && subsKeys[0] !== '_default')

        return (
          <CollapsibleSection
            key={sectionKey}
            title={SECTION_LABELS[sectionKey] || sectionKey}
            icon={SECTION_ICONS[sectionKey] || <FileText className="w-4 h-4" />}
            tasks={sectionTasks}
          >
            <div className="mt-1">
              {sectionTasks.length === 0 && addingSection !== sectionKey ? (
                <p className="text-sm text-muted-foreground/60 py-4 text-center italic">
                  No tasks yet
                </p>
              ) : hasSubsections ? (
                subsKeys.map((subKey) => (
                  <SubsectionGroup
                    key={subKey}
                    label={subKey === '_default' ? 'General' : subKey}
                    tasks={subs[subKey]}
                    onUpdate={updateTask}
                    savingTasks={savingTasks}
                    notesOpenId={notesOpenId}
                    onToggleNotes={toggleNotes}
                  />
                ))
              ) : (
                sectionTasks.map((task) => (
                  <TaskRow
                    key={task.id}
                    task={task}
                    onUpdate={updateTask}
                    saving={savingTasks.has(task.id)}
                    notesOpen={notesOpenId === task.id}
                    onToggleNotes={toggleNotes}
                  />
                ))
              )}
            </div>
            {addingSection === sectionKey ? (
              <AddTaskForm
                section={sectionKey}
                onAdd={(t) => {
                  createTask(t.section, t.subsection ?? null, t.title)
                  setAddingSection(null)
                }}
                onCancel={() => setAddingSection(null)}
              />
            ) : (
              <button
                onClick={() => setAddingSection(sectionKey)}
                className="flex items-center gap-2 mt-2 px-3 py-1.5 text-xs text-slate-400 hover:text-teal-600 hover:bg-teal-50/50 rounded-md transition-colors w-full"
              >
                <Plus className="w-3.5 h-3.5" />
                Add task
              </button>
            )}
          </CollapsibleSection>
        )
      })}

      {/* Show any sections in data that aren't in SECTION_ORDER */}
      {Object.keys(grouped)
        .filter((s) => !SECTION_ORDER.includes(s))
        .map((sectionKey) => {
          const sectionTasks = grouped[sectionKey] || []
          return (
            <CollapsibleSection
              key={sectionKey}
              title={sectionKey}
              icon={<FileText className="w-4 h-4" />}
              tasks={sectionTasks}
            >
              <div className="mt-1">
                {sectionTasks.length === 0 ? (
                  <p className="text-sm text-muted-foreground/60 py-4 text-center italic">
                    No tasks yet
                  </p>
                ) : (
                  sectionTasks.map((task) => (
                    <TaskRow
                      key={task.id}
                      task={task}
                      onUpdate={updateTask}
                      saving={savingTasks.has(task.id)}
                      notesOpen={notesOpenId === task.id}
                      onToggleNotes={toggleNotes}
                    />
                  ))
                )}
              </div>
              {addingSection === sectionKey ? (
                <AddTaskForm
                  section={sectionKey}
                  onAdd={(t) => {
                    createTask(t.section, t.subsection ?? null, t.title)
                    setAddingSection(null)
                  }}
                  onCancel={() => setAddingSection(null)}
                />
              ) : (
                <button
                  onClick={() => setAddingSection(sectionKey)}
                  className="flex items-center gap-2 mt-2 px-3 py-1.5 text-xs text-slate-400 hover:text-teal-600 hover:bg-teal-50/50 rounded-md transition-colors w-full"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add task
                </button>
              )}
            </CollapsibleSection>
          )
        })}
    </div>
  )
}
