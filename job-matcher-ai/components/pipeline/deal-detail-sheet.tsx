'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
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
  Calendar,
  Clock,
  DollarSign,
  ExternalLink,
  Save,
  User,
} from 'lucide-react';
import { type Deal } from './deal-card';

interface StageConfig {
  name: string;
  color: string;
}

interface DealDetailSheetProps {
  deal: Deal | null;
  open: boolean;
  stages: StageConfig[];
  onOpenChange: (open: boolean) => void;
  onDealUpdated: (deal: Deal) => void;
  onViewContact: (contactId: number) => void;
}

function stageKey(name: string): string {
  return name.toLowerCase().replace(/\s+/g, '_');
}

function daysInStage(updatedAt: string): number {
  const updated = new Date(updatedAt);
  const now = new Date();
  return Math.floor((now.getTime() - updated.getTime()) / (1000 * 60 * 60 * 24));
}

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function DealDetailSheet({
  deal,
  open,
  stages,
  onOpenChange,
  onDealUpdated,
  onViewContact,
}: DealDetailSheetProps) {
  const [title, setTitle] = useState('');
  const [stage, setStage] = useState('');
  const [amount, setAmount] = useState('');
  const [closeDate, setCloseDate] = useState('');
  const [notes, setNotes] = useState('');
  const [nextAction, setNextAction] = useState('');
  const [nextActionDate, setNextActionDate] = useState('');
  const [source, setSource] = useState('');
  const [lostReason, setLostReason] = useState('');
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  // Populate form when deal changes
  useEffect(() => {
    if (deal) {
      setTitle(deal.title || '');
      setStage(deal.stage || '');
      setAmount(deal.amount != null ? String(deal.amount) : '');
      setCloseDate(deal.close_date || '');
      setNotes(deal.notes || '');
      setNextAction(deal.next_action || '');
      setNextActionDate(deal.next_action_date || '');
      setSource(deal.source || '');
      setLostReason(deal.lost_reason || '');
      setDirty(false);
    }
  }, [deal]);

  const markDirty = useCallback(() => setDirty(true), []);

  const handleSave = async () => {
    if (!deal) return;
    setSaving(true);

    try {
      const body: Record<string, unknown> = {
        title: title.trim(),
        stage,
        amount: amount ? parseFloat(amount) : null,
        close_date: closeDate || null,
        notes: notes.trim() || null,
        next_action: nextAction.trim() || null,
        next_action_date: nextActionDate || null,
        source: source.trim() || null,
        lost_reason: lostReason.trim() || null,
      };

      const res = await fetch(`/api/network-intel/pipeline/deals/${deal.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error('Failed to update deal');

      const data = await res.json();
      onDealUpdated(data.deal);
      setDirty(false);
    } catch (err) {
      console.error('Failed to save deal:', err);
    } finally {
      setSaving(false);
    }
  };

  if (!deal) return null;

  const days = daysInStage(deal.updated_at);
  const contactName = deal.contacts
    ? `${deal.contacts.first_name} ${deal.contacts.last_name}`
    : null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-lg p-0 flex flex-col overflow-hidden min-w-0"
      >
        <SheetHeader className="px-6 pt-6 pb-4 space-y-1 min-w-0">
          <SheetTitle className="text-xl">{deal.title}</SheetTitle>
          {contactName && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <User className="w-4 h-4 shrink-0" />
              <span>{contactName}</span>
              {deal.contacts?.company && (
                <>
                  <Building2 className="w-3.5 h-3.5 shrink-0" />
                  <span>{deal.contacts.company}</span>
                </>
              )}
            </div>
          )}
        </SheetHeader>

        <div className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden">
          <div className="px-6 pb-6 space-y-5 min-w-0 max-w-full">
            {/* Meta info */}
            <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
              <div className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                Created {formatTimestamp(deal.created_at)}
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                Updated {formatTimestamp(deal.updated_at)}
              </div>
              <Badge variant="outline" className="text-[10px]">
                {days === 0 ? 'Moved today' : `${days}d in stage`}
              </Badge>
            </div>

            {/* Contact link */}
            {deal.contacts && deal.contact_id && (
              <>
                <div>
                  <label className="text-sm font-medium mb-1.5 block">Contact</label>
                  <button
                    onClick={() => onViewContact(deal.contact_id!)}
                    className="flex items-center gap-2 px-3 py-2 rounded-md border bg-muted/30 hover:bg-muted/50 transition-colors w-full text-left"
                  >
                    <User className="w-4 h-4 text-muted-foreground shrink-0" />
                    <span className="text-sm font-medium">{contactName}</span>
                    {deal.contacts.company && (
                      <span className="text-xs text-muted-foreground">
                        at {deal.contacts.company}
                      </span>
                    )}
                    <ExternalLink className="w-3.5 h-3.5 text-muted-foreground ml-auto shrink-0" />
                  </button>
                </div>
                <Separator />
              </>
            )}

            {/* Title */}
            <div>
              <label className="text-sm font-medium mb-1.5 block">Title</label>
              <Input
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  markDirty();
                }}
              />
            </div>

            {/* Stage */}
            <div>
              <label className="text-sm font-medium mb-1.5 block">Stage</label>
              <Select
                value={stage}
                onValueChange={(v) => {
                  setStage(v);
                  markDirty();
                }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {stages.map((s) => {
                    const key = stageKey(s.name);
                    return (
                      <SelectItem key={key} value={key}>
                        <div className="flex items-center gap-2">
                          <div
                            className="w-2 h-2 rounded-full shrink-0"
                            style={{ backgroundColor: s.color }}
                          />
                          {s.name}
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>

            {/* Amount + Close Date */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium mb-1.5 block">
                  <DollarSign className="w-3.5 h-3.5 inline mr-1" />
                  Amount
                </label>
                <Input
                  type="number"
                  placeholder="0"
                  value={amount}
                  onChange={(e) => {
                    setAmount(e.target.value);
                    markDirty();
                  }}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Close Date</label>
                <Input
                  type="date"
                  value={closeDate}
                  onChange={(e) => {
                    setCloseDate(e.target.value);
                    markDirty();
                  }}
                />
              </div>
            </div>

            {/* Source */}
            <div>
              <label className="text-sm font-medium mb-1.5 block">Source</label>
              <Input
                placeholder="e.g. LinkedIn, Referral, Conference..."
                value={source}
                onChange={(e) => {
                  setSource(e.target.value);
                  markDirty();
                }}
              />
            </div>

            {/* Next Action + Date */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Next Action</label>
                <Input
                  placeholder="e.g. Send proposal"
                  value={nextAction}
                  onChange={(e) => {
                    setNextAction(e.target.value);
                    markDirty();
                  }}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Action Date</label>
                <Input
                  type="date"
                  value={nextActionDate}
                  onChange={(e) => {
                    setNextActionDate(e.target.value);
                    markDirty();
                  }}
                />
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="text-sm font-medium mb-1.5 block">Notes</label>
              <Textarea
                placeholder="Any context or notes about this deal..."
                value={notes}
                onChange={(e) => {
                  setNotes(e.target.value);
                  markDirty();
                }}
                rows={4}
              />
            </div>

            {/* Lost Reason (only visible when stage is lost) */}
            {stage === 'lost' && (
              <div>
                <label className="text-sm font-medium mb-1.5 block">Lost Reason</label>
                <Input
                  placeholder="Why was this deal lost?"
                  value={lostReason}
                  onChange={(e) => {
                    setLostReason(e.target.value);
                    markDirty();
                  }}
                />
              </div>
            )}

            {/* Save button */}
            <div className="flex justify-end pt-2">
              <Button
                onClick={handleSave}
                disabled={saving || !dirty || !title.trim()}
                className="gap-1.5"
              >
                <Save className="w-3.5 h-3.5" />
                {saving ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
