'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Building2,
  DollarSign,
  Loader2,
  Save,
  User,
  Check,
  BookOpen,
  Target,
  Heart,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ── Types ──────────────────────────────────────────────────────────────

interface Scaffold {
  persona?: string;
  persona_confidence?: number;
  campaign_list?: string;
  capacity_tier?: string;
  primary_ask_amount?: number;
  motivation_flags?: string[];
  primary_motivation?: string;
  lifecycle_stage?: string;
  lead_story?: string;
  opener_insert?: string;
  personalization_sentence?: string;
  thank_you_variant?: string;
  text_followup?: string;
}

interface PersonalOutreach {
  subject_line?: string;
  message_body?: string;
  channel?: string;
  follow_up_text?: string;
  thank_you_message?: string;
  internal_notes?: string;
}

interface CampaignCopy {
  pre_email_note?: string;
  text_followup_opener?: string;
  text_followup_milestone?: string;
  thank_you_message?: string;
  thank_you_channel?: string;
  email_sequence?: number[];
}

interface Campaign2026 {
  scaffold?: Scaffold;
  personal_outreach?: PersonalOutreach;
  campaign_copy?: CampaignCopy;
  send_status?: Record<string, { sent_at: string; resend_id: string }>;
  donation?: { amount: number; donated_at: string; source: string } | null;
  responded_at?: string | null;
  sidelined?: { reason: string; sidelined_at: string; original_list: string } | null;
}

interface ContactFull {
  id: number;
  first_name: string;
  last_name: string;
  company: string | null;
  position: string | null;
  email: string | null;
  personal_email: string | null;
  work_email: string | null;
  campaign_2026: Campaign2026 | null;
}

interface MessageDetailSheetProps {
  contactId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpdated: () => void;
}

// ── Label maps ─────────────────────────────────────────────────────────

const PERSONA_LABELS: Record<string, string> = {
  believer: 'Believer',
  impact_professional: 'Impact Pro',
  network_peer: 'Network Peer',
};

const CAPACITY_LABELS: Record<string, string> = {
  leadership: 'Leadership',
  major: 'Major',
  mid: 'Mid',
  base: 'Base',
  community: 'Community',
};

const LIFECYCLE_LABELS: Record<string, string> = {
  new: 'New',
  prior_donor: 'Prior Donor',
  lapsed: 'Lapsed',
};

const LIST_OPTIONS = [
  { value: 'A', label: 'List A' },
  { value: 'B', label: 'List B' },
  { value: 'C', label: 'List C' },
  { value: 'D', label: 'List D' },
  { value: 'sidelined', label: 'Sidelined' },
];

// ── Auto-resize helper ────────────────────────────────────────────────

function autoResize(el: HTMLTextAreaElement | null) {
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = el.scrollHeight + 'px';
}

// ── Component ──────────────────────────────────────────────────────────

export function MessageDetailSheet({
  contactId,
  open,
  onOpenChange,
  onUpdated,
}: MessageDetailSheetProps) {
  const [contact, setContact] = useState<ContactFull | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [dirty, setDirty] = useState(false);

  // List / sideline state
  const [selectedList, setSelectedList] = useState('');
  const [sidelineReason, setSidelineReason] = useState('');

  // List A editable fields
  const [subjectLine, setSubjectLine] = useState('');
  const [messageBody, setMessageBody] = useState('');
  const [followUpText, setFollowUpText] = useState('');
  const [thankYouMessage, setThankYouMessage] = useState('');
  const [internalNotes, setInternalNotes] = useState('');

  // Lists B-D editable fields
  const [preEmailNote, setPreEmailNote] = useState('');
  const [textFollowupOpener, setTextFollowupOpener] = useState('');
  const [textFollowupMilestone, setTextFollowupMilestone] = useState('');
  const [bcdThankYou, setBcdThankYou] = useState('');

  // Track original values for dirty checking per field
  const [originals, setOriginals] = useState<Record<string, string>>({});

  // Ref for auto-resize after data loads
  const contentRef = useRef<HTMLDivElement>(null);

  const fetchContact = useCallback(async (id: number) => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`/api/network-intel/campaign/${id}`);
      if (!res.ok) throw new Error('Failed to fetch contact');
      const data = await res.json();
      const c: ContactFull = data.contact;
      setContact(c);

      const campaign = c.campaign_2026;
      const po = campaign?.personal_outreach;
      const cc = campaign?.campaign_copy;
      const scaf = campaign?.scaffold;

      // Populate list / sideline
      setSelectedList(scaf?.campaign_list || '');
      setSidelineReason(campaign?.sidelined?.reason || '');

      // Populate List A fields
      setSubjectLine(po?.subject_line || '');
      setMessageBody(po?.message_body || '');
      setFollowUpText(po?.follow_up_text || '');
      setThankYouMessage(po?.thank_you_message || '');
      setInternalNotes(po?.internal_notes || '');

      // Populate Lists B-D fields
      setPreEmailNote(cc?.pre_email_note || '');
      setTextFollowupOpener(cc?.text_followup_opener || '');
      setTextFollowupMilestone(cc?.text_followup_milestone || '');
      setBcdThankYou(cc?.thank_you_message || '');

      // Store originals for dirty checking
      setOriginals({
        campaign_list: scaf?.campaign_list || '',
        sideline_reason: campaign?.sidelined?.reason || '',
        subject_line: po?.subject_line || '',
        message_body: po?.message_body || '',
        follow_up_text: po?.follow_up_text || '',
        thank_you_message: po?.thank_you_message || '',
        internal_notes: po?.internal_notes || '',
        pre_email_note: cc?.pre_email_note || '',
        text_followup_opener: cc?.text_followup_opener || '',
        text_followup_milestone: cc?.text_followup_milestone || '',
        bcd_thank_you: cc?.thank_you_message || '',
      });
      setDirty(false);
      setSaved(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-resize all textareas after data loads
  useEffect(() => {
    if (!loading && contact && contentRef.current) {
      // Small delay to let React render the values into the textareas
      const timer = setTimeout(() => {
        const textareas = contentRef.current?.querySelectorAll('textarea');
        textareas?.forEach((ta) => autoResize(ta));
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [loading, contact]);

  useEffect(() => {
    if (open && contactId) {
      fetchContact(contactId);
    }
    if (!open) {
      setContact(null);
      setDirty(false);
      setSaved(false);
    }
  }, [open, contactId, fetchContact]);

  const markDirty = useCallback(() => {
    setDirty(true);
    setSaved(false);
  }, []);

  const currentList = selectedList;
  const isListA = currentList === 'A';
  const isSidelined = currentList === 'sidelined';
  const scaffold = contact?.campaign_2026?.scaffold;
  const lifecycle = scaffold?.lifecycle_stage;

  const handleSave = async () => {
    if (!contact) return;

    // Validate sideline reason
    if (isSidelined && !sidelineReason.trim()) {
      return; // Reason required
    }

    setSaving(true);

    try {
      // Build list of patches to send
      const patches: Array<{ section: string; field?: string; value: unknown }> = [];

      // Handle list change
      const listChanged = selectedList !== originals.campaign_list;
      if (listChanged) {
        // Update scaffold.campaign_list
        patches.push({ section: 'scaffold', field: 'campaign_list', value: selectedList });

        if (isSidelined) {
          // Moving TO sidelined: store reason + original list
          patches.push({
            section: 'sidelined',
            value: {
              reason: sidelineReason.trim(),
              sidelined_at: new Date().toISOString(),
              original_list: originals.campaign_list,
            },
          });
        } else if (originals.campaign_list === 'sidelined') {
          // Moving FROM sidelined: clear sideline data
          patches.push({ section: 'sidelined', value: null });
        }
      } else if (isSidelined && sidelineReason !== originals.sideline_reason) {
        // Reason changed but list didn't
        patches.push({
          section: 'sidelined',
          value: {
            reason: sidelineReason.trim(),
            sidelined_at: contact.campaign_2026?.sidelined?.sidelined_at || new Date().toISOString(),
            original_list: contact.campaign_2026?.sidelined?.original_list || originals.campaign_list,
          },
        });
      }

      // Handle content field changes (use original list to determine which fields to check)
      const origListIsA = originals.campaign_list === 'A';
      if (origListIsA) {
        if (subjectLine !== originals.subject_line)
          patches.push({ section: 'personal_outreach', field: 'subject_line', value: subjectLine });
        if (messageBody !== originals.message_body)
          patches.push({ section: 'personal_outreach', field: 'message_body', value: messageBody });
        if (followUpText !== originals.follow_up_text)
          patches.push({ section: 'personal_outreach', field: 'follow_up_text', value: followUpText });
        if (thankYouMessage !== originals.thank_you_message)
          patches.push({ section: 'personal_outreach', field: 'thank_you_message', value: thankYouMessage });
        if (internalNotes !== originals.internal_notes)
          patches.push({ section: 'personal_outreach', field: 'internal_notes', value: internalNotes });
      } else {
        if (preEmailNote !== originals.pre_email_note)
          patches.push({ section: 'campaign_copy', field: 'pre_email_note', value: preEmailNote });
        if (textFollowupOpener !== originals.text_followup_opener)
          patches.push({ section: 'campaign_copy', field: 'text_followup_opener', value: textFollowupOpener });
        if (textFollowupMilestone !== originals.text_followup_milestone)
          patches.push({ section: 'campaign_copy', field: 'text_followup_milestone', value: textFollowupMilestone });
        if (bcdThankYou !== originals.bcd_thank_you)
          patches.push({ section: 'campaign_copy', field: 'thank_you_message', value: bcdThankYou });
      }

      // Send patches sequentially
      for (const patch of patches) {
        const res = await fetch(`/api/network-intel/campaign/${contact.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch),
        });
        if (!res.ok) throw new Error('Failed to save changes');
      }

      // Update originals to match current values
      setOriginals({
        campaign_list: selectedList,
        sideline_reason: sidelineReason,
        subject_line: subjectLine,
        message_body: messageBody,
        follow_up_text: followUpText,
        thank_you_message: thankYouMessage,
        internal_notes: internalNotes,
        pre_email_note: preEmailNote,
        text_followup_opener: textFollowupOpener,
        text_followup_milestone: textFollowupMilestone,
        bcd_thank_you: bcdThankYou,
      });
      setDirty(false);
      setSaved(true);
      onUpdated();

      // Clear saved indicator after a moment
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error('Failed to save:', err);
    } finally {
      setSaving(false);
    }
  };

  const resolvedEmail = contact
    ? contact.personal_email || contact.email || contact.work_email || null
    : null;

  // Show content fields based on original list (not selected list, so fields don't disappear mid-edit)
  const showListAFields = originals.campaign_list === 'A';

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl p-0 flex flex-col overflow-hidden min-w-0"
      >
        {loading ? (
          <>
            <SheetHeader className="px-6 pt-6 pb-4">
              <SheetTitle>Loading...</SheetTitle>
              <SheetDescription>Fetching contact details</SheetDescription>
            </SheetHeader>
            <div className="flex items-center justify-center h-48">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          </>
        ) : error ? (
          <>
            <SheetHeader className="px-6 pt-6 pb-4">
              <SheetTitle>Error</SheetTitle>
              <SheetDescription>{error}</SheetDescription>
            </SheetHeader>
          </>
        ) : contact ? (
          <>
            <SheetHeader className="px-6 pt-6 pb-4 space-y-1 min-w-0">
              <SheetTitle className="text-xl">
                {contact.first_name} {contact.last_name}
              </SheetTitle>
              <SheetDescription className="flex items-center gap-3 text-sm">
                {contact.company && (
                  <span className="flex items-center gap-1">
                    <Building2 className="w-3.5 h-3.5" />
                    {contact.company}
                  </span>
                )}
                {resolvedEmail && (
                  <span className="font-mono text-xs">{resolvedEmail}</span>
                )}
              </SheetDescription>
            </SheetHeader>

            <div className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden" ref={contentRef}>
              <div className="px-6 pb-6 space-y-5 min-w-0 max-w-full">
                {/* Scaffold summary with list selector */}
                <div className="flex flex-wrap gap-1.5 items-center">
                  <Select
                    value={selectedList}
                    onValueChange={(val) => {
                      setSelectedList(val);
                      if (val !== 'sidelined') setSidelineReason('');
                      markDirty();
                    }}
                  >
                    <SelectTrigger className="h-6 w-[110px] text-[10px] font-medium border rounded-full px-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {LIST_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value} className="text-xs">
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Badge variant="outline" className="text-[10px]">
                    {PERSONA_LABELS[scaffold?.persona || ''] || scaffold?.persona || '—'}
                  </Badge>
                  <Badge variant="outline" className="text-[10px]">
                    <DollarSign className="w-3 h-3 mr-0.5" />
                    {scaffold?.primary_ask_amount?.toLocaleString() || '—'}
                  </Badge>
                  <Badge variant="outline" className="text-[10px]">
                    {CAPACITY_LABELS[scaffold?.capacity_tier || ''] || scaffold?.capacity_tier || '—'}
                  </Badge>
                  <Badge variant="outline" className="text-[10px]">
                    {LIFECYCLE_LABELS[scaffold?.lifecycle_stage || ''] || scaffold?.lifecycle_stage || '—'}
                  </Badge>
                </div>

                {/* Sideline reason (when sidelined is selected) */}
                {isSidelined && (
                  <div className="rounded-md border border-yellow-200 bg-yellow-50 dark:bg-yellow-950/20 dark:border-yellow-800 p-3 space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-medium text-yellow-800 dark:text-yellow-200">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Sidelined from campaign
                    </div>
                    <Textarea
                      value={sidelineReason}
                      onChange={(e) => {
                        setSidelineReason(e.target.value);
                        markDirty();
                        autoResize(e.target);
                      }}
                      placeholder="Reason for sidelining (required)..."
                      className="text-sm min-h-[40px] bg-white dark:bg-background"
                    />
                  </div>
                )}

                {/* Motivation + Story */}
                <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                  {scaffold?.primary_motivation && (
                    <span className="flex items-center gap-1">
                      <Heart className="w-3 h-3" />
                      {scaffold.primary_motivation.replace(/_/g, ' ')}
                    </span>
                  )}
                  {scaffold?.lead_story && (
                    <span className="flex items-center gap-1">
                      <BookOpen className="w-3 h-3" />
                      {scaffold.lead_story}
                    </span>
                  )}
                </div>

                <Separator />

                {/* ── List A: Personal Outreach Fields ── */}
                {showListAFields ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <User className="w-4 h-4 text-orange-600" />
                      <span className="text-sm font-medium">Personal Outreach</span>
                      {contact.campaign_2026?.personal_outreach?.channel && (
                        <Badge variant="outline" className="text-[10px] ml-auto">
                          {contact.campaign_2026.personal_outreach.channel}
                        </Badge>
                      )}
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Subject Line</label>
                      <Input
                        value={subjectLine}
                        onChange={(e) => {
                          setSubjectLine(e.target.value);
                          markDirty();
                        }}
                        placeholder="Email subject line"
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Message Body</label>
                      <Textarea
                        value={messageBody}
                        onChange={(e) => {
                          setMessageBody(e.target.value);
                          markDirty();
                          autoResize(e.target);
                        }}
                        className="min-h-[120px] text-sm resize-none overflow-hidden"
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Follow-Up Text</label>
                      <Textarea
                        value={followUpText}
                        onChange={(e) => {
                          setFollowUpText(e.target.value);
                          markDirty();
                          autoResize(e.target);
                        }}
                        className="min-h-[60px] text-sm resize-none overflow-hidden"
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Thank-You Message</label>
                      <Textarea
                        value={thankYouMessage}
                        onChange={(e) => {
                          setThankYouMessage(e.target.value);
                          markDirty();
                          autoResize(e.target);
                        }}
                        className="min-h-[60px] text-sm resize-none overflow-hidden"
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Internal Notes</label>
                      <Textarea
                        value={internalNotes}
                        onChange={(e) => {
                          setInternalNotes(e.target.value);
                          markDirty();
                          autoResize(e.target);
                        }}
                        className="min-h-[60px] text-sm resize-none overflow-hidden"
                        placeholder="Private notes about this contact..."
                      />
                    </div>
                  </div>
                ) : (
                  /* ── Lists B-D: Campaign Copy Fields ── */
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <Target className="w-4 h-4 text-blue-600" />
                      <span className="text-sm font-medium">Campaign Copy</span>
                      {contact.campaign_2026?.campaign_copy?.thank_you_channel && (
                        <Badge variant="outline" className="text-[10px] ml-auto">
                          {contact.campaign_2026.campaign_copy.thank_you_channel}
                        </Badge>
                      )}
                    </div>

                    {(lifecycle === 'prior_donor' || lifecycle === 'lapsed') && (
                      <div>
                        <label className="text-sm font-medium mb-1.5 block">Pre-Email Note</label>
                        <Textarea
                          value={preEmailNote}
                          onChange={(e) => {
                            setPreEmailNote(e.target.value);
                            markDirty();
                            autoResize(e.target);
                          }}
                          className="min-h-[60px] text-sm resize-none overflow-hidden"
                          placeholder="Personal note before the campaign email..."
                        />
                      </div>
                    )}

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Text Follow-Up Opener</label>
                      <Textarea
                        value={textFollowupOpener}
                        onChange={(e) => {
                          setTextFollowupOpener(e.target.value);
                          markDirty();
                          autoResize(e.target);
                        }}
                        className="min-h-[60px] text-sm resize-none overflow-hidden"
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Text Follow-Up Milestone</label>
                      <Textarea
                        value={textFollowupMilestone}
                        onChange={(e) => {
                          setTextFollowupMilestone(e.target.value);
                          markDirty();
                          autoResize(e.target);
                        }}
                        className="min-h-[60px] text-sm resize-none overflow-hidden"
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Thank-You Message</label>
                      <Textarea
                        value={bcdThankYou}
                        onChange={(e) => {
                          setBcdThankYou(e.target.value);
                          markDirty();
                          autoResize(e.target);
                        }}
                        className="min-h-[60px] text-sm resize-none overflow-hidden"
                      />
                    </div>
                  </div>
                )}

                {/* Save button */}
                <div className="flex justify-end pt-2">
                  <Button
                    onClick={handleSave}
                    disabled={saving || !dirty || (isSidelined && !sidelineReason.trim())}
                    className={cn(
                      'gap-1.5',
                      saved && 'bg-green-600 hover:bg-green-700'
                    )}
                  >
                    {saving ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : saved ? (
                      <Check className="w-3.5 h-3.5" />
                    ) : (
                      <Save className="w-3.5 h-3.5" />
                    )}
                    {saving ? 'Saving...' : saved ? 'Saved' : 'Save'}
                  </Button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <>
            <SheetHeader className="px-6 pt-6 pb-4">
              <SheetTitle>No Contact</SheetTitle>
              <SheetDescription>Select a contact to view details</SheetDescription>
            </SheetHeader>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
