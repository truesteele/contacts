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
import { Separator } from '@/components/ui/separator';
import {
  Building2,
  MapPin,
  Mail,
  Briefcase,
  GraduationCap,
  Users,
  MessageSquare,
  Lightbulb,
  AlertTriangle,
  Target,
  CheckCircle2,
  Home,
  DollarSign,
  Info,
} from 'lucide-react';

interface CommThread {
  subject?: string;
  date?: string;
  snippet?: string;
  source?: string;
  direction?: string;
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
  familiarity_rating?: number | null;
  comms_last_date?: string | null;
  comms_thread_count?: number | null;
  comms_closeness?: string | null;
  comms_momentum?: string | null;
  comms_reasoning?: string | null;
  comms_relationship_summary?: string | null;
  comms_recent_threads?: CommThread[];
  shared_institutions?: Array<{ name: string; type: string; overlap: string }>;
  ask_readiness?: Record<string, AskReadinessGoal> | null;
  fec_donations?: Record<string, any> | null;
  real_estate_data?: Record<string, any> | null;
  ai_proximity_score?: number;
  ai_proximity_tier?: string;
  ai_capacity_score?: number;
  ai_capacity_tier?: string;
  education_focus_fit?: string;
  shared_employers: string[];
  shared_schools: string[];
  shared_boards: string[];
  topics: string[];
  primary_interests: string[];
  personalization_hooks: string[];
  suggested_opener: string;
  best_approach: string;
  talking_points: string[];
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

const COMMS_CLOSENESS_COLORS: Record<string, string> = {
  active_inner_circle: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/40 dark:text-green-300',
  regular_contact: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/40 dark:text-blue-300',
  occasional: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300',
  dormant: 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/40 dark:text-orange-300',
  one_way: 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/40 dark:text-purple-300',
  no_history: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800/40 dark:text-gray-400',
};

const COMMS_CLOSENESS_LABELS: Record<string, string> = {
  active_inner_circle: 'Inner Circle',
  regular_contact: 'Regular',
  occasional: 'Occasional',
  dormant: 'Dormant',
  one_way: 'One-Way',
  no_history: 'No History',
};

const COMMS_MOMENTUM_COLORS: Record<string, string> = {
  growing: 'text-green-600 dark:text-green-400',
  stable: 'text-blue-600 dark:text-blue-400',
  fading: 'text-orange-600 dark:text-orange-400',
  inactive: 'text-gray-500 dark:text-gray-400',
};

const COMMS_MOMENTUM_LABELS: Record<string, string> = {
  growing: 'Growing',
  stable: 'Stable',
  fading: 'Fading',
  inactive: 'Inactive',
};

const COMMS_MOMENTUM_ICONS: Record<string, string> = {
  growing: '\u2197',
  stable: '\u2014',
  fading: '\u2198',
  inactive: '\u00D7',
};

const OVERLAP_TYPE_ICONS: Record<string, typeof Briefcase> = {
  employer: Briefcase,
  school: GraduationCap,
  board: Users,
  volunteer: Users,
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
  const month = date.toLocaleString('en-US', { month: 'short' });
  const day = date.getDate();
  if (date.getFullYear() === now.getFullYear()) return `${month} ${day}`;
  return `${month} ${day}, ${date.getFullYear()}`;
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
      const res = await fetch(`/api/contact/${id}`);
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
    if (open && contactId != null) fetchDetail(contactId);
    if (!open) { setDetail(null); setError(''); }
  }, [open, contactId, fetchDetail]);

  const location = detail ? [detail.city, detail.state].filter(Boolean).join(', ') : '';

  const hasStructuredOverlap = detail?.shared_institutions && detail.shared_institutions.length > 0;

  const hasOutreach = detail && (
    detail.personalization_hooks.length > 0 ||
    detail.suggested_opener ||
    detail.talking_points.length > 0
  );

  const hasCommsHistory = detail && (
    (detail.comms_recent_threads && detail.comms_recent_threads.length > 0) ||
    detail.comms_relationship_summary
  );

  const askReadinessGoals = detail?.ask_readiness
    ? Object.entries(detail.ask_readiness).filter(
        ([, v]) => v && typeof v === 'object' && 'score' in v
      )
    : [];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center h-32">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              Loading...
            </div>
          </div>
        )}

        {error && (
          <div className="p-4 text-destructive text-sm">{error}</div>
        )}

        {detail && !loading && (
          <>
            <SheetHeader className="pb-2">
              <SheetTitle className="text-xl">
                {detail.first_name} {detail.last_name}
              </SheetTitle>
              <SheetDescription className="text-sm">
                {detail.headline || [detail.position, detail.company].filter(Boolean).join(' at ')}
              </SheetDescription>
            </SheetHeader>

            {/* Basic info */}
            <div className="space-y-2 text-sm mb-4">
              {detail.company && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Building2 className="w-4 h-4 shrink-0" />
                  <span>{detail.position ? `${detail.position} at ${detail.company}` : detail.company}</span>
                </div>
              )}
              {location && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <MapPin className="w-4 h-4 shrink-0" />
                  <span>{location}</span>
                </div>
              )}
              {detail.email && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Mail className="w-4 h-4 shrink-0" />
                  <span>{detail.email}</span>
                </div>
              )}
            </div>

            {detail.summary && (
              <p className="text-sm text-muted-foreground mb-4 leading-relaxed">{detail.summary}</p>
            )}

            <Separator className="my-4" />

            {/* ── Relationship ── */}
            <div className="space-y-3 mb-4">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Users className="w-4 h-4" /> Relationship
              </h3>

              {detail.familiarity_rating != null && detail.familiarity_rating > 0 && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Familiarity</span>
                  <div className="flex items-center gap-2">
                    <FamiliarityDots rating={detail.familiarity_rating} />
                    <span className="text-xs text-muted-foreground">
                      {FAMILIARITY_LABELS[detail.familiarity_rating] || ''}
                    </span>
                  </div>
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                {detail.comms_closeness && (
                  <Badge variant="outline" className={`text-xs ${COMMS_CLOSENESS_COLORS[detail.comms_closeness] || ''}`}>
                    {COMMS_CLOSENESS_LABELS[detail.comms_closeness] || detail.comms_closeness}
                  </Badge>
                )}
                {detail.comms_momentum && (
                  <span className={`text-xs font-medium ${COMMS_MOMENTUM_COLORS[detail.comms_momentum] || ''}`}>
                    {COMMS_MOMENTUM_ICONS[detail.comms_momentum] || ''}{' '}
                    {COMMS_MOMENTUM_LABELS[detail.comms_momentum] || detail.comms_momentum}
                  </span>
                )}
              </div>

              {detail.comms_reasoning && (
                <p className="text-xs text-muted-foreground leading-relaxed">{detail.comms_reasoning}</p>
              )}

              {detail.comms_last_date && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Last contact</span>
                  <span className={getRecencyColor(detail.comms_last_date)}>
                    {formatDate(detail.comms_last_date)}
                    {detail.comms_thread_count ? ` (${detail.comms_thread_count} threads)` : ''}
                  </span>
                </div>
              )}
            </div>

            {/* Communication threads */}
            {hasCommsHistory && (
              <>
                <Separator className="my-4" />
                <div className="space-y-3 mb-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" /> Communication History
                  </h3>
                  {detail.comms_relationship_summary && (
                    <p className="text-xs text-muted-foreground leading-relaxed italic">
                      {detail.comms_relationship_summary}
                    </p>
                  )}
                  {detail.comms_recent_threads && detail.comms_recent_threads.length > 0 && (
                    <div className="space-y-2">
                      {detail.comms_recent_threads.map((thread, i) => (
                        <div key={i} className="border rounded-md p-2 text-xs">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium truncate max-w-[200px]">
                              {thread.subject || 'No subject'}
                            </span>
                            {thread.date && (
                              <span className="text-muted-foreground shrink-0 ml-2">
                                {formatDate(thread.date)}
                              </span>
                            )}
                          </div>
                          {thread.snippet && (
                            <p className="text-muted-foreground line-clamp-2">{thread.snippet}</p>
                          )}
                          <div className="flex items-center gap-2 mt-1">
                            {thread.source && (
                              <Badge variant="outline" className="text-[10px] px-1 py-0">
                                {thread.source}
                              </Badge>
                            )}
                            {thread.direction && (
                              <span className="text-[10px] text-muted-foreground capitalize">
                                {thread.direction}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}

            {/* Shared institutions */}
            {hasStructuredOverlap && (
              <>
                <Separator className="my-4" />
                <div className="space-y-3 mb-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <Briefcase className="w-4 h-4" /> Shared Background
                  </h3>
                  <div className="space-y-2">
                    {detail.shared_institutions!.map((inst, i) => {
                      const Icon = OVERLAP_TYPE_ICONS[inst.type] || Users;
                      return (
                        <div key={i} className="flex items-start gap-2 text-xs">
                          <Icon className="w-3.5 h-3.5 mt-0.5 text-muted-foreground shrink-0" />
                          <div>
                            <span className="font-medium">{inst.name}</span>
                            <span className="text-muted-foreground ml-1">- {inst.overlap}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            )}

            {/* Ask Readiness */}
            {askReadinessGoals.length > 0 && (
              <>
                <Separator className="my-4" />
                <div className="space-y-3 mb-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <Target className="w-4 h-4" /> Ask Readiness
                  </h3>
                  {askReadinessGoals.map(([goal, data]) => (
                    <div key={goal} className="border rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium">Individual Giving</span>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${ASK_READINESS_COLORS[data.tier] || ''}`}>
                            {ASK_READINESS_LABELS[data.tier] || data.tier}
                          </Badge>
                          <span className="text-sm font-mono font-bold tabular-nums">{data.score}</span>
                        </div>
                      </div>

                      <p className="text-xs text-muted-foreground leading-relaxed">{data.reasoning}</p>

                      <div className="grid grid-cols-2 gap-2 text-xs">
                        {data.recommended_approach && (
                          <div>
                            <span className="text-muted-foreground">Approach:</span>{' '}
                            <span className="font-medium capitalize">{data.recommended_approach.replace(/_/g, ' ')}</span>
                          </div>
                        )}
                        {data.ask_timing && (
                          <div>
                            <span className="text-muted-foreground">Timing:</span>{' '}
                            <span className="font-medium capitalize">{data.ask_timing.replace(/_/g, ' ')}</span>
                          </div>
                        )}
                        {data.suggested_ask_range && (
                          <div className="col-span-2">
                            <span className="text-muted-foreground">Ask Range:</span>{' '}
                            <span className="font-medium">{data.suggested_ask_range}</span>
                          </div>
                        )}
                      </div>

                      {data.cultivation_needed && (
                        <div className="text-xs">
                          <span className="text-muted-foreground">Cultivation:</span>{' '}
                          <span>{data.cultivation_needed}</span>
                        </div>
                      )}

                      {data.personalization_angle && (
                        <div className="text-xs">
                          <span className="text-muted-foreground">Personalization:</span>{' '}
                          <span className="italic">{data.personalization_angle}</span>
                        </div>
                      )}

                      {data.risk_factors && data.risk_factors.length > 0 && (
                        <div className="flex items-start gap-1.5 text-xs">
                          <AlertTriangle className="w-3.5 h-3.5 text-orange-500 shrink-0 mt-0.5" />
                          <span className="text-orange-700 dark:text-orange-400">
                            {data.risk_factors.join('; ')}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* Wealth Signals */}
            {(detail.fec_donations || detail.real_estate_data) && (
              <>
                <Separator className="my-4" />
                <div className="space-y-3 mb-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <DollarSign className="w-4 h-4" /> Wealth Signals
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {detail.ai_capacity_tier && (
                      <Badge className={`text-xs ${CAPACITY_COLORS[detail.ai_capacity_tier] || ''}`}>
                        {TIER_LABELS[detail.ai_capacity_tier] || detail.ai_capacity_tier}
                      </Badge>
                    )}
                    {detail.ai_capacity_score != null && (
                      <span className="text-xs text-muted-foreground">
                        Capacity Score: {detail.ai_capacity_score}
                      </span>
                    )}
                  </div>
                  {detail.fec_donations && (
                    <div className="text-xs">
                      <span className="text-muted-foreground">FEC Donations:</span>{' '}
                      <span className="font-medium">${(detail.fec_donations.total || 0).toLocaleString()}</span>
                    </div>
                  )}
                  {detail.real_estate_data?.properties?.[0] && (
                    <div className="flex items-center gap-1.5 text-xs">
                      <Home className="w-3.5 h-3.5 text-muted-foreground" />
                      <span>{detail.real_estate_data.properties[0].address}</span>
                      {detail.real_estate_data.properties[0].zestimate && (
                        <span className="text-muted-foreground">
                          (est. ${(detail.real_estate_data.properties[0].zestimate / 1000000).toFixed(1)}M)
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </>
            )}

            {/* AI Scores */}
            <Separator className="my-4" />
            <div className="space-y-3 mb-4">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Info className="w-4 h-4" /> AI Scores
              </h3>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {detail.ai_proximity_score != null && (
                  <div>
                    <span className="text-muted-foreground">Proximity:</span>{' '}
                    <span className="font-medium">{detail.ai_proximity_score}</span>
                    {detail.ai_proximity_tier && (
                      <span className="text-muted-foreground ml-1">
                        ({TIER_LABELS[detail.ai_proximity_tier] || detail.ai_proximity_tier})
                      </span>
                    )}
                  </div>
                )}
                {detail.ai_capacity_score != null && (
                  <div>
                    <span className="text-muted-foreground">Capacity:</span>{' '}
                    <span className="font-medium">{detail.ai_capacity_score}</span>
                    {detail.ai_capacity_tier && (
                      <span className="text-muted-foreground ml-1">
                        ({TIER_LABELS[detail.ai_capacity_tier] || detail.ai_capacity_tier})
                      </span>
                    )}
                  </div>
                )}
              </div>
              {detail.topics && detail.topics.length > 0 && (
                <div>
                  <span className="text-xs text-muted-foreground">Topics:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {detail.topics.map((topic, i) => (
                      <Badge key={i} variant="outline" className="text-[10px] px-1.5 py-0">
                        {topic}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Outreach Context */}
            {hasOutreach && (
              <>
                <Separator className="my-4" />
                <div className="space-y-3 mb-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <Lightbulb className="w-4 h-4" /> Outreach Context
                  </h3>

                  {detail.personalization_hooks.length > 0 && (
                    <div>
                      <span className="text-xs text-muted-foreground">Personalization Hooks:</span>
                      <ul className="mt-1 space-y-1">
                        {detail.personalization_hooks.map((hook, i) => (
                          <li key={i} className="text-xs flex items-start gap-1.5">
                            <CheckCircle2 className="w-3 h-3 text-green-500 mt-0.5 shrink-0" />
                            <span>{hook}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {detail.suggested_opener && (
                    <div>
                      <span className="text-xs text-muted-foreground">Suggested Opener:</span>
                      <p className="text-xs mt-1 italic leading-relaxed border-l-2 border-primary/30 pl-2">
                        {detail.suggested_opener}
                      </p>
                    </div>
                  )}

                  {detail.talking_points.length > 0 && (
                    <div>
                      <span className="text-xs text-muted-foreground">Talking Points:</span>
                      <ul className="mt-1 space-y-1">
                        {detail.talking_points.map((point, i) => (
                          <li key={i} className="text-xs flex items-start gap-1.5">
                            <span className="text-primary font-bold">-</span>
                            <span>{point}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </>
            )}

            {/* Footer */}
            <Separator className="my-4" />
            <p className="text-[10px] text-muted-foreground text-center pb-4">
              SF Education Fund | Donor Intelligence Preview | Mock Data
            </p>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
