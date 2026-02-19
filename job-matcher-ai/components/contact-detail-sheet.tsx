'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import {
  Building2,
  MapPin,
  Mail,
  Linkedin,
  Briefcase,
  GraduationCap,
  Users,
  MessageSquare,
  Lightbulb,
  Loader2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';

interface ContactDetail {
  id: number;
  first_name: string;
  last_name: string;
  company?: string;
  position?: string;
  headline?: string;
  summary?: string;
  city?: string;
  state?: string;
  email?: string;
  linkedin_url?: string;
  ai_proximity_score?: number;
  ai_proximity_tier?: string;
  ai_capacity_score?: number;
  ai_capacity_tier?: string;
  ai_kindora_prospect_score?: number;
  ai_kindora_prospect_type?: string;
  ai_outdoorithm_fit?: string;
  shared_employers: string[];
  shared_schools: string[];
  shared_boards: string[];
  topics: string[];
  primary_interests: string[];
  personalization_hooks: string[];
  suggested_opener: string;
  best_approach: string;
  talking_points: string[];
  kindora_rationale?: string;
}

interface ContactDetailSheetProps {
  contactId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const TIER_LABELS: Record<string, string> = {
  inner_circle: 'Inner Circle',
  close: 'Close',
  warm: 'Warm',
  familiar: 'Familiar',
  acquaintance: 'Acquaintance',
  distant: 'Distant',
  major_donor: 'Major Donor',
  mid_level: 'Mid-Level',
  grassroots: 'Grassroots',
  unknown: 'Unknown',
  enterprise_buyer: 'Enterprise Buyer',
  champion: 'Champion',
  influencer: 'Influencer',
  not_relevant: 'Not Relevant',
};

const PROXIMITY_COLORS: Record<string, string> = {
  inner_circle: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  close: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  warm: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  familiar: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  acquaintance: 'bg-slate-100 text-slate-700 dark:bg-slate-800/40 dark:text-slate-300',
  distant: 'bg-gray-100 text-gray-600 dark:bg-gray-800/40 dark:text-gray-400',
};

const CAPACITY_COLORS: Record<string, string> = {
  major_donor: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  mid_level: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  grassroots: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  unknown: 'bg-gray-100 text-gray-600 dark:bg-gray-800/40 dark:text-gray-400',
};

export function ContactDetailSheet({
  contactId,
  open,
  onOpenChange,
}: ContactDetailSheetProps) {
  const [detail, setDetail] = useState<ContactDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchDetail = useCallback(async (id: number) => {
    setLoading(true);
    setError('');
    setDetail(null);

    try {
      const res = await fetch(`/api/network-intel/contact/${id}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `Failed to load contact (${res.status})`);
      }
      const data = await res.json();
      setDetail(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load contact details');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open && contactId != null) {
      fetchDetail(contactId);
    }
    if (!open) {
      setDetail(null);
      setError('');
    }
  }, [open, contactId, fetchDetail]);

  const location = detail
    ? [detail.city, detail.state].filter(Boolean).join(', ')
    : '';

  const hasSharedContext =
    detail &&
    (detail.shared_employers.length > 0 ||
      detail.shared_schools.length > 0 ||
      detail.shared_boards.length > 0);

  const hasOutreach =
    detail &&
    (detail.personalization_hooks.length > 0 ||
      detail.suggested_opener ||
      detail.talking_points.length > 0);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-lg p-0 flex flex-col"
      >
        {loading && (
          <div className="flex-1 px-6 pt-6 space-y-5">
            {/* Skeleton header */}
            <div className="space-y-2">
              <div className="h-6 w-48 rounded bg-muted animate-pulse" />
              <div className="h-4 w-64 rounded bg-muted animate-pulse" />
            </div>
            {/* Skeleton info rows */}
            <div className="space-y-3">
              <div className="h-4 w-56 rounded bg-muted animate-pulse" />
              <div className="h-4 w-40 rounded bg-muted animate-pulse" />
              <div className="h-4 w-48 rounded bg-muted animate-pulse" />
            </div>
            {/* Skeleton score cards */}
            <div className="grid grid-cols-2 gap-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="rounded-lg border p-3 space-y-2">
                  <div className="h-3 w-16 rounded bg-muted animate-pulse" />
                  <div className="h-6 w-20 rounded bg-muted animate-pulse" />
                </div>
              ))}
            </div>
            {/* Skeleton sections */}
            <div className="space-y-3">
              <div className="h-4 w-32 rounded bg-muted animate-pulse" />
              <div className="flex gap-2">
                <div className="h-5 w-20 rounded-full bg-muted animate-pulse" />
                <div className="h-5 w-24 rounded-full bg-muted animate-pulse" />
                <div className="h-5 w-16 rounded-full bg-muted animate-pulse" />
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="text-center space-y-3">
              <AlertCircle className="w-8 h-8 text-destructive mx-auto" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-destructive">Failed to load contact</p>
                <p className="text-xs text-muted-foreground">{error}</p>
              </div>
              {contactId != null && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fetchDetail(contactId)}
                  className="gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Retry
                </Button>
              )}
            </div>
          </div>
        )}

        {detail && !loading && (
          <>
            {/* Header */}
            <SheetHeader className="px-6 pt-6 pb-4 space-y-1">
              <SheetTitle className="text-xl">
                {detail.first_name} {detail.last_name}
              </SheetTitle>
              {detail.headline && (
                <SheetDescription className="text-sm leading-snug">
                  {detail.headline}
                </SheetDescription>
              )}
            </SheetHeader>

            <ScrollArea className="flex-1">
              <div className="px-6 pb-6 space-y-5">
                {/* Basic Info */}
                <div className="space-y-2">
                  {detail.company && (
                    <div className="flex items-center gap-2 text-sm">
                      <Building2 className="w-4 h-4 text-muted-foreground shrink-0" />
                      <span>
                        {detail.position
                          ? `${detail.position} at ${detail.company}`
                          : detail.company}
                      </span>
                    </div>
                  )}
                  {location && (
                    <div className="flex items-center gap-2 text-sm">
                      <MapPin className="w-4 h-4 text-muted-foreground shrink-0" />
                      <span>{location}</span>
                    </div>
                  )}
                  {detail.email && (
                    <div className="flex items-center gap-2 text-sm">
                      <Mail className="w-4 h-4 text-muted-foreground shrink-0" />
                      <a
                        href={`mailto:${detail.email}`}
                        className="text-primary hover:underline truncate"
                      >
                        {detail.email}
                      </a>
                    </div>
                  )}
                  {detail.linkedin_url && (
                    <div className="flex items-center gap-2 text-sm">
                      <Linkedin className="w-4 h-4 text-muted-foreground shrink-0" />
                      <a
                        href={detail.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline truncate"
                      >
                        LinkedIn Profile
                      </a>
                    </div>
                  )}
                </div>

                <Separator />

                {/* AI Scores */}
                <div className="space-y-3">
                  <h3 className="text-sm font-medium">AI Scores</h3>
                  <div className="grid grid-cols-2 gap-3">
                    {/* Proximity */}
                    <div className="rounded-lg border p-3 space-y-1.5">
                      <div className="text-xs text-muted-foreground">Proximity</div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-semibold tabular-nums">
                          {detail.ai_proximity_score ?? '—'}
                        </span>
                        {detail.ai_proximity_tier && (
                          <Badge
                            variant="outline"
                            className={`text-[10px] ${PROXIMITY_COLORS[detail.ai_proximity_tier] || ''}`}
                          >
                            {TIER_LABELS[detail.ai_proximity_tier] || detail.ai_proximity_tier}
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Capacity */}
                    <div className="rounded-lg border p-3 space-y-1.5">
                      <div className="text-xs text-muted-foreground">Capacity</div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-semibold tabular-nums">
                          {detail.ai_capacity_score ?? '—'}
                        </span>
                        {detail.ai_capacity_tier && (
                          <Badge
                            variant="outline"
                            className={`text-[10px] ${CAPACITY_COLORS[detail.ai_capacity_tier] || ''}`}
                          >
                            {TIER_LABELS[detail.ai_capacity_tier] || detail.ai_capacity_tier}
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Kindora Type */}
                    <div className="rounded-lg border p-3 space-y-1.5">
                      <div className="text-xs text-muted-foreground">Kindora Type</div>
                      <div>
                        {detail.ai_kindora_prospect_type ? (
                          <Badge
                            variant="outline"
                            className="text-[10px] bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300"
                          >
                            {TIER_LABELS[detail.ai_kindora_prospect_type] || detail.ai_kindora_prospect_type}
                          </Badge>
                        ) : (
                          <span className="text-sm text-muted-foreground">—</span>
                        )}
                      </div>
                    </div>

                    {/* Outdoorithm Fit */}
                    <div className="rounded-lg border p-3 space-y-1.5">
                      <div className="text-xs text-muted-foreground">Outdoorithm Fit</div>
                      <div>
                        {detail.ai_outdoorithm_fit ? (
                          <Badge
                            variant="outline"
                            className={`text-[10px] ${
                              detail.ai_outdoorithm_fit === 'high' || detail.ai_outdoorithm_fit === 'medium'
                                ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                                : 'bg-gray-100 text-gray-600 dark:bg-gray-800/40 dark:text-gray-400'
                            }`}
                          >
                            {detail.ai_outdoorithm_fit.charAt(0).toUpperCase() +
                              detail.ai_outdoorithm_fit.slice(1)}
                          </Badge>
                        ) : (
                          <span className="text-sm text-muted-foreground">—</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Shared Context */}
                {hasSharedContext && (
                  <>
                    <Separator />
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium">Shared Context</h3>
                      {detail.shared_employers.length > 0 && (
                        <div className="flex items-start gap-2 text-sm">
                          <Briefcase className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                          <div>
                            <div className="text-xs text-muted-foreground mb-1">
                              Shared Employers
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {detail.shared_employers.map((e) => (
                                <Badge
                                  key={e}
                                  variant="secondary"
                                  className="text-xs"
                                >
                                  {e}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                      {detail.shared_schools.length > 0 && (
                        <div className="flex items-start gap-2 text-sm">
                          <GraduationCap className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                          <div>
                            <div className="text-xs text-muted-foreground mb-1">
                              Shared Schools
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {detail.shared_schools.map((s) => (
                                <Badge
                                  key={s}
                                  variant="secondary"
                                  className="text-xs"
                                >
                                  {s}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                      {detail.shared_boards.length > 0 && (
                        <div className="flex items-start gap-2 text-sm">
                          <Users className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                          <div>
                            <div className="text-xs text-muted-foreground mb-1">
                              Shared Boards
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {detail.shared_boards.map((b) => (
                                <Badge
                                  key={b}
                                  variant="secondary"
                                  className="text-xs"
                                >
                                  {b}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* Topics & Interests */}
                {(detail.topics.length > 0 || detail.primary_interests.length > 0) && (
                  <>
                    <Separator />
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium">Topics & Interests</h3>
                      <div className="flex flex-wrap gap-1.5">
                        {detail.topics.map((t) => (
                          <Badge
                            key={t}
                            variant="outline"
                            className="text-xs bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
                          >
                            {t}
                          </Badge>
                        ))}
                        {detail.primary_interests
                          .filter((i) => !detail.topics.includes(i))
                          .map((i) => (
                            <Badge key={i} variant="outline" className="text-xs">
                              {i}
                            </Badge>
                          ))}
                      </div>
                    </div>
                  </>
                )}

                {/* Outreach Context */}
                {hasOutreach && (
                  <>
                    <Separator />
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium">Outreach Context</h3>

                      {detail.suggested_opener && (
                        <div className="flex items-start gap-2">
                          <MessageSquare className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                          <div>
                            <div className="text-xs text-muted-foreground mb-1">
                              Suggested Opener
                            </div>
                            <p className="text-sm leading-relaxed italic">
                              &ldquo;{detail.suggested_opener}&rdquo;
                            </p>
                          </div>
                        </div>
                      )}

                      {detail.personalization_hooks.length > 0 && (
                        <div className="flex items-start gap-2">
                          <Lightbulb className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                          <div>
                            <div className="text-xs text-muted-foreground mb-1">
                              Personalization Hooks
                            </div>
                            <ul className="text-sm space-y-1">
                              {detail.personalization_hooks.map((h, i) => (
                                <li key={i} className="leading-snug">
                                  {h}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      )}

                      {detail.talking_points.length > 0 && (
                        <div className="flex items-start gap-2">
                          <MessageSquare className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                          <div>
                            <div className="text-xs text-muted-foreground mb-1">
                              Talking Points
                            </div>
                            <ul className="text-sm space-y-1">
                              {detail.talking_points.map((tp, i) => (
                                <li key={i} className="leading-snug">
                                  {tp}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      )}

                      {detail.best_approach && (
                        <div className="rounded-lg bg-muted/50 p-3">
                          <div className="text-xs text-muted-foreground mb-1">
                            Best Approach
                          </div>
                          <p className="text-sm leading-relaxed">
                            {detail.best_approach}
                          </p>
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* Summary */}
                {detail.summary && (
                  <>
                    <Separator />
                    <div className="space-y-2">
                      <h3 className="text-sm font-medium">Summary</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        {detail.summary}
                      </p>
                    </div>
                  </>
                )}
              </div>
            </ScrollArea>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
