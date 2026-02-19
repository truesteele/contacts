'use client';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { ExternalLink, Linkedin, Star, User } from 'lucide-react';

export interface CoachResult {
  expert_id: number;
  expert_name: string;
  expert_position: string;
  expert_organization: string;
  expert_areas: string;
  expert_headline: string;
  expert_profile_picture_url: string | null;
  expert_linkedin_url: string | null;
  expert_profile_url: string | null;
  expert_follower_count: number | null;
  coaching_summary: string;
  expertise_tags: string[];
  coaching_strengths: string[];
  ideal_for: string;
  rrf_score: number;
  match_rationale?: string;
  match_score?: number;
}

function MatchScoreBadge({ score }: { score: number }) {
  const color =
    score >= 8 ? 'bg-green-100 text-green-800 border-green-200' :
    score >= 6 ? 'bg-yellow-100 text-yellow-800 border-yellow-200' :
    'bg-gray-100 text-gray-800 border-gray-200';

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${color}`}>
      <Star className="w-3 h-3" />
      {score}/10
    </span>
  );
}

export function CoachResultCard({ coach, rank }: { coach: CoachResult; rank: number }) {
  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0">
            {coach.expert_profile_picture_url ? (
              <img
                src={coach.expert_profile_picture_url}
                alt={coach.expert_name}
                className="w-14 h-14 rounded-full object-cover border-2 border-muted"
              />
            ) : (
              <div className="w-14 h-14 rounded-full bg-muted flex items-center justify-center border-2 border-muted">
                <User className="w-6 h-6 text-muted-foreground" />
              </div>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-medium text-muted-foreground bg-muted rounded-full px-2 py-0.5">
                #{rank}
              </span>
              <h3 className="font-semibold text-lg leading-tight">{coach.expert_name}</h3>
              {coach.match_score && <MatchScoreBadge score={coach.match_score} />}
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">
              {coach.expert_position}{coach.expert_organization ? ` at ${coach.expert_organization}` : ''}
            </p>
            {coach.expert_headline && coach.expert_headline !== coach.expert_position && (
              <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{coach.expert_headline}</p>
            )}
            {coach.expert_areas && (
              <p className="text-xs text-blue-600 mt-1">Camelback Area: {coach.expert_areas}</p>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {coach.match_rationale && (
          <div className="bg-blue-50 border border-blue-100 rounded-lg p-3">
            <p className="text-xs font-medium text-blue-800 mb-1">Why this match</p>
            <p className="text-sm text-blue-900">{coach.match_rationale}</p>
          </div>
        )}

        <div className="flex flex-wrap gap-1.5">
          {coach.expertise_tags.slice(0, 8).map((tag) => (
            <span
              key={tag}
              className="inline-flex px-2 py-0.5 rounded-md bg-muted text-xs font-medium text-muted-foreground"
            >
              {tag}
            </span>
          ))}
        </div>

        {coach.coaching_strengths.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">Can help with</p>
            <ul className="text-sm space-y-0.5">
              {coach.coaching_strengths.slice(0, 4).map((strength) => (
                <li key={strength} className="text-muted-foreground">
                  <span className="text-foreground">{strength}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex items-center gap-3 pt-2 border-t">
          {coach.expert_linkedin_url && (
            <a
              href={coach.expert_linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 hover:underline"
            >
              <Linkedin className="w-3.5 h-3.5" />
              LinkedIn
            </a>
          )}
          {coach.expert_profile_url && (
            <a
              href={coach.expert_profile_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 hover:underline"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Camelback Profile
            </a>
          )}
          {coach.expert_follower_count && coach.expert_follower_count > 0 && (
            <span className="text-xs text-muted-foreground ml-auto">
              {coach.expert_follower_count.toLocaleString()} followers
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
