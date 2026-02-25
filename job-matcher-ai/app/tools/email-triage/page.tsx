'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Inbox,
  RefreshCw,
  Sparkles,
  Send,
  Save,
  Check,
  X,
  Loader2,
  Clock,
  AlertCircle,
  Filter,
  EyeOff,
  Zap,
  ChevronDown,
  ChevronRight,
  User,
  UserCheck,
  Building2,
  MapPin,
  GraduationCap,
  Briefcase,
  Users,
  ExternalLink,
  MessageSquare,
} from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────

type EmailCategory = 'action' | 'fyi' | 'skip' | 'unclassified';
type FilterTab = 'action' | 'fyi' | 'skip' | 'all';

interface EmailMessage {
  id: string;
  threadId: string;
  account: string;
  from: string;
  fromName: string;
  to: string;
  subject: string;
  snippet: string;
  date: string;
  timestamp: number;
  labels: string[];
  category: EmailCategory;
  categoryReason: string;
}

interface EmailThread {
  threadId: string;
  subject: string;
  account: string;
  lastMessage: EmailMessage;
  messageCount: number;
  messages: EmailMessage[];
  category: EmailCategory;
  categoryReason: string;
  timestamp: number;
}

interface ThreadMessage {
  id: string;
  threadId: string;
  from: string;
  fromName: string;
  fromEmail: string;
  to: string;
  cc: string;
  subject: string;
  date: string;
  timestamp: number;
  body: string;
}

interface ContactSummary {
  id: number;
  first_name: string;
  last_name: string;
  company: string | null;
  position: string | null;
  headline: string | null;
  city: string | null;
  state: string | null;
  linkedin_url: string | null;
  familiarity_rating: number | null;
  comms_closeness: string | null;
  comms_momentum: string | null;
  comms_last_date: string | null;
  comms_thread_count: number | null;
  comms_relationship_summary: string | null;
  ai_proximity_tier: string | null;
  ai_capacity_tier: string | null;
  ai_outdoorithm_fit: string | null;
  ask_readiness_tier: string | null;
  ask_readiness_score: number | null;
  ask_readiness_reasoning: string | null;
  ask_readiness_personalization: string | null;
  shared_institutions: Array<{
    name: string;
    type: string;
    overlap: string;
    temporal_overlap?: boolean;
    justin_period?: string;
    contact_period?: string;
  }>;
  personalization_hooks: string[];
  suggested_opener: string;
  talking_points: string[];
  topics: string[];
  primary_interests: string[];
  best_approach: string;
}

type ThreadStatus = 'pending' | 'loading' | 'loaded' | 'drafting' | 'draft_ready' | 'sending' | 'sent' | 'saved' | 'done';

interface ThreadState {
  status: ThreadStatus;
  messages: ThreadMessage[];
  draftBody: string;
  draftSubject: string;
  fetchError?: string;
}

// ── Constants ─────────────────────────────────────────────────────────

const ACCOUNT_STYLES: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  'justinrsteele@gmail.com': { label: 'Gmail', bg: 'bg-red-100', text: 'text-red-700', dot: 'bg-red-500' },
  'justin@truesteele.com': { label: 'TrueSteele', bg: 'bg-blue-100', text: 'text-blue-700', dot: 'bg-blue-500' },
  'justin@outdoorithm.com': { label: 'Outdoorithm', bg: 'bg-green-100', text: 'text-green-700', dot: 'bg-green-500' },
  'justin@outdoorithmcollective.org': { label: 'OC', bg: 'bg-orange-100', text: 'text-orange-700', dot: 'bg-orange-500' },
  'justin@kindora.co': { label: 'Kindora', bg: 'bg-purple-100', text: 'text-purple-700', dot: 'bg-purple-500' },
};

const CATEGORY_STYLES: Record<EmailCategory, { label: string; bg: string; text: string }> = {
  action: { label: 'Action', bg: 'bg-red-50', text: 'text-red-700' },
  fyi: { label: 'FYI', bg: 'bg-sky-50', text: 'text-sky-700' },
  skip: { label: 'Skip', bg: 'bg-gray-100', text: 'text-gray-500' },
  unclassified: { label: '...', bg: 'bg-yellow-50', text: 'text-yellow-700' },
};

const CLOSENESS_LABELS: Record<string, string> = {
  active_inner_circle: 'Inner Circle',
  regular_contact: 'Regular',
  occasional: 'Occasional',
  dormant: 'Dormant',
  one_way: 'One-Way',
  no_history: 'No History',
};

const CLOSENESS_COLORS: Record<string, string> = {
  active_inner_circle: 'bg-green-100 text-green-800',
  regular_contact: 'bg-blue-100 text-blue-800',
  occasional: 'bg-yellow-100 text-yellow-800',
  dormant: 'bg-orange-100 text-orange-800',
  one_way: 'bg-purple-100 text-purple-800',
  no_history: 'bg-gray-100 text-gray-600',
};

const MOMENTUM_ICONS: Record<string, string> = {
  growing: '\u2197',
  stable: '\u2014',
  fading: '\u2198',
  inactive: '\u00D7',
};

const ASK_READINESS_COLORS: Record<string, string> = {
  ready_now: 'bg-green-100 text-green-800',
  cultivate_first: 'bg-yellow-100 text-yellow-800',
  long_term: 'bg-gray-100 text-gray-600',
  not_a_fit: 'bg-red-100 text-red-700',
};

const OVERLAP_ICONS: Record<string, typeof Briefcase> = {
  employer: Briefcase,
  school: GraduationCap,
  board: Users,
  volunteer: Users,
};

// ── Helpers ───────────────────────────────────────────────────────────

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return d.toLocaleDateString('en-US', { weekday: 'short' });
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

function formatFullDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return (name[0] || '?').toUpperCase();
}

function hashColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
  const colors = [
    'bg-red-500', 'bg-blue-500', 'bg-green-500', 'bg-purple-500',
    'bg-orange-500', 'bg-teal-500', 'bg-pink-500', 'bg-indigo-500',
    'bg-cyan-500', 'bg-amber-500',
  ];
  return colors[Math.abs(hash) % colors.length];
}

function parseFromEmail(from: string): string {
  const match = from.match(/<([^>]+)>/);
  return match ? match[1] : from;
}

// ── Avatar Component ──────────────────────────────────────────────────

function SenderAvatar({ name, size = 'md' }: { name: string; size?: 'sm' | 'md' | 'lg' }) {
  const sizeClass = size === 'sm' ? 'w-8 h-8 text-xs' : size === 'lg' ? 'w-12 h-12 text-base' : 'w-10 h-10 text-sm';
  return (
    <div className={`${sizeClass} ${hashColor(name)} rounded-full flex items-center justify-center text-white font-medium flex-none`}>
      {getInitials(name)}
    </div>
  );
}

// ── Familiarity Dots ──────────────────────────────────────────────────

function FamiliarityDots({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className={`w-2 h-2 rounded-full ${i <= rating ? 'bg-blue-500' : 'bg-gray-200'}`}
        />
      ))}
    </div>
  );
}

// ── Contact Sidebar ───────────────────────────────────────────────────

function ContactSidebar({ contact, senderEmail }: { contact: ContactSummary | null; senderEmail: string }) {
  if (!contact) {
    return (
      <div className="p-4 text-center text-sm text-muted-foreground">
        <User className="h-8 w-8 mx-auto mb-2 opacity-30" />
        <p className="font-medium">{senderEmail}</p>
        <p className="text-xs mt-1">Not in contacts database</p>
      </div>
    );
  }

  const location = [contact.city, contact.state].filter(Boolean).join(', ');

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <SenderAvatar name={`${contact.first_name} ${contact.last_name}`} size="lg" />
        <div className="min-w-0">
          <h3 className="font-semibold text-sm truncate">
            {contact.first_name} {contact.last_name}
          </h3>
          {contact.position && (
            <p className="text-xs text-muted-foreground truncate">{contact.position}</p>
          )}
          {contact.company && (
            <p className="text-xs text-muted-foreground truncate flex items-center gap-1">
              <Building2 className="h-3 w-3 flex-none" />
              {contact.company}
            </p>
          )}
          {location && (
            <p className="text-xs text-muted-foreground truncate flex items-center gap-1">
              <MapPin className="h-3 w-3 flex-none" />
              {location}
            </p>
          )}
        </div>
      </div>

      {/* Relationship Signals */}
      <div className="space-y-2">
        <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Relationship</h4>
        <div className="flex flex-wrap gap-1.5">
          {contact.familiarity_rating != null && contact.familiarity_rating > 0 && (
            <div className="flex items-center gap-1">
              <FamiliarityDots rating={contact.familiarity_rating} />
              <span className="text-[10px] text-muted-foreground">{contact.familiarity_rating}/4</span>
            </div>
          )}
          {contact.comms_closeness && (
            <Badge variant="secondary" className={`text-[10px] px-1.5 py-0 border-0 ${CLOSENESS_COLORS[contact.comms_closeness] || 'bg-gray-100 text-gray-600'}`}>
              {CLOSENESS_LABELS[contact.comms_closeness] || contact.comms_closeness}
            </Badge>
          )}
          {contact.comms_momentum && (
            <span className="text-[10px] text-muted-foreground">
              {MOMENTUM_ICONS[contact.comms_momentum] || ''} {contact.comms_momentum}
            </span>
          )}
        </div>
        {contact.comms_last_date && (
          <p className="text-[10px] text-muted-foreground">
            Last contact: {contact.comms_last_date}
            {contact.comms_thread_count ? ` (${contact.comms_thread_count} threads)` : ''}
          </p>
        )}
        {contact.comms_relationship_summary && (
          <p className="text-xs text-muted-foreground leading-snug">
            {contact.comms_relationship_summary}
          </p>
        )}
      </div>

      {/* Shared Institutions */}
      {contact.shared_institutions.length > 0 && (
        <div className="space-y-1.5">
          <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Shared History</h4>
          {contact.shared_institutions.slice(0, 5).map((inst, i) => {
            const Icon = OVERLAP_ICONS[inst.type] || Users;
            return (
              <div key={i} className="flex items-start gap-2 text-xs">
                <Icon className="h-3.5 w-3.5 mt-0.5 text-muted-foreground flex-none" />
                <div>
                  <span className="font-medium">{inst.name}</span>
                  {inst.temporal_overlap && (
                    <span className="text-green-600 ml-1 text-[10px]">overlapping</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Ask Readiness */}
      {contact.ask_readiness_tier && (
        <div className="space-y-1">
          <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Ask Readiness</h4>
          <Badge variant="secondary" className={`text-[10px] px-1.5 py-0 border-0 ${ASK_READINESS_COLORS[contact.ask_readiness_tier] || 'bg-gray-100 text-gray-600'}`}>
            {contact.ask_readiness_tier.replace(/_/g, ' ')}
            {contact.ask_readiness_score != null && ` (${contact.ask_readiness_score})`}
          </Badge>
          {contact.ask_readiness_personalization && (
            <p className="text-[10px] text-muted-foreground leading-snug">
              {contact.ask_readiness_personalization}
            </p>
          )}
        </div>
      )}

      {/* Topics */}
      {contact.topics.length > 0 && (
        <div className="space-y-1">
          <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Topics</h4>
          <div className="flex flex-wrap gap-1">
            {contact.topics.slice(0, 6).map((t, i) => (
              <Badge key={i} variant="secondary" className="text-[10px] px-1.5 py-0 border-0 bg-gray-100 text-gray-600">
                {t}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* LinkedIn link */}
      {contact.linkedin_url && (
        <a
          href={contact.linkedin_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
        >
          <ExternalLink className="h-3 w-3" />
          LinkedIn Profile
        </a>
      )}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────

export default function EmailTriagePage() {
  const [threads, setThreads] = useState<EmailThread[]>([]);
  const [flatMessages, setFlatMessages] = useState<EmailMessage[]>([]);
  const [threadStates, setThreadStates] = useState<Record<string, ThreadState>>({});
  const [contactMap, setContactMap] = useState<Record<string, ContactSummary>>({});
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [classifying, setClassifying] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [classifyError, setClassifyError] = useState<string | null>(null);
  const [scanWarnings, setScanWarnings] = useState<string[]>([]);
  const [accountsScanned, setAccountsScanned] = useState(0);
  const [confirmSend, setConfirmSend] = useState(false);
  const [activeTab, setActiveTab] = useState<FilterTab>('action');
  const [showContactPanel, setShowContactPanel] = useState(true);
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());
  const classifyTriggered = useRef(false);

  const selectedThread = threads.find((t) => t.threadId === selectedThreadId);
  const selectedState = selectedThreadId ? threadStates[selectedThreadId] : undefined;
  const senderEmail = selectedThread ? selectedThread.lastMessage.from.toLowerCase() : '';
  const senderContact = senderEmail ? contactMap[senderEmail] : null;

  const updateThreadState = useCallback(
    (threadId: string, updates: Partial<ThreadState>) => {
      setThreadStates((prev) => ({
        ...prev,
        [threadId]: { ...prev[threadId], ...updates },
      }));
    },
    []
  );

  // ── AI Classification ────────────────────────────────────────────────

  const runClassification = useCallback(
    async (msgs: EmailMessage[]) => {
      const unclassified = msgs.filter((m) => m.category === 'unclassified');
      if (unclassified.length === 0) return;

      setClassifying(true);
      setClassifyError(null);
      try {
        const res = await fetch('/api/network-intel/email-triage/classify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            emails: unclassified.map((m) => ({
              id: m.id,
              from: m.from,
              fromName: m.fromName,
              subject: m.subject,
              snippet: m.snippet,
              account: m.account,
            })),
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Classification failed');

        const classifications = data.classifications as Array<{
          id: string;
          category: EmailCategory;
          reason: string;
        }>;

        // Build lookup map
        const classMap = new Map(classifications.map((c) => [c.id, c]));

        // Update flat messages
        setFlatMessages((prev) =>
          prev.map((m) => {
            const cls = classMap.get(m.id);
            if (cls && m.category === 'unclassified') {
              return { ...m, category: cls.category, categoryReason: cls.reason };
            }
            return m;
          })
        );

        // Update threads with new classifications
        setThreads((prev) =>
          prev.map((thread) => {
            const updatedMessages = thread.messages.map((m) => {
              const cls = classMap.get(m.id);
              if (cls && m.category === 'unclassified') {
                return { ...m, category: cls.category, categoryReason: cls.reason };
              }
              return m;
            });

            // Recompute thread category
            const categoryPriority: Record<EmailCategory, number> = {
              action: 3, unclassified: 2, fyi: 1, skip: 0,
            };
            let threadCategory = updatedMessages[updatedMessages.length - 1].category;
            let threadCategoryReason = updatedMessages[updatedMessages.length - 1].categoryReason;
            for (const m of updatedMessages) {
              if (categoryPriority[m.category] > categoryPriority[threadCategory]) {
                threadCategory = m.category;
                threadCategoryReason = m.categoryReason;
              }
            }

            return {
              ...thread,
              messages: updatedMessages,
              lastMessage: updatedMessages[updatedMessages.length - 1],
              category: threadCategory,
              categoryReason: threadCategoryReason,
            };
          })
        );
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : 'Classification failed';
        console.error('Classification error:', msg);
        setClassifyError(msg);
      } finally {
        setClassifying(false);
      }
    },
    []
  );

  // Auto-trigger classification after scan
  useEffect(() => {
    if (
      flatMessages.length > 0 &&
      !classifying &&
      !classifyTriggered.current &&
      flatMessages.some((m) => m.category === 'unclassified')
    ) {
      classifyTriggered.current = true;
      runClassification(flatMessages);
    }
  }, [flatMessages, classifying, runClassification]);

  // ── Contact Lookup ───────────────────────────────────────────────────

  const runContactLookup = useCallback(async (msgs: EmailMessage[]) => {
    const emails = [...new Set(msgs.map((m) => m.from.toLowerCase()))];
    if (emails.length === 0) return;

    try {
      const res = await fetch('/api/network-intel/email-triage/contact-lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emails }),
      });
      const data = await res.json();
      if (res.ok && data.contacts) {
        setContactMap(data.contacts);
      }
    } catch (e) {
      console.error('Contact lookup failed:', e);
    }
  }, []);

  // ── Scan ─────────────────────────────────────────────────────────────

  const handleScan = useCallback(async () => {
    setScanning(true);
    setScanError(null);
    classifyTriggered.current = false;
    try {
      const res = await fetch('/api/network-intel/email-triage/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ newer_than_days: 21 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Scan failed');

      setThreads(data.threads || []);
      setFlatMessages(data.messages || []);
      setAccountsScanned(data.accounts_scanned);

      // Initialize thread states
      const states: Record<string, ThreadState> = {};
      for (const thread of (data.threads || [])) {
        states[thread.threadId] = {
          status: 'pending',
          messages: [],
          draftBody: '',
          draftSubject: `Re: ${thread.subject}`,
        };
      }
      setThreadStates(states);
      setSelectedThreadId(null);
      setActiveTab('action');

      // Surface scan warnings
      const warnings: string[] = [];
      if (data.accounts_failed?.length > 0) {
        for (const f of data.accounts_failed) warnings.push(`${f.account}: ${f.error}`);
      }
      if (data.fetch_failures > 0) warnings.push(`${data.fetch_failures} individual message(s) failed to load`);
      setScanWarnings(warnings);

      // Trigger contact lookup
      if (data.messages?.length > 0) {
        runContactLookup(data.messages);
      }
    } catch (e: unknown) {
      setScanError(e instanceof Error ? e.message : 'Scan failed');
    } finally {
      setScanning(false);
    }
  }, [runContactLookup]);

  // ── Thread Selection ─────────────────────────────────────────────────

  const handleSelectThread = useCallback(
    async (thread: EmailThread) => {
      setSelectedThreadId(thread.threadId);
      setConfirmSend(false);

      const state = threadStates[thread.threadId];
      if (state && state.status === 'pending') {
        updateThreadState(thread.threadId, { status: 'loading' });
        try {
          const res = await fetch('/api/network-intel/email-triage/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ thread_id: thread.threadId, account: thread.account }),
          });
          const data = await res.json();
          if (res.ok) {
            const messages = data.messages || [data]; // backward compat
            updateThreadState(thread.threadId, { status: 'loaded', messages });
            // Expand the last message by default
            if (messages.length > 0) {
              setExpandedMessages(new Set([messages[messages.length - 1].id]));
            }
          } else {
            updateThreadState(thread.threadId, {
              status: 'loaded',
              fetchError: data.error || 'Failed to load thread',
            });
          }
        } catch (e: unknown) {
          updateThreadState(thread.threadId, {
            status: 'loaded',
            fetchError: `Network error: ${e instanceof Error ? e.message : 'unknown'}`,
          });
        }
      } else if (state?.messages.length > 0) {
        // Already loaded — just expand last message
        setExpandedMessages(new Set([state.messages[state.messages.length - 1].id]));
      }
    },
    [threadStates, updateThreadState]
  );

  // ── Draft Response ───────────────────────────────────────────────────

  const handleDraftResponse = useCallback(async () => {
    if (!selectedThreadId || !selectedThread) return;

    updateThreadState(selectedThreadId, { status: 'drafting' });

    try {
      const state = threadStates[selectedThreadId];
      // Build thread context from all messages
      const threadContext = state?.messages
        .map((m) => `From: ${m.from}\nTo: ${m.to}\nDate: ${m.date}\nSubject: ${m.subject}\n\n${m.body}`)
        .join('\n\n--- Next message ---\n\n');

      // Get contact context for the sender
      const contact = senderContact;

      const res = await fetch('/api/network-intel/email-triage/draft-response', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: selectedThread.lastMessage.id,
          account: selectedThread.account,
          thread_context: threadContext || undefined,
          contact_context: contact || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Draft failed');

      updateThreadState(selectedThreadId, {
        status: 'draft_ready',
        draftBody: data.draft_body,
      });
    } catch (e: unknown) {
      updateThreadState(selectedThreadId, { status: 'loaded' });
      alert(`Draft failed: ${e instanceof Error ? e.message : 'unknown error'}`);
    }
  }, [selectedThreadId, selectedThread, threadStates, updateThreadState, senderContact]);

  // ── Gmail Actions ────────────────────────────────────────────────────

  const handleGmailAction = useCallback(
    async (action: 'draft' | 'send') => {
      if (!selectedThreadId || !selectedThread) return;

      const state = threadStates[selectedThreadId];
      if (!state) return;

      const replyTo = parseFromEmail(selectedThread.lastMessage.from);

      updateThreadState(selectedThreadId, { status: 'sending' });

      try {
        const res = await fetch('/api/network-intel/email-triage/gmail-action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action,
            account: selectedThread.account,
            thread_id: selectedThread.threadId,
            message_id: selectedThread.lastMessage.id,
            subject: state.draftSubject,
            body: state.draftBody,
            to: replyTo,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `${action} failed`);

        updateThreadState(selectedThreadId, {
          status: action === 'send' ? 'sent' : 'saved',
        });
        setConfirmSend(false);
      } catch (e: unknown) {
        updateThreadState(selectedThreadId, { status: 'draft_ready' });
        alert(`${action === 'send' ? 'Send' : 'Save'} failed: ${e instanceof Error ? e.message : 'unknown error'}`);
      }
    },
    [selectedThreadId, selectedThread, threadStates, updateThreadState]
  );

  // ── Mark Done ────────────────────────────────────────────────────────

  const handleMarkDone = useCallback(() => {
    if (!selectedThreadId) return;
    updateThreadState(selectedThreadId, { status: 'done' });
    const notDoneNow = threads.filter(
      (t) => threadStates[t.threadId]?.status !== 'done' && t.threadId !== selectedThreadId
    );
    const filtered = notDoneNow.filter((t) => {
      if (activeTab === 'all') return true;
      if (activeTab === 'action') return t.category === 'action' || t.category === 'unclassified';
      return t.category === activeTab;
    });
    setSelectedThreadId(filtered.length > 0 ? filtered[0].threadId : null);
    setConfirmSend(false);
  }, [selectedThreadId, threads, threadStates, activeTab, updateThreadState]);

  // ── Reclassify ───────────────────────────────────────────────────────

  const handleReclassify = useCallback(
    (threadId: string, newCategory: EmailCategory) => {
      setThreads((prev) =>
        prev.map((t) =>
          t.threadId === threadId
            ? { ...t, category: newCategory, categoryReason: 'Manually reclassified' }
            : t
        )
      );
    },
    []
  );

  // ── Toggle message expand ────────────────────────────────────────────

  const toggleMessage = useCallback((msgId: string) => {
    setExpandedMessages((prev) => {
      const next = new Set(prev);
      if (next.has(msgId)) next.delete(msgId);
      else next.add(msgId);
      return next;
    });
  }, []);

  // ── Computed values ──────────────────────────────────────────────────

  const notDone = threads.filter((t) => threadStates[t.threadId]?.status !== 'done');
  const counts = {
    action: notDone.filter((t) => t.category === 'action').length,
    fyi: notDone.filter((t) => t.category === 'fyi').length,
    skip: notDone.filter((t) => t.category === 'skip').length,
    unclassified: notDone.filter((t) => t.category === 'unclassified').length,
    all: notDone.length,
  };
  const doneCount = threads.filter((t) => threadStates[t.threadId]?.status === 'done').length;

  const filteredThreads = notDone.filter((t) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'action') return t.category === 'action' || t.category === 'unclassified';
    return t.category === activeTab;
  });

  // ── Render ───────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="flex-none border-b bg-white px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Inbox className="h-5 w-5 text-red-600" />
            <h1 className="text-lg font-semibold">Email Triage</h1>
            {threads.length > 0 && (
              <span className="text-sm text-muted-foreground">
                {threads.length} threads ({flatMessages.length} emails)
                {doneCount > 0 && ` \u00B7 ${doneCount} done`}
                {accountsScanned > 0 && ` \u00B7 ${accountsScanned} accounts`}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {classifying && (
              <span className="flex items-center gap-1.5 text-sm text-amber-600">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Classifying...
              </span>
            )}
            {classifyError && (
              <button
                onClick={() => {
                  setClassifyError(null);
                  classifyTriggered.current = false;
                  runClassification(flatMessages);
                }}
                className="flex items-center gap-1.5 text-sm text-red-600 hover:underline"
              >
                <AlertCircle className="h-3.5 w-3.5" />
                Classification failed — retry
              </button>
            )}
            <Button onClick={handleScan} disabled={scanning} variant="outline" size="sm">
              {scanning ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
              {scanning ? 'Scanning...' : threads.length > 0 ? 'Rescan' : 'Scan Inbox'}
            </Button>
          </div>
        </div>
        {scanError && (
          <div className="mt-2 flex items-center gap-2 text-sm text-red-600">
            <AlertCircle className="h-4 w-4" />
            {scanError}
          </div>
        )}
        {scanWarnings.length > 0 && (
          <div className="mt-2 text-sm text-amber-600">
            {scanWarnings.map((w, i) => (
              <div key={i} className="flex items-center gap-2">
                <AlertCircle className="h-3.5 w-3.5 flex-none" />
                {w}
              </div>
            ))}
          </div>
        )}

        {/* Filter tabs */}
        {threads.length > 0 && (
          <div className="flex items-center gap-1 mt-2">
            <Filter className="h-3.5 w-3.5 text-muted-foreground mr-1" />
            {([
              { key: 'action' as FilterTab, label: 'Action', count: counts.action + counts.unclassified },
              { key: 'fyi' as FilterTab, label: 'FYI', count: counts.fyi },
              { key: 'skip' as FilterTab, label: 'Skip', count: counts.skip },
              { key: 'all' as FilterTab, label: 'All', count: counts.all },
            ]).map((tab) => (
              <button
                key={tab.key}
                onClick={() => { setActiveTab(tab.key); setSelectedThreadId(null); }}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  activeTab === tab.key
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {tab.label}
                {tab.count > 0 && <span className="ml-1.5 opacity-75">{tab.count}</span>}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main content — 3-column layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel — Thread list */}
        <div className="w-[380px] flex-none border-r bg-white overflow-y-auto">
          {threads.length === 0 && !scanning && (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground p-8 text-center">
              <Inbox className="h-12 w-12 mb-4 opacity-30" />
              <p className="text-sm">Click &ldquo;Scan Inbox&rdquo; to search all 5 Gmail accounts for unread emails.</p>
            </div>
          )}
          {scanning && threads.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <Loader2 className="h-8 w-8 animate-spin mb-4" />
              <p className="text-sm">Scanning all accounts...</p>
            </div>
          )}
          {filteredThreads.length === 0 && threads.length > 0 && !scanning && (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground p-8 text-center">
              <Check className="h-12 w-12 mb-4 opacity-30" />
              <p className="text-sm">No threads in this category.</p>
            </div>
          )}
          {filteredThreads.map((thread) => {
            const state = threadStates[thread.threadId];
            const acct = ACCOUNT_STYLES[thread.account] || { label: thread.account.split('@')[1], bg: 'bg-gray-100', text: 'text-gray-700', dot: 'bg-gray-500' };
            const cat = CATEGORY_STYLES[thread.category];
            const isSelected = thread.threadId === selectedThreadId;
            const isSkip = thread.category === 'skip';
            const senderInDB = !!contactMap[thread.lastMessage.from.toLowerCase()];

            return (
              <div
                key={thread.threadId}
                onClick={() => handleSelectThread(thread)}
                className={`cursor-pointer border-b px-3 py-2.5 transition-colors hover:bg-gray-50 ${
                  isSelected ? 'bg-blue-50 border-l-2 border-l-blue-500' : ''
                } ${isSkip ? 'opacity-50' : ''}`}
              >
                <div className="flex items-start gap-2.5">
                  {/* Avatar */}
                  <SenderAvatar name={thread.lastMessage.fromName} size="sm" />

                  <div className="min-w-0 flex-1">
                    {/* Row 1: Sender name + badges + date */}
                    <div className="flex items-center justify-between mb-0.5">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className={`font-medium text-sm truncate ${isSkip ? 'line-through text-gray-400' : ''}`}>
                          {thread.lastMessage.fromName}
                        </span>
                        {senderInDB && <UserCheck className="h-3 w-3 text-green-600 flex-none" />}
                        {thread.messageCount > 1 && (
                          <span className="text-[10px] bg-gray-200 text-gray-600 px-1 rounded font-medium flex-none">
                            {thread.messageCount}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 flex-none ml-2">
                        {state?.status === 'sent' && <Check className="h-3 w-3 text-green-600" />}
                        {state?.status === 'saved' && <Save className="h-3 w-3 text-blue-600" />}
                        {state?.status === 'draft_ready' && <Sparkles className="h-3 w-3 text-amber-500" />}
                        <span className="text-[11px] text-muted-foreground">{formatDate(thread.lastMessage.date)}</span>
                      </div>
                    </div>

                    {/* Row 2: Subject + account badge */}
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <div className={`w-1.5 h-1.5 rounded-full ${acct.dot} flex-none`} />
                      <span className={`text-sm truncate ${isSkip ? 'text-gray-400' : 'font-medium'}`}>
                        {thread.subject}
                      </span>
                    </div>

                    {/* Row 3: Snippet + category badge */}
                    <div className="flex items-center justify-between">
                      <p className="text-xs text-muted-foreground truncate flex-1 mr-2">
                        {thread.lastMessage.snippet}
                      </p>
                      <Badge variant="secondary" className={`text-[9px] px-1 py-0 ${cat.bg} ${cat.text} border-0 font-bold flex-none`}>
                        {cat.label}
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Center panel — Conversation view */}
        <div className="flex-1 overflow-y-auto bg-white">
          {!selectedThread ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <p className="text-sm">Select a thread to view</p>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto p-6">
              {/* Thread header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1 min-w-0">
                  <h2 className="text-xl font-semibold leading-tight mb-1">{selectedThread.subject}</h2>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className={`text-[10px] px-1.5 py-0 ${CATEGORY_STYLES[selectedThread.category].bg} ${CATEGORY_STYLES[selectedThread.category].text} border-0`}>
                      {CATEGORY_STYLES[selectedThread.category].label}
                    </Badge>
                    <Badge variant="secondary" className={`text-[10px] px-1.5 py-0 ${ACCOUNT_STYLES[selectedThread.account]?.bg || 'bg-gray-100'} ${ACCOUNT_STYLES[selectedThread.account]?.text || 'text-gray-700'} border-0`}>
                      {ACCOUNT_STYLES[selectedThread.account]?.label || selectedThread.account}
                    </Badge>
                    {selectedThread.categoryReason && (
                      <span className="text-[10px] text-muted-foreground italic">{selectedThread.categoryReason}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-none">
                  {selectedThread.category !== 'action' && (
                    <Button variant="ghost" size="sm" onClick={() => handleReclassify(selectedThread.threadId, 'action')} className="text-red-600 text-xs h-7 px-2">
                      <Zap className="h-3 w-3 mr-1" />Action
                    </Button>
                  )}
                  {selectedThread.category !== 'skip' && (
                    <Button variant="ghost" size="sm" onClick={() => handleReclassify(selectedThread.threadId, 'skip')} className="text-gray-400 text-xs h-7 px-2">
                      <EyeOff className="h-3 w-3 mr-1" />Skip
                    </Button>
                  )}
                  <Button variant="ghost" size="sm" onClick={handleMarkDone} className="flex-none text-muted-foreground">
                    <X className="h-4 w-4 mr-1" />Done
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowContactPanel(!showContactPanel)}
                    className={`flex-none ${showContactPanel ? 'text-blue-600' : 'text-muted-foreground'}`}
                    title={showContactPanel ? 'Hide contact panel' : 'Show contact panel'}
                  >
                    <UserCheck className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <Separator className="mb-4" />

              {/* Messages */}
              {selectedState?.status === 'loading' && (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              )}

              {selectedState?.fetchError && (
                <div className="py-8 text-center">
                  <AlertCircle className="h-6 w-6 text-red-500 mx-auto mb-2" />
                  <p className="text-sm text-red-500">{selectedState.fetchError}</p>
                  <p className="text-xs text-muted-foreground mt-2 italic">{selectedThread.lastMessage.snippet}</p>
                </div>
              )}

              {selectedState?.messages && selectedState.messages.length > 0 && (
                <div className="space-y-3 mb-6">
                  {selectedState.messages.map((msg, i) => {
                    const isLast = i === selectedState.messages.length - 1;
                    const isExpanded = expandedMessages.has(msg.id) || isLast;

                    return (
                      <div key={msg.id} className="border rounded-lg overflow-hidden">
                        {/* Message header — always visible */}
                        <div
                          onClick={() => !isLast && toggleMessage(msg.id)}
                          className={`flex items-center gap-3 px-4 py-2.5 ${!isLast ? 'cursor-pointer hover:bg-gray-50' : ''} ${isExpanded ? 'border-b' : ''}`}
                        >
                          <SenderAvatar name={msg.fromName} size="sm" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm">{msg.fromName}</span>
                              <span className="text-xs text-muted-foreground truncate">&lt;{msg.fromEmail}&gt;</span>
                            </div>
                            {!isExpanded && (
                              <p className="text-xs text-muted-foreground truncate">{msg.body.slice(0, 100)}...</p>
                            )}
                          </div>
                          <div className="flex items-center gap-2 flex-none">
                            <span className="text-xs text-muted-foreground">{formatFullDate(msg.date)}</span>
                            {!isLast && (
                              isExpanded
                                ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                : <ChevronRight className="h-4 w-4 text-muted-foreground" />
                            )}
                          </div>
                        </div>

                        {/* Message body */}
                        {isExpanded && (
                          <div className="px-4 py-3">
                            {msg.to && (
                              <p className="text-xs text-muted-foreground mb-2">
                                To: {msg.to.length > 80 ? msg.to.slice(0, 80) + '...' : msg.to}
                                {msg.cc && <><br />Cc: {msg.cc.length > 80 ? msg.cc.slice(0, 80) + '...' : msg.cc}</>}
                              </p>
                            )}
                            <div className="text-sm whitespace-pre-wrap leading-relaxed">
                              {msg.body}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Only show snippet if no messages loaded yet and not loading */}
              {(!selectedState?.messages || selectedState.messages.length === 0) && selectedState?.status !== 'loading' && !selectedState?.fetchError && (
                <div className="mb-6">
                  <p className="text-sm text-muted-foreground italic">{selectedThread.lastMessage.snippet}</p>
                </div>
              )}

              <Separator className="mb-4" />

              {/* Inline Reply */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-muted-foreground" />
                    <h3 className="font-medium text-sm text-muted-foreground">Reply</h3>
                    {senderContact && (
                      <span className="text-[10px] text-green-600 flex items-center gap-0.5">
                        <UserCheck className="h-3 w-3" />
                        Draft with {senderContact.first_name}&apos;s context
                      </span>
                    )}
                  </div>
                  <Button
                    onClick={handleDraftResponse}
                    disabled={selectedState?.status === 'drafting'}
                    variant="outline"
                    size="sm"
                  >
                    {selectedState?.status === 'drafting' ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4 mr-2" />
                    )}
                    {selectedState?.status === 'drafting'
                      ? 'Drafting...'
                      : selectedState?.draftBody
                        ? 'Regenerate'
                        : 'Draft Response'}
                  </Button>
                </div>

                {/* Subject */}
                <div className="mb-2">
                  <input
                    type="text"
                    className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={selectedState?.draftSubject || `Re: ${selectedThread.subject}`}
                    onChange={(e) => updateThreadState(selectedThread.threadId, { draftSubject: e.target.value })}
                  />
                </div>

                {/* Body */}
                <textarea
                  className="w-full min-h-[160px] px-3 py-2 border rounded-md text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                  placeholder={
                    selectedState?.status === 'drafting'
                      ? 'Generating draft with contact context...'
                      : 'Click "Draft Response" to generate a reply, or type your own...'
                  }
                  value={selectedState?.draftBody || ''}
                  onChange={(e) =>
                    updateThreadState(selectedThread.threadId, {
                      draftBody: e.target.value,
                      status: selectedState?.status === 'pending' || selectedState?.status === 'loaded'
                        ? 'draft_ready'
                        : selectedState?.status || 'draft_ready',
                    })
                  }
                  disabled={selectedState?.status === 'drafting'}
                />

                {/* Action buttons */}
                <div className="flex items-center gap-3 mt-3">
                  <Button
                    onClick={() => handleGmailAction('draft')}
                    disabled={!selectedState?.draftBody || selectedState?.status === 'sending' || selectedState?.status === 'drafting'}
                    variant="outline"
                    size="sm"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    Save to Drafts
                  </Button>

                  {!confirmSend ? (
                    <Button
                      onClick={() => setConfirmSend(true)}
                      disabled={!selectedState?.draftBody || selectedState?.status === 'sending' || selectedState?.status === 'drafting'}
                      size="sm"
                    >
                      <Send className="h-4 w-4 mr-2" />
                      Send Reply
                    </Button>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-amber-600 font-medium">
                        Send to {parseFromEmail(selectedThread.lastMessage.from)}?
                      </span>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleGmailAction('send')}
                        disabled={selectedState?.status === 'sending'}
                      >
                        {selectedState?.status === 'sending' ? (
                          <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                        ) : (
                          <Check className="h-4 w-4 mr-1" />
                        )}
                        Confirm
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setConfirmSend(false)}>Cancel</Button>
                    </div>
                  )}

                  {selectedState?.status === 'sent' && (
                    <span className="text-sm text-green-600 flex items-center gap-1">
                      <Check className="h-4 w-4" /> Sent
                    </span>
                  )}
                  {selectedState?.status === 'saved' && (
                    <span className="text-sm text-blue-600 flex items-center gap-1">
                      <Check className="h-4 w-4" /> Saved to Drafts
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right panel — Contact context */}
        {showContactPanel && selectedThread && (
          <div className="w-[280px] flex-none border-l bg-gray-50 overflow-y-auto">
            <ContactSidebar contact={senderContact} senderEmail={senderEmail} />
          </div>
        )}
      </div>
    </div>
  );
}
