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
  Eye,
  EyeOff,
  Zap,
} from 'lucide-react';

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

interface FullMessage {
  id: string;
  threadId: string;
  from: string;
  to: string;
  cc: string;
  subject: string;
  date: string;
  body: string;
}

type EmailStatus = 'pending' | 'drafting' | 'draft_ready' | 'sending' | 'sent' | 'saved' | 'done';

interface EmailState {
  status: EmailStatus;
  draftBody: string;
  draftSubject: string;
  fullMessage: FullMessage | null;
  fetchError?: string;
}

const ACCOUNT_STYLES: Record<string, { label: string; bg: string; text: string }> = {
  'justinrsteele@gmail.com': { label: 'Gmail', bg: 'bg-red-100', text: 'text-red-700' },
  'justin@truesteele.com': { label: 'TrueSteele', bg: 'bg-blue-100', text: 'text-blue-700' },
  'justin@outdoorithm.com': { label: 'Outdoorithm', bg: 'bg-green-100', text: 'text-green-700' },
  'justin@outdoorithmcollective.org': { label: 'OC', bg: 'bg-orange-100', text: 'text-orange-700' },
  'justin@kindora.co': { label: 'Kindora', bg: 'bg-purple-100', text: 'text-purple-700' },
};

const CATEGORY_STYLES: Record<EmailCategory, { label: string; bg: string; text: string; icon: string }> = {
  action: { label: 'Action', bg: 'bg-red-50', text: 'text-red-700', icon: '!' },
  fyi: { label: 'FYI', bg: 'bg-sky-50', text: 'text-sky-700', icon: 'i' },
  skip: { label: 'Skip', bg: 'bg-gray-100', text: 'text-gray-500', icon: '~' },
  unclassified: { label: '...', bg: 'bg-yellow-50', text: 'text-yellow-700', icon: '?' },
};

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return d.toLocaleDateString('en-US', { weekday: 'short' });
    } else {
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  } catch {
    return dateStr;
  }
}

function parseFromEmail(from: string): string {
  const match = from.match(/<([^>]+)>/);
  return match ? match[1] : from;
}

export default function EmailTriagePage() {
  const [messages, setMessages] = useState<EmailMessage[]>([]);
  const [emailStates, setEmailStates] = useState<Record<string, EmailState>>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [classifying, setClassifying] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [accountsScanned, setAccountsScanned] = useState(0);
  const [confirmSend, setConfirmSend] = useState(false);
  const [activeTab, setActiveTab] = useState<FilterTab>('action');
  const [classifyError, setClassifyError] = useState<string | null>(null);
  const [scanWarnings, setScanWarnings] = useState<string[]>([]);
  const classifyTriggered = useRef(false);

  const selectedMessage = messages.find((m) => m.id === selectedId);
  const selectedState = selectedId ? emailStates[selectedId] : undefined;

  const updateEmailState = useCallback(
    (id: string, updates: Partial<EmailState>) => {
      setEmailStates((prev) => ({
        ...prev,
        [id]: { ...prev[id], ...updates },
      }));
    },
    []
  );

  // ── AI Classification ──────────────────────────────────────────────

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

        // Update messages with AI classifications
        setMessages((prev) =>
          prev.map((m) => {
            const cls = classifications.find((c) => c.id === m.id);
            if (cls && m.category === 'unclassified') {
              return { ...m, category: cls.category, categoryReason: cls.reason };
            }
            return m;
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
      messages.length > 0 &&
      !classifying &&
      !classifyTriggered.current &&
      messages.some((m) => m.category === 'unclassified')
    ) {
      classifyTriggered.current = true;
      runClassification(messages);
    }
  }, [messages, classifying, runClassification]);

  // ── Scan ────────────────────────────────────────────────────────────

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

      setMessages(data.messages);
      setAccountsScanned(data.accounts_scanned);

      // Surface scan warnings
      const warnings: string[] = [];
      if (data.accounts_failed?.length > 0) {
        for (const f of data.accounts_failed) {
          warnings.push(`${f.account}: ${f.error}`);
        }
      }
      if (data.fetch_failures > 0) {
        warnings.push(`${data.fetch_failures} individual message(s) failed to load`);
      }
      setScanWarnings(warnings);

      // Initialize states for new messages
      const states: Record<string, EmailState> = {};
      for (const msg of data.messages) {
        states[msg.id] = {
          status: 'pending',
          draftBody: '',
          draftSubject: `Re: ${msg.subject}`,
          fullMessage: null,
        };
      }
      setEmailStates(states);
      setSelectedId(null);
      setActiveTab('action');
    } catch (e: unknown) {
      setScanError(e instanceof Error ? e.message : 'Scan failed');
    } finally {
      setScanning(false);
    }
  }, []);

  // ── Message Selection ───────────────────────────────────────────────

  const handleSelect = useCallback(
    async (msg: EmailMessage) => {
      setSelectedId(msg.id);
      setConfirmSend(false);

      const state = emailStates[msg.id];
      if (state && !state.fullMessage && !state.fetchError) {
        try {
          const res = await fetch('/api/network-intel/email-triage/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_id: msg.id, account: msg.account }),
          });
          const data = await res.json();
          if (res.ok) {
            updateEmailState(msg.id, { fullMessage: data });
          } else {
            updateEmailState(msg.id, {
              fetchError: data.error || 'Failed to load message',
            });
          }
        } catch (e: unknown) {
          updateEmailState(msg.id, {
            fetchError: `Network error: ${e instanceof Error ? e.message : 'unknown'}`,
          });
        }
      }
    },
    [emailStates, updateEmailState]
  );

  // ── Draft Response ──────────────────────────────────────────────────

  const handleDraftResponse = useCallback(async () => {
    if (!selectedId || !selectedMessage) return;

    updateEmailState(selectedId, { status: 'drafting' });

    try {
      const state = emailStates[selectedId];
      const threadContext = state?.fullMessage
        ? `From: ${state.fullMessage.from}\nTo: ${state.fullMessage.to}\nDate: ${state.fullMessage.date}\nSubject: ${state.fullMessage.subject}\n\n${state.fullMessage.body}`
        : undefined;

      const res = await fetch('/api/network-intel/email-triage/draft-response', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: selectedId,
          account: selectedMessage.account,
          thread_context: threadContext,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Draft failed');

      updateEmailState(selectedId, {
        status: 'draft_ready',
        draftBody: data.draft_body,
      });
    } catch (e: unknown) {
      updateEmailState(selectedId, { status: 'pending' });
      alert(`Draft failed: ${e instanceof Error ? e.message : 'unknown error'}`);
    }
  }, [selectedId, selectedMessage, emailStates, updateEmailState]);

  // ── Gmail Actions ───────────────────────────────────────────────────

  const handleGmailAction = useCallback(
    async (action: 'draft' | 'send') => {
      if (!selectedId || !selectedMessage) return;

      const state = emailStates[selectedId];
      if (!state) return;

      const replyTo = parseFromEmail(selectedMessage.from);

      updateEmailState(selectedId, { status: 'sending' });

      try {
        const res = await fetch('/api/network-intel/email-triage/gmail-action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action,
            account: selectedMessage.account,
            thread_id: selectedMessage.threadId,
            message_id: selectedId,
            subject: state.draftSubject,
            body: state.draftBody,
            to: replyTo,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `${action} failed`);

        updateEmailState(selectedId, {
          status: action === 'send' ? 'sent' : 'saved',
        });
        setConfirmSend(false);
      } catch (e: unknown) {
        updateEmailState(selectedId, { status: 'draft_ready' });
        alert(`${action === 'send' ? 'Send' : 'Save'} failed: ${e instanceof Error ? e.message : 'unknown error'}`);
      }
    },
    [selectedId, selectedMessage, emailStates, updateEmailState]
  );

  // ── Mark Done ───────────────────────────────────────────────────────

  const handleMarkDone = useCallback(() => {
    if (!selectedId) return;
    updateEmailState(selectedId, { status: 'done' });
    // Recompute filtered list inside callback to avoid stale closure
    const notDoneNow = messages.filter(
      (m) => emailStates[m.id]?.status !== 'done' && m.id !== selectedId
    );
    const filtered = notDoneNow.filter((m) => {
      if (activeTab === 'all') return true;
      if (activeTab === 'action') return m.category === 'action' || m.category === 'unclassified';
      return m.category === activeTab;
    });
    setSelectedId(filtered.length > 0 ? filtered[0].id : null);
    setConfirmSend(false);
  }, [selectedId, messages, emailStates, activeTab, updateEmailState]);

  // ── Reclassify a single email ───────────────────────────────────────

  const handleReclassify = useCallback(
    (id: string, newCategory: EmailCategory) => {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id
            ? { ...m, category: newCategory, categoryReason: 'Manually reclassified' }
            : m
        )
      );
    },
    []
  );

  // ── Computed values ─────────────────────────────────────────────────

  const notDone = messages.filter((m) => emailStates[m.id]?.status !== 'done');
  const counts = {
    action: notDone.filter((m) => m.category === 'action').length,
    fyi: notDone.filter((m) => m.category === 'fyi').length,
    skip: notDone.filter((m) => m.category === 'skip').length,
    unclassified: notDone.filter((m) => m.category === 'unclassified').length,
    all: notDone.length,
  };
  const doneCount = messages.filter((m) => emailStates[m.id]?.status === 'done').length;

  const filteredMessages = notDone.filter((m) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'action') return m.category === 'action' || m.category === 'unclassified';
    return m.category === activeTab;
  });

  // ── Render ──────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="flex-none border-b bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Inbox className="h-6 w-6 text-red-600" />
            <h1 className="text-xl font-semibold">Email Triage</h1>
            {messages.length > 0 && (
              <span className="text-sm text-muted-foreground">
                {messages.length} emails
                {doneCount > 0 && ` (${doneCount} done)`}
                {accountsScanned > 0 && ` across ${accountsScanned} accounts`}
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
                  runClassification(messages);
                }}
                className="flex items-center gap-1.5 text-sm text-red-600 hover:underline"
              >
                <AlertCircle className="h-3.5 w-3.5" />
                Classification failed — click to retry
              </button>
            )}
            <Button onClick={handleScan} disabled={scanning} variant="outline">
              {scanning ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              {scanning ? 'Scanning...' : messages.length > 0 ? 'Rescan' : 'Scan Inbox'}
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
        {messages.length > 0 && (
          <div className="flex items-center gap-1 mt-3">
            <Filter className="h-3.5 w-3.5 text-muted-foreground mr-1" />
            {(
              [
                { key: 'action' as FilterTab, label: 'Action', count: counts.action + counts.unclassified },
                { key: 'fyi' as FilterTab, label: 'FYI', count: counts.fyi },
                { key: 'skip' as FilterTab, label: 'Skipped', count: counts.skip },
                { key: 'all' as FilterTab, label: 'All', count: counts.all },
              ] as const
            ).map((tab) => (
              <button
                key={tab.key}
                onClick={() => {
                  setActiveTab(tab.key);
                  setSelectedId(null);
                }}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  activeTab === tab.key
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {tab.label}
                {tab.count > 0 && (
                  <span className="ml-1.5 opacity-75">{tab.count}</span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel — email list */}
        <div className="w-[420px] flex-none border-r bg-white overflow-y-auto">
          {messages.length === 0 && !scanning && (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground p-8 text-center">
              <Inbox className="h-12 w-12 mb-4 opacity-30" />
              <p className="text-sm">
                Click &ldquo;Scan Inbox&rdquo; to search all 5 Gmail accounts for unread
                emails from the last 21 days.
              </p>
            </div>
          )}
          {scanning && messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <Loader2 className="h-8 w-8 animate-spin mb-4" />
              <p className="text-sm">Scanning all accounts...</p>
            </div>
          )}
          {filteredMessages.length === 0 && messages.length > 0 && !scanning && (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground p-8 text-center">
              <Check className="h-12 w-12 mb-4 opacity-30" />
              <p className="text-sm">No emails in this category.</p>
            </div>
          )}
          {filteredMessages.map((msg) => {
            const state = emailStates[msg.id];
            const acct = ACCOUNT_STYLES[msg.account] || {
              label: msg.account.split('@')[1],
              bg: 'bg-gray-100',
              text: 'text-gray-700',
            };
            const cat = CATEGORY_STYLES[msg.category];
            const isSelected = msg.id === selectedId;
            const isSkip = msg.category === 'skip';

            return (
              <div
                key={msg.id}
                onClick={() => handleSelect(msg)}
                className={`cursor-pointer border-b px-4 py-3 transition-colors hover:bg-gray-50 ${
                  isSelected ? 'bg-blue-50 border-l-2 border-l-blue-500' : ''
                } ${isSkip ? 'opacity-50' : ''}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`font-medium text-sm truncate max-w-[180px] ${isSkip ? 'line-through' : ''}`}>
                    {msg.fromName}
                  </span>
                  <div className="flex items-center gap-1.5 flex-none">
                    {state?.status === 'sent' && (
                      <Check className="h-3.5 w-3.5 text-green-600" />
                    )}
                    {state?.status === 'saved' && (
                      <Save className="h-3.5 w-3.5 text-blue-600" />
                    )}
                    {state?.status === 'draft_ready' && (
                      <Sparkles className="h-3.5 w-3.5 text-amber-500" />
                    )}
                    <Badge
                      variant="secondary"
                      className={`text-[9px] px-1 py-0 ${cat.bg} ${cat.text} border-0 font-bold`}
                    >
                      {cat.label}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(msg.date)}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 mb-1">
                  <Badge
                    variant="secondary"
                    className={`text-[10px] px-1.5 py-0 ${acct.bg} ${acct.text} border-0`}
                  >
                    {acct.label}
                  </Badge>
                  <span className={`text-sm font-medium truncate ${isSkip ? 'text-gray-400' : ''}`}>
                    {msg.subject}
                  </span>
                </div>
                {msg.categoryReason && (
                  <p className="text-[10px] text-muted-foreground italic truncate">
                    {msg.categoryReason}
                  </p>
                )}
              </div>
            );
          })}
        </div>

        {/* Right panel — detail + response */}
        <div className="flex-1 overflow-y-auto bg-white">
          {!selectedMessage ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <p className="text-sm">Select an email to view</p>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto p-6">
              {/* Email header */}
              <div className="mb-6">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-semibold leading-tight">
                      {selectedMessage.subject}
                    </h2>
                    <Badge
                      variant="secondary"
                      className={`text-[10px] px-1.5 py-0 ${CATEGORY_STYLES[selectedMessage.category].bg} ${CATEGORY_STYLES[selectedMessage.category].text} border-0 flex-none`}
                    >
                      {CATEGORY_STYLES[selectedMessage.category].label}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1 flex-none">
                    {/* Reclassify buttons */}
                    {selectedMessage.category !== 'action' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleReclassify(selectedMessage.id, 'action')}
                        className="text-red-600 text-xs h-7 px-2"
                        title="Mark as Action"
                      >
                        <Zap className="h-3 w-3 mr-1" />
                        Action
                      </Button>
                    )}
                    {selectedMessage.category !== 'skip' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleReclassify(selectedMessage.id, 'skip')}
                        className="text-gray-400 text-xs h-7 px-2"
                        title="Mark as Skip"
                      >
                        <EyeOff className="h-3 w-3 mr-1" />
                        Skip
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleMarkDone}
                      className="flex-none text-muted-foreground"
                    >
                      <X className="h-4 w-4 mr-1" />
                      Done
                    </Button>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground space-y-0.5">
                  <p>
                    <span className="font-medium text-foreground">
                      {selectedMessage.fromName}
                    </span>{' '}
                    &lt;{parseFromEmail(selectedMessage.from)}&gt;
                  </p>
                  <p>
                    To:{' '}
                    {selectedMessage.to.length > 60
                      ? selectedMessage.to.slice(0, 60) + '...'
                      : selectedMessage.to}
                  </p>
                  <p className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {selectedMessage.date}
                  </p>
                  {selectedMessage.categoryReason && (
                    <p className="text-xs italic">
                      Classification: {selectedMessage.categoryReason}
                    </p>
                  )}
                </div>
              </div>

              <Separator className="mb-6" />

              {/* Email body */}
              <div className="mb-8">
                {selectedState?.fullMessage ? (
                  <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed">
                    {selectedState.fullMessage.body}
                  </pre>
                ) : selectedState?.fetchError ? (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground italic">
                      {selectedMessage.snippet}
                    </p>
                    <p className="text-xs text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {selectedState.fetchError}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground italic">
                      {selectedMessage.snippet}
                    </p>
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  </div>
                )}
              </div>

              <Separator className="mb-6" />

              {/* Response section */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-sm uppercase tracking-wide text-muted-foreground">
                    Your Reply
                  </h3>
                  <div className="flex gap-2">
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
                </div>

                {/* Subject line */}
                <div className="mb-3">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">
                    Subject
                  </label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={selectedState?.draftSubject || `Re: ${selectedMessage.subject}`}
                    onChange={(e) =>
                      updateEmailState(selectedMessage.id, {
                        draftSubject: e.target.value,
                      })
                    }
                  />
                </div>

                {/* Draft body */}
                <textarea
                  className="w-full min-h-[200px] px-3 py-2 border rounded-md text-sm font-sans leading-relaxed focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                  placeholder={
                    selectedState?.status === 'drafting'
                      ? 'Generating draft in your style...'
                      : 'Click "Draft Response" to generate a reply, or type your own...'
                  }
                  value={selectedState?.draftBody || ''}
                  onChange={(e) =>
                    updateEmailState(selectedMessage.id, {
                      draftBody: e.target.value,
                      status:
                        selectedState?.status === 'pending'
                          ? 'draft_ready'
                          : selectedState?.status || 'draft_ready',
                    })
                  }
                  disabled={selectedState?.status === 'drafting'}
                />

                {/* Action buttons */}
                <div className="flex items-center gap-3 mt-4">
                  <Button
                    onClick={() => handleGmailAction('draft')}
                    disabled={
                      !selectedState?.draftBody ||
                      selectedState?.status === 'sending' ||
                      selectedState?.status === 'drafting'
                    }
                    variant="outline"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    Save to Drafts
                  </Button>

                  {!confirmSend ? (
                    <Button
                      onClick={() => setConfirmSend(true)}
                      disabled={
                        !selectedState?.draftBody ||
                        selectedState?.status === 'sending' ||
                        selectedState?.status === 'drafting'
                      }
                    >
                      <Send className="h-4 w-4 mr-2" />
                      Send Reply
                    </Button>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-amber-600 font-medium">
                        Send to {parseFromEmail(selectedMessage.from)}?
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
                        Confirm Send
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setConfirmSend(false)}
                      >
                        Cancel
                      </Button>
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
      </div>
    </div>
  );
}
