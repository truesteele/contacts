'use client';

import { useState, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { cn } from '@/lib/utils';
import { STAGE_CONFIG, SECTOR_CONFIG, ACTIVITY_CONFIG } from '@/lib/mock-data';
import type { AlumniDetail } from '@/lib/mock-data';
import {
  Building2, MapPin, Users, DollarSign, TrendingUp, Newspaper, MessageSquare,
  ExternalLink, Calendar, Award, Handshake, Megaphone, UserPlus,
} from 'lucide-react';

const MILESTONE_ICONS: Record<string, any> = {
  funding: DollarSign, product: TrendingUp, team: UserPlus, award: Award,
  partnership: Handshake, media: Megaphone,
};

function SentimentDot({ sentiment }: { sentiment: string }) {
  const colors: Record<string, string> = {
    positive: 'bg-green-500', neutral: 'bg-gray-400', negative: 'bg-red-500',
  };
  return <span className={cn('inline-block w-2 h-2 rounded-full', colors[sentiment] || colors.neutral)} />;
}

export function AlumniDetailSheet({
  alumniId,
  open,
  onOpenChange,
}: {
  alumniId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [detail, setDetail] = useState<AlumniDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!alumniId || !open) return;
    setLoading(true);
    fetch(`/api/alumni-detail?id=${alumniId}`)
      .then((r) => r.json())
      .then((d) => setDetail(d))
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [alumniId, open]);

  const stageConf = detail ? STAGE_CONFIG[detail.venture_stage] : null;
  const sectorConf = detail ? SECTOR_CONFIG[detail.sector] : null;
  const activityConf = detail ? ACTIVITY_CONFIG[detail.activity_level] : null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[520px] sm:max-w-[520px] overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center h-40">
            <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
          </div>
        )}
        {!loading && detail && (
          <>
            <SheetHeader>
              <SheetTitle className="text-xl">
                {detail.first_name} {detail.last_name}
              </SheetTitle>
              <p className="text-sm text-muted-foreground">{detail.venture_role}</p>
            </SheetHeader>

            <div className="mt-4 space-y-5">
              {/* Venture header */}
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-bold text-lg">
                  {detail.venture_name.charAt(0)}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-base">{detail.venture_name}</h3>
                  <p className="text-sm text-muted-foreground">{detail.headline}</p>
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    {stageConf && (
                      <Badge variant="outline" className={cn('text-[10px] px-1.5 py-0', stageConf.bg, stageConf.color)}>
                        {stageConf.label}
                      </Badge>
                    )}
                    {sectorConf && (
                      <Badge variant="outline" className={cn('text-[10px] px-1.5 py-0', sectorConf.color)}>
                        {sectorConf.label}
                      </Badge>
                    )}
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                      {detail.cohort}
                    </Badge>
                    {detail.venture_type === 'nonprofit' && (
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-teal-100 text-teal-700 border-teal-200">
                        Nonprofit
                      </Badge>
                    )}
                  </div>
                </div>
              </div>

              {/* Key metrics grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border p-2.5">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                    <DollarSign className="w-3 h-3" /> {detail.venture_type === 'nonprofit' ? 'Grants Received' : 'Total Funding'}
                  </div>
                  <div className="font-semibold">
                    {detail.total_funding > 0
                      ? detail.total_funding >= 1e6 ? `$${(detail.total_funding / 1e6).toFixed(1)}M` : `$${(detail.total_funding / 1e3).toFixed(0)}K`
                      : detail.venture_type === 'nonprofit' ? 'New' : 'Bootstrapped'}
                  </div>
                  {detail.last_funding_type && (
                    <div className="text-xs text-muted-foreground">{detail.last_funding_type}</div>
                  )}
                </div>
                <div className="rounded-lg border p-2.5">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                    <Users className="w-3 h-3" /> {detail.venture_type === 'nonprofit' ? 'Staff' : 'Team Size'}
                  </div>
                  <div className="font-semibold">{detail.team_size > 0 ? detail.team_size : 'N/A'}</div>
                  {detail.revenue_range && (
                    <div className="text-xs text-muted-foreground">
                      {detail.venture_type === 'nonprofit' ? detail.revenue_range : detail.revenue_range}
                    </div>
                  )}
                </div>
                <div className="rounded-lg border p-2.5">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                    <TrendingUp className="w-3 h-3" /> Activity
                  </div>
                  <div className={cn('font-semibold', activityConf?.color)}>
                    {activityConf?.label} ({detail.activity_score})
                  </div>
                  <div className="text-xs text-muted-foreground capitalize">Momentum: {detail.momentum}</div>
                </div>
                <div className="rounded-lg border p-2.5">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                    <MapPin className="w-3 h-3" /> Location
                  </div>
                  <div className="font-semibold">{detail.city}, {detail.state}</div>
                </div>
              </div>

              {/* Nonprofit impact metrics */}
              {detail.venture_type === 'nonprofit' && (detail.people_served || detail.impact_metric) && (
                <div className="rounded-lg border border-teal-200 bg-teal-50 dark:bg-teal-900/20 dark:border-teal-800 p-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-teal-700 dark:text-teal-400 mb-1">Impact</h4>
                  {detail.people_served && (
                    <div className="text-sm font-semibold text-teal-800 dark:text-teal-300">
                      {detail.people_served.toLocaleString()} people served
                    </div>
                  )}
                  {detail.impact_metric && (
                    <p className="text-sm text-teal-700 dark:text-teal-300 mt-0.5">{detail.impact_metric}</p>
                  )}
                </div>
              )}

              {/* Summary */}
              {detail.summary && (
                <>
                  <Separator />
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1.5">About</h4>
                    <p className="text-sm leading-relaxed">{detail.summary}</p>
                  </div>
                </>
              )}

              {/* Key updates */}
              {detail.key_updates.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1.5">Key Updates</h4>
                    <ul className="space-y-1">
                      {detail.key_updates.map((u, i) => (
                        <li key={i} className="text-sm flex items-start gap-2">
                          <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                          {u}
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}

              {/* Risk flags */}
              {detail.risk_flags.length > 0 && (
                <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 p-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-red-600 dark:text-red-400 mb-1">Risk Flags</h4>
                  <ul className="space-y-1">
                    {detail.risk_flags.map((r, i) => (
                      <li key={i} className="text-sm text-red-700 dark:text-red-300">{r}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recent LinkedIn posts */}
              {detail.linkedin_posts_recent.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                      <MessageSquare className="w-3 h-3 inline mr-1" />
                      Recent LinkedIn Posts
                    </h4>
                    <div className="space-y-3">
                      {detail.linkedin_posts_recent.map((post, i) => (
                        <div key={i} className="rounded-lg border p-3">
                          <p className="text-sm leading-relaxed mb-2">{post.text}</p>
                          <div className="flex items-center gap-3 text-xs text-muted-foreground">
                            <span>{new Date(post.date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                            <span>{post.likes} likes</span>
                            <span>{post.comments} comments</span>
                            <span>{post.reposts} reposts</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* News */}
              {detail.news_articles.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                      <Newspaper className="w-3 h-3 inline mr-1" />
                      News Coverage
                    </h4>
                    <div className="space-y-2">
                      {detail.news_articles.map((article, i) => (
                        <div key={i} className="flex items-start gap-2 text-sm">
                          <SentimentDot sentiment={article.sentiment} />
                          <div className="flex-1">
                            <span className="font-medium">{article.title}</span>
                            <div className="text-xs text-muted-foreground">
                              {article.source} &middot; {new Date(article.date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Milestones */}
              {detail.milestones.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Timeline</h4>
                    <div className="space-y-2">
                      {detail.milestones.map((m, i) => {
                        const Icon = MILESTONE_ICONS[m.type] || TrendingUp;
                        return (
                          <div key={i} className="flex items-start gap-2 text-sm">
                            <Icon className="w-3.5 h-3.5 mt-0.5 text-muted-foreground shrink-0" />
                            <div>
                              <span>{m.description}</span>
                              <span className="text-xs text-muted-foreground ml-2">
                                {new Date(m.date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </>
              )}

              {/* Camelback notes */}
              {detail.camelback_notes && (
                <>
                  <Separator />
                  <div className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-800 p-3">
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-400 mb-1">Camelback Notes</h4>
                    <p className="text-sm text-amber-800 dark:text-amber-300">{detail.camelback_notes}</p>
                  </div>
                </>
              )}

              {/* LinkedIn stats */}
              <Separator />
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-lg border p-2">
                  <div className="text-lg font-bold">{detail.linkedin_followers.toLocaleString()}</div>
                  <div className="text-xs text-muted-foreground">Followers</div>
                </div>
                <div className="rounded-lg border p-2">
                  <div className="text-lg font-bold">{detail.linkedin_posts_30d}</div>
                  <div className="text-xs text-muted-foreground">Posts (30d)</div>
                </div>
                <div className="rounded-lg border p-2">
                  <div className="text-lg font-bold">{detail.linkedin_engagement_rate}%</div>
                  <div className="text-xs text-muted-foreground">Engagement</div>
                </div>
              </div>

              <div className="text-[10px] text-muted-foreground text-right">
                Last scraped: {new Date(detail.scraped_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
