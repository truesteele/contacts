'use client';

import { useState, useCallback } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Loader2,
  Send,
  SendHorizonal,
  Sparkles,
  ChevronDown,
  ChevronRight,
  Check,
  AlertCircle,
  Mail,
  User,
  Building2,
} from 'lucide-react';
import { NetworkContact } from '@/lib/supabase';

type Tone = 'warm_professional' | 'formal' | 'casual' | 'networking' | 'fundraising';

const TONE_OPTIONS: { value: Tone; label: string; description: string }[] = [
  { value: 'warm_professional', label: 'Warm Professional', description: 'Friendly yet credible' },
  { value: 'formal', label: 'Formal', description: 'Polished, for executives' },
  { value: 'casual', label: 'Casual', description: 'Relaxed and friendly' },
  { value: 'networking', label: 'Networking', description: 'Relationship-building' },
  { value: 'fundraising', label: 'Fundraising', description: 'Mission-driven ask' },
];

interface Draft {
  id: string;
  contact_id: number;
  contact_name: string;
  contact_email: string;
  contact_company: string | null;
  subject: string;
  body: string;
  tone: string;
  status: 'draft' | 'sent' | 'failed';
}

interface OutreachDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  contacts: NetworkContact[];
  listId?: string;
}

export function OutreachDrawer({
  open,
  onOpenChange,
  contacts,
  listId,
}: OutreachDrawerProps) {
  const [tone, setTone] = useState<Tone>('warm_professional');
  const [context, setContext] = useState('');
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState('');
  const [expandedDraftId, setExpandedDraftId] = useState<string | null>(null);
  const [sendingIds, setSendingIds] = useState<Set<string>>(new Set());
  const [sendingAll, setSendingAll] = useState(false);

  const contactIds = contacts.map((c) => parseInt(String(c.id), 10));

  const handleGenerateDrafts = useCallback(async () => {
    setGenerating(true);
    setGenerateError('');
    setDrafts([]);

    try {
      const res = await fetch('/api/network-intel/outreach/draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          list_id: listId || undefined,
          contact_ids: contactIds,
          context: context.trim() || undefined,
          tone,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `Draft generation failed (${res.status})`);
      }

      const data = await res.json();
      setDrafts(data.drafts || []);

      if (data.errors?.length > 0) {
        const errorNames = data.errors.map((e: any) => e.name || `Contact #${e.contact_id}`).join(', ');
        setGenerateError(`Some drafts skipped: ${errorNames}`);
      }

      if (data.drafts?.length > 0) {
        setExpandedDraftId(data.drafts[0].id);
      }
    } catch (err: any) {
      setGenerateError(err.message || 'Failed to generate drafts');
    } finally {
      setGenerating(false);
    }
  }, [contactIds, context, tone, listId]);

  const handleSendDraft = useCallback(async (draftId: string) => {
    setSendingIds((prev) => new Set(prev).add(draftId));

    const draft = drafts.find((d) => d.id === draftId);
    try {
      const res = await fetch('/api/network-intel/outreach/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          draft_id: draftId,
          overrides: draft
            ? { [draftId]: { subject: draft.subject, body: draft.body } }
            : undefined,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || 'Send failed');
      }

      const data = await res.json();
      const result = data.results?.[0];

      setDrafts((prev) =>
        prev.map((d) =>
          d.id === draftId
            ? { ...d, status: result?.status === 'sent' ? 'sent' : 'failed' }
            : d
        )
      );
    } catch {
      setDrafts((prev) =>
        prev.map((d) => (d.id === draftId ? { ...d, status: 'failed' } : d))
      );
    } finally {
      setSendingIds((prev) => {
        const next = new Set(prev);
        next.delete(draftId);
        return next;
      });
    }
  }, [drafts]);

  const handleSendAll = useCallback(async () => {
    const unsent = drafts.filter((d) => d.status === 'draft');
    if (unsent.length === 0) return;

    setSendingAll(true);

    try {
      const overrides: Record<string, { subject: string; body: string }> = {};
      for (const d of unsent) {
        overrides[d.id] = { subject: d.subject, body: d.body };
      }

      const res = await fetch('/api/network-intel/outreach/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ draft_ids: unsent.map((d) => d.id), overrides }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || 'Send failed');
      }

      const data = await res.json();
      const resultMap = new Map<string, string>();
      for (const r of data.results || []) {
        resultMap.set(r.draft_id, r.status);
      }

      setDrafts((prev) =>
        prev.map((d) => {
          const newStatus = resultMap.get(d.id);
          if (newStatus === 'sent' || newStatus === 'failed') {
            return { ...d, status: newStatus };
          }
          return d;
        })
      );
    } catch {
      // Mark all unsent as failed on network error
      setDrafts((prev) =>
        prev.map((d) => (d.status === 'draft' ? { ...d, status: 'failed' } : d))
      );
    } finally {
      setSendingAll(false);
    }
  }, [drafts]);

  const handleUpdateDraft = useCallback((draftId: string, field: 'subject' | 'body', value: string) => {
    setDrafts((prev) =>
      prev.map((d) => (d.id === draftId ? { ...d, [field]: value } : d))
    );
  }, []);

  const unsentCount = drafts.filter((d) => d.status === 'draft').length;
  const sentCount = drafts.filter((d) => d.status === 'sent').length;
  const hasDrafts = drafts.length > 0;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl p-0 flex flex-col"
      >
        <SheetHeader className="px-6 pt-6 pb-4 space-y-1 shrink-0">
          <SheetTitle className="text-lg flex items-center gap-2">
            <Mail className="w-5 h-5" />
            Draft Outreach
          </SheetTitle>
          <SheetDescription>
            {contacts.length} {contacts.length === 1 ? 'contact' : 'contacts'} selected
            {hasDrafts && sentCount > 0 && (
              <span className="ml-2 text-green-600 dark:text-green-400">
                — {sentCount} sent
              </span>
            )}
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="flex-1">
          <div className="px-6 pb-6 space-y-5">
            {/* Configuration section — only show before drafts are generated */}
            {!hasDrafts && (
              <>
                {/* Contact preview */}
                <div className="space-y-2">
                  <div className="text-sm font-medium">Recipients</div>
                  <div className="flex flex-wrap gap-1.5">
                    {contacts.slice(0, 12).map((c) => (
                      <Badge
                        key={String(c.id)}
                        variant="secondary"
                        className="text-xs gap-1"
                      >
                        <User className="w-3 h-3" />
                        {c.first_name} {c.last_name}
                      </Badge>
                    ))}
                    {contacts.length > 12 && (
                      <Badge variant="outline" className="text-xs">
                        +{contacts.length - 12} more
                      </Badge>
                    )}
                  </div>
                </div>

                <Separator />

                {/* Tone selector */}
                <div className="space-y-2">
                  <div className="text-sm font-medium">Tone</div>
                  <Select value={tone} onValueChange={(v) => setTone(v as Tone)}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TONE_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          <span className="flex items-center gap-2">
                            <span className="font-medium">{opt.label}</span>
                            <span className="text-muted-foreground text-xs">
                              — {opt.description}
                            </span>
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Context textarea */}
                <div className="space-y-2">
                  <div className="text-sm font-medium">
                    Additional Context{' '}
                    <span className="text-muted-foreground font-normal">(optional)</span>
                  </div>
                  <Textarea
                    placeholder="e.g., Mention the upcoming Outdoorithm gala on March 15th..."
                    value={context}
                    onChange={(e) => setContext(e.target.value)}
                    rows={3}
                    className="resize-none text-sm"
                  />
                </div>

                {/* No email warning */}
                {contacts.length > 0 && contacts.every((c) => !c.email) && (
                  <div className="flex items-start gap-2 rounded-lg border border-amber-500/50 bg-amber-50 dark:bg-amber-900/10 p-3 text-xs">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                    <span className="text-amber-700 dark:text-amber-300">
                      None of the selected contacts have email addresses. Drafts will be generated but cannot be sent.
                    </span>
                  </div>
                )}

                {/* Generate button */}
                <Button
                  onClick={handleGenerateDrafts}
                  disabled={generating || contacts.length === 0}
                  className="w-full gap-2"
                >
                  {generating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Generating {contacts.length} {contacts.length === 1 ? 'draft' : 'drafts'}...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Generate Drafts
                    </>
                  )}
                </Button>

                {generateError && (
                  <div className="flex items-start gap-2 rounded-lg border border-destructive/50 bg-destructive/5 p-3 text-sm">
                    <AlertCircle className="w-4 h-4 text-destructive shrink-0 mt-0.5" />
                    <span className="text-destructive">{generateError}</span>
                  </div>
                )}
              </>
            )}

            {/* Drafts list */}
            {hasDrafts && (
              <>
                {/* Summary + Send All */}
                <div className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    {drafts.length} {drafts.length === 1 ? 'draft' : 'drafts'} generated
                    {sentCount > 0 && (
                      <span className="text-green-600 dark:text-green-400 ml-1">
                        ({sentCount} sent)
                      </span>
                    )}
                  </div>
                  {unsentCount > 0 && (
                    <Button
                      size="sm"
                      onClick={handleSendAll}
                      disabled={sendingAll || sendingIds.size > 0}
                      className="gap-1.5"
                    >
                      {sendingAll ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Sending...
                        </>
                      ) : (
                        <>
                          <SendHorizonal className="w-3.5 h-3.5" />
                          Send All ({unsentCount})
                        </>
                      )}
                    </Button>
                  )}
                </div>

                {generateError && (
                  <div className="flex items-start gap-2 rounded-lg border border-amber-500/50 bg-amber-50 dark:bg-amber-900/10 p-2.5 text-xs">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                    <span className="text-amber-700 dark:text-amber-300">{generateError}</span>
                  </div>
                )}

                <Separator />

                {/* Individual drafts */}
                <div className="space-y-2">
                  {drafts.map((draft) => {
                    const isExpanded = expandedDraftId === draft.id;
                    const isSending = sendingIds.has(draft.id);
                    const isSent = draft.status === 'sent';
                    const isFailed = draft.status === 'failed';

                    return (
                      <div
                        key={draft.id}
                        className={`rounded-lg border transition-colors ${
                          isSent
                            ? 'border-green-200 bg-green-50/50 dark:border-green-900 dark:bg-green-950/20'
                            : isFailed
                              ? 'border-red-200 bg-red-50/50 dark:border-red-900 dark:bg-red-950/20'
                              : 'border-border'
                        }`}
                      >
                        {/* Draft header — always visible */}
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedDraftId(isExpanded ? null : draft.id)
                          }
                          className="flex items-center gap-3 w-full px-3 py-2.5 text-left hover:bg-muted/50 rounded-lg transition-colors"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
                          )}

                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium truncate">
                                {draft.contact_name}
                              </span>
                              {draft.contact_company && (
                                <span className="text-xs text-muted-foreground flex items-center gap-1 shrink-0">
                                  <Building2 className="w-3 h-3" />
                                  {draft.contact_company}
                                </span>
                              )}
                            </div>
                            <div className="text-xs text-muted-foreground truncate mt-0.5">
                              {draft.subject}
                            </div>
                          </div>

                          {/* Status badge */}
                          {isSent && (
                            <Badge className="bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300 text-[10px] shrink-0">
                              <Check className="w-3 h-3 mr-0.5" />
                              Sent
                            </Badge>
                          )}
                          {isFailed && (
                            <Badge className="bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300 text-[10px] shrink-0">
                              <AlertCircle className="w-3 h-3 mr-0.5" />
                              Failed
                            </Badge>
                          )}
                          {isSending && (
                            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground shrink-0" />
                          )}
                        </button>

                        {/* Expanded draft editor */}
                        {isExpanded && (
                          <div className="px-3 pb-3 space-y-3 border-t">
                            <div className="pt-3 space-y-2">
                              <div className="text-xs font-medium text-muted-foreground">
                                To: {draft.contact_email}
                              </div>

                              {/* Subject */}
                              <div className="space-y-1">
                                <label className="text-xs font-medium text-muted-foreground">
                                  Subject
                                </label>
                                <input
                                  type="text"
                                  value={draft.subject}
                                  onChange={(e) =>
                                    handleUpdateDraft(draft.id, 'subject', e.target.value)
                                  }
                                  disabled={isSent}
                                  className="w-full rounded-md border border-input bg-transparent px-3 py-1.5 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
                                />
                              </div>

                              {/* Body */}
                              <div className="space-y-1">
                                <label className="text-xs font-medium text-muted-foreground">
                                  Body
                                </label>
                                <Textarea
                                  value={draft.body}
                                  onChange={(e) =>
                                    handleUpdateDraft(draft.id, 'body', e.target.value)
                                  }
                                  disabled={isSent}
                                  rows={10}
                                  className="text-sm resize-none leading-relaxed"
                                />
                              </div>
                            </div>

                            {/* Actions */}
                            {!isSent && (
                              <div className="flex justify-end">
                                <Button
                                  size="sm"
                                  onClick={() => handleSendDraft(draft.id)}
                                  disabled={isSending || sendingAll}
                                  className="gap-1.5"
                                >
                                  {isSending ? (
                                    <>
                                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                      Sending...
                                    </>
                                  ) : (
                                    <>
                                      <Send className="w-3.5 h-3.5" />
                                      Send
                                    </>
                                  )}
                                </Button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Regenerate option */}
                <Separator />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setDrafts([]);
                    setExpandedDraftId(null);
                    setGenerateError('');
                  }}
                  className="w-full gap-1.5 text-muted-foreground"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Start Over
                </Button>
              </>
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
