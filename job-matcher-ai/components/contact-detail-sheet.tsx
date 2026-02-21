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
  AlertCircle,
  RefreshCw,
  Target,
  CheckCircle2,
} from 'lucide-react';

interface SharedInstitution {
  name: string;
  type: string;
  overlap: string;
  justin_period?: string;
  contact_period?: string;
  temporal_overlap?: boolean;
  depth?: string;
  notes?: string;
}

interface CommThread {
  subject?: string;
  date?: string;
  last_date?: string;
  snippet?: string;
}

interface AskReadinessGoal {
  score: number;
  tier: string;
  reasoning: string;
  recommended_approach?: string;
  ask_timing?: string;
  cultivation_needed?: string;
  suggested_ask_range?: string;
  personalization_angle?: string;
  risk_factors?: string[];
  scored_at?: string;
}

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
  // Relationship
  familiarity_rating?: number | null;
  comms_last_date?: string | null;
  comms_thread_count?: number | null;
  comms_relationship_summary?: string | null;
  comms_recent_threads?: CommThread[];
  // Structured institutional overlap
  shared_institutions?: SharedInstitution[];
  // Ask-readiness
  ask_readiness?: Record<string, AskReadinessGoal> | null;
  // Wealth signals
  fec_donations?: Record<string, any> | null;
  real_estate_data?: Record<string, any> | null;
  // AI scores
  ai_proximity_score?: number;
  ai_proximity_tier?: string;
  ai_capacity_score?: number;
  ai_capacity_tier?: string;
  ai_kindora_prospect_score?: number;
  ai_kindora_prospect_type?: string;
  ai_outdoorithm_fit?: string;
  // Legacy shared context
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

const CAPACITY_COLORS: Record<string, string> = {
  major_donor: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  mid_level: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  grassroots: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  unknown: 'bg-gray-100 text-gray-600 dark:bg-gray-800/40 dark:text-gray-400',
};

const ASK_READINESS_COLORS: Record<string, string> = {
  ready_now: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/40 dark:text-green-300',
  cultivate_first: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300',
  long_term: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800/40 dark:text-gray-400',
  not_a_fit: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/40 dark:text-red-300',
};

const ASK_READINESS_LABELS: Record<string, string> = {
  ready_now: 'Ready Now',
  cultivate_first: 'Cultivate First',
  long_term: 'Long Term',
  not_a_fit: 'Not a Fit',
};

const OVERLAP_TYPE_ICONS: Record<string, typeof Briefcase> = {
  employer: Briefcase,
  school: GraduationCap,
  board: Users,
  volunteer: Users,
};

const GOAL_LABELS: Record<string, string> = {
  outdoorithm_fundraising: 'Outdoorithm Fundraising',
  kindora_sales: 'Kindora Sales',
};

const FAMILIARITY_LABELS: Record<number, string> = {
  0: "Don't Know",
  1: 'Recognize',
  2: 'Know Them',
  3: 'Good Relationship',
  4: 'Close / Trusted',
};

function FamiliarityDots({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className={`w-2.5 h-2.5 rounded-full ${
            i <= rating
              ? 'bg-blue-500 dark:bg-blue-400'
              : 'bg-gray-200 dark:bg-gray-700'
          }`}
        />
      ))}
      <span className="ml-1.5 text-sm font-medium tabular-nums">{rating}/4</span>
    </div>
  );
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  const now = new Date();
  const currentYear = now.getFullYear();
  const dateYear = date.getFullYear();
  const month = date.toLocaleString('en-US', { month: 'short' });
  const day = date.getDate();
  if (dateYear === currentYear) {
    return `${month} ${day}`;
  }
  return `${month} ${day}, ${dateYear}`;
}

function getRecencyColor(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  const now = new Date();
  const monthsAgo = (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24 * 30);
  if (monthsAgo < 3) return 'text-green-600 dark:text-green-400';
  if (monthsAgo < 12) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-gray-500 dark:text-gray-400';
}

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

  const hasLegacySharedContext =
    detail &&
    (detail.shared_employers.length > 0 ||
      detail.shared_schools.length > 0 ||
      detail.shared_boards.length > 0);

  const hasStructuredOverlap =
    detail &&
    detail.shared_institutions &&
    detail.shared_institutions.length > 0;

  const hasOutreach =
    detail &&
    (detail.personalization_hooks.length > 0 ||
      detail.suggested_opener ||
      detail.talking_points.length > 0);

  const hasCommsHistory =
    detail &&
    ((detail.comms_recent_threads && detail.comms_recent_threads.length > 0) ||
      detail.comms_relationship_summary);

  const askReadinessGoals = detail?.ask_readiness
    ? Object.entries(detail.ask_readiness).filter(
        ([, v]) => v && typeof v === 'object' && 'score' in v
      )
    : [];

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

                {/* Your Relationship */}
                <div className="space-y-3">
                  <h3 className="text-sm font-medium">Your Relationship</h3>
                  <div className="grid grid-cols-3 gap-3">
                    {/* Familiarity */}
                    <div className="rounded-lg border p-3 space-y-1.5">
                      <div className="text-xs text-muted-foreground">Familiarity</div>
                      {detail.familiarity_rating != null ? (
                        <div>
                          <FamiliarityDots rating={detail.familiarity_rating} />
                          <div className="text-xs text-muted-foreground mt-1">
                            {FAMILIARITY_LABELS[detail.familiarity_rating] || ''}
                          </div>
                        </div>
                      ) : (
                        <span className="text-sm text-muted-foreground">Not rated</span>
                      )}
                    </div>

                    {/* Last Contact */}
                    <div className="rounded-lg border p-3 space-y-1.5">
                      <div className="text-xs text-muted-foreground">Last Contact</div>
                      {detail.comms_last_date ? (
                        <div className={`text-sm font-medium ${getRecencyColor(detail.comms_last_date)}`}>
                          {formatDate(detail.comms_last_date)}
                        </div>
                      ) : (
                        <span className="text-sm text-muted-foreground">No email history</span>
                      )}
                    </div>

                    {/* Email Threads */}
                    <div className="rounded-lg border p-3 space-y-1.5">
                      <div className="text-xs text-muted-foreground">Email Threads</div>
                      <div className="text-lg font-semibold tabular-nums">
                        {detail.comms_thread_count ?? 0}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Communication History */}
                {hasCommsHistory && (
                  <>
                    <Separator />
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium">Communication History</h3>
                      {detail.comms_relationship_summary && (
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {detail.comms_relationship_summary}
                        </p>
                      )}
                      {detail.comms_recent_threads && detail.comms_recent_threads.length > 0 && (
                        <div className="space-y-2">
                          <div className="text-xs text-muted-foreground">Recent Threads</div>
                          {detail.comms_recent_threads.map((thread, i) => (
                            <div key={i} className="flex items-start gap-2 text-sm">
                              <Mail className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
                              <div className="min-w-0">
                                <div className="truncate font-medium">
                                  {thread.subject || 'No subject'}
                                </div>
                                {(thread.date || thread.last_date) && (
                                  <div className="text-xs text-muted-foreground">
                                    {formatDate(thread.date || thread.last_date || '')}
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* Institutional Overlap — prefer structured, fall back to legacy */}
                {hasStructuredOverlap ? (
                  <>
                    <Separator />
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium">Institutional Overlap</h3>
                      <div className="space-y-2.5">
                        {detail.shared_institutions!.map((inst, i) => {
                          const Icon = OVERLAP_TYPE_ICONS[inst.type] || Building2;
                          return (
                            <div key={i} className="flex items-start gap-2 text-sm">
                              <Icon className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                              <div className="min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="font-medium">{inst.name}</span>
                                  <Badge variant="outline" className="text-[10px]">
                                    {inst.type}
                                  </Badge>
                                  {inst.temporal_overlap && (
                                    <Badge
                                      variant="outline"
                                      className="text-[10px] bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400"
                                    >
                                      <CheckCircle2 className="w-2.5 h-2.5 mr-0.5" />
                                      Overlapping
                                    </Badge>
                                  )}
                                </div>
                                <div className="text-xs text-muted-foreground mt-0.5">
                                  {inst.justin_period && (
                                    <span>Justin: {inst.justin_period}</span>
                                  )}
                                  {inst.justin_period && inst.contact_period && (
                                    <span className="mx-1.5">&middot;</span>
                                  )}
                                  {inst.contact_period && (
                                    <span>Contact: {inst.contact_period}</span>
                                  )}
                                </div>
                                {inst.notes && (
                                  <div className="text-xs text-muted-foreground mt-0.5 italic">
                                    {inst.notes}
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </>
                ) : hasLegacySharedContext ? (
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
                                <Badge key={e} variant="secondary" className="text-xs">
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
                                <Badge key={s} variant="secondary" className="text-xs">
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
                                <Badge key={b} variant="secondary" className="text-xs">
                                  {b}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                ) : null}

                {/* Ask Readiness — shown for each scored goal */}
                {askReadinessGoals.length > 0 && (
                  <>
                    <Separator />
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium">Ask Readiness</h3>
                      {askReadinessGoals.map(([goalKey, goalData]) => (
                        <div
                          key={goalKey}
                          className="rounded-lg border p-4 space-y-3"
                        >
                          {/* Goal header with tier + score */}
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Target className="w-4 h-4 text-muted-foreground" />
                              <span className="text-sm font-medium">
                                {GOAL_LABELS[goalKey] || goalKey}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge
                                variant="outline"
                                className={`text-xs ${ASK_READINESS_COLORS[goalData.tier] || ''}`}
                              >
                                {ASK_READINESS_LABELS[goalData.tier] || goalData.tier}
                              </Badge>
                              <span className="text-lg font-semibold tabular-nums">
                                {goalData.score}
                              </span>
                            </div>
                          </div>

                          {/* Reasoning */}
                          {goalData.reasoning && (
                            <p className="text-sm text-muted-foreground leading-relaxed">
                              {goalData.reasoning}
                            </p>
                          )}

                          {/* Key details grid */}
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            {goalData.recommended_approach && (
                              <div>
                                <div className="text-muted-foreground">Approach</div>
                                <div className="font-medium capitalize">
                                  {goalData.recommended_approach.replace(/_/g, ' ')}
                                </div>
                              </div>
                            )}
                            {goalData.ask_timing && (
                              <div>
                                <div className="text-muted-foreground">Timing</div>
                                <div className="font-medium capitalize">
                                  {goalData.ask_timing.replace(/_/g, ' ')}
                                </div>
                              </div>
                            )}
                            {goalData.suggested_ask_range && (
                              <div>
                                <div className="text-muted-foreground">Suggested Range</div>
                                <div className="font-medium">{goalData.suggested_ask_range}</div>
                              </div>
                            )}
                            {goalData.cultivation_needed && goalData.cultivation_needed !== 'None' && (
                              <div>
                                <div className="text-muted-foreground">Cultivation</div>
                                <div className="font-medium">{goalData.cultivation_needed}</div>
                              </div>
                            )}
                          </div>

                          {/* Personalization angle */}
                          {goalData.personalization_angle && (
                            <div className="rounded bg-muted/50 p-2.5">
                              <div className="text-xs text-muted-foreground mb-1">Personalization Angle</div>
                              <p className="text-sm leading-relaxed">
                                {goalData.personalization_angle}
                              </p>
                            </div>
                          )}

                          {/* Risk factors */}
                          {goalData.risk_factors && goalData.risk_factors.length > 0 && (
                            <div className="text-xs">
                              <div className="text-muted-foreground mb-1">Risk Factors</div>
                              <ul className="space-y-0.5 text-red-600 dark:text-red-400">
                                {goalData.risk_factors.map((risk, i) => (
                                  <li key={i}>{risk}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                )}

                <Separator />

                {/* AI Analysis (formerly AI Scores) */}
                <div className="space-y-3">
                  <h3 className="text-sm font-medium">AI Analysis</h3>
                  <div className="grid grid-cols-2 gap-3">
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

                    {/* Proximity (legacy/secondary) */}
                    <div className="rounded-lg border p-3 space-y-1.5">
                      <div className="text-xs text-muted-foreground">Proximity <span className="text-[10px]">(legacy)</span></div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-semibold tabular-nums text-muted-foreground">
                          {detail.ai_proximity_score ?? '—'}
                        </span>
                        {detail.ai_proximity_tier && (
                          <Badge variant="outline" className="text-[10px]">
                            {TIER_LABELS[detail.ai_proximity_tier] || detail.ai_proximity_tier}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

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
