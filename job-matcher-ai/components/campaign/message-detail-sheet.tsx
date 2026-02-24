'use client';

import { useState, useEffect, useCallback } from 'react';
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
  Building2,
  DollarSign,
  Loader2,
  Save,
  User,
  Check,
  BookOpen,
  Target,
  Heart,
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

  const isListA = contact?.campaign_2026?.scaffold?.campaign_list === 'A';
  const scaffold = contact?.campaign_2026?.scaffold;
  const lifecycle = scaffold?.lifecycle_stage;

  const handleSave = async () => {
    if (!contact) return;
    setSaving(true);

    try {
      // Build list of changed fields to PATCH
      const patches: Array<{ section: string; field: string; value: string }> = [];

      if (isListA) {
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

            <div className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden">
              <div className="px-6 pb-6 space-y-5 min-w-0 max-w-full">
                {/* Scaffold summary */}
                <div className="flex flex-wrap gap-1.5">
                  <Badge variant="outline" className="text-[10px]">
                    List {scaffold?.campaign_list || '?'}
                  </Badge>
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
                {isListA ? (
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
                        }}
                        className="min-h-[200px] text-sm"
                        rows={8}
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Follow-Up Text</label>
                      <Textarea
                        value={followUpText}
                        onChange={(e) => {
                          setFollowUpText(e.target.value);
                          markDirty();
                        }}
                        className="text-sm"
                        rows={3}
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Thank-You Message</label>
                      <Textarea
                        value={thankYouMessage}
                        onChange={(e) => {
                          setThankYouMessage(e.target.value);
                          markDirty();
                        }}
                        className="text-sm"
                        rows={3}
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Internal Notes</label>
                      <Textarea
                        value={internalNotes}
                        onChange={(e) => {
                          setInternalNotes(e.target.value);
                          markDirty();
                        }}
                        className="text-sm"
                        rows={3}
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
                          }}
                          className="text-sm"
                          rows={3}
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
                        }}
                        className="text-sm"
                        rows={2}
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Text Follow-Up Milestone</label>
                      <Textarea
                        value={textFollowupMilestone}
                        onChange={(e) => {
                          setTextFollowupMilestone(e.target.value);
                          markDirty();
                        }}
                        className="text-sm"
                        rows={2}
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium mb-1.5 block">Thank-You Message</label>
                      <Textarea
                        value={bcdThankYou}
                        onChange={(e) => {
                          setBcdThankYou(e.target.value);
                          markDirty();
                        }}
                        className="text-sm"
                        rows={3}
                      />
                    </div>
                  </div>
                )}

                {/* Save button */}
                <div className="flex justify-end pt-2">
                  <Button
                    onClick={handleSave}
                    disabled={saving || !dirty}
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
