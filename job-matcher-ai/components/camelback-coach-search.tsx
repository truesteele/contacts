'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Search, Loader2, Sparkles } from 'lucide-react';
import { CoachResultCard, CoachResult } from '@/components/coach-result-card';

const SUGGESTED_QUERIES = [
  'I need help with UX/UI design for my fundraising app',
  'Fundraising strategy for a nonprofit startup',
  'How to build a sales pipeline for B2B SaaS',
  'DEI strategy and equitable hiring practices',
  'Marketing and brand building for an early-stage company',
  'Product-market fit validation for EdTech',
];

export function CamelbackCoachSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<CoachResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchedQuery, setSearchedQuery] = useState('');

  const handleSearch = async (searchQuery?: string) => {
    const q = searchQuery || query;
    if (!q.trim()) return;

    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    setSearchedQuery(q);

    try {
      const response = await fetch('/api/coach-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Search failed');
      }

      const data = await response.json();
      setResults(data.recommendations || []);
    } catch (err) {
      console.error('Search error:', err);
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch();
  };

  const handleSuggestion = (suggestion: string) => {
    setQuery(suggestion);
    handleSearch(suggestion);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="mb-4">
        <h2 className="text-2xl font-bold mb-1">Camelback Coach Search</h2>
        <p className="text-muted-foreground text-sm">
          AI-powered search across 73 Camelback Ventures Expert Bench coaches. Describe what you need help with.
        </p>
      </div>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <div className="border-b p-4">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What kind of help are you looking for? e.g. 'UX/UI design for my fundraising app'"
                className="w-full pl-10 pr-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm"
                disabled={isLoading}
              />
            </div>
            <Button type="submit" disabled={isLoading || !query.trim()}>
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              <span className="ml-2">Search</span>
            </Button>
          </form>
        </div>

        <ScrollArea className="flex-1">
          <div className="p-4">
            {!hasSearched && !isLoading && (
              <div className="text-center py-8">
                <Sparkles className="w-10 h-10 text-muted-foreground mx-auto mb-4" />
                <p className="text-lg font-medium mb-2">Find the right coach for your needs</p>
                <p className="text-sm text-muted-foreground mb-6">
                  Uses AI to match your query against coach expertise, experience, and LinkedIn activity
                </p>
                <div className="max-w-xl mx-auto">
                  <p className="text-xs font-medium text-muted-foreground mb-3">Try a search</p>
                  <div className="flex flex-wrap justify-center gap-2">
                    {SUGGESTED_QUERIES.map((suggestion) => (
                      <button
                        key={suggestion}
                        onClick={() => handleSuggestion(suggestion)}
                        className="text-xs px-3 py-1.5 rounded-full border hover:bg-muted transition-colors text-left"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {isLoading && (
              <div className="text-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground mx-auto mb-4" />
                <p className="text-sm text-muted-foreground">
                  Searching coaches and generating AI recommendations...
                </p>
              </div>
            )}

            {error && (
              <div className="text-center py-8">
                <p className="text-sm text-red-600 mb-2">Something went wrong</p>
                <p className="text-xs text-muted-foreground">{error}</p>
              </div>
            )}

            {hasSearched && !isLoading && !error && results.length === 0 && (
              <div className="text-center py-8">
                <p className="text-sm text-muted-foreground">
                  No matches found for &ldquo;{searchedQuery}&rdquo;. Try a broader search.
                </p>
              </div>
            )}

            {!isLoading && results.length > 0 && (
              <div className="space-y-4">
                <p className="text-xs text-muted-foreground">
                  {results.length} coach{results.length !== 1 ? 'es' : ''} recommended for &ldquo;{searchedQuery}&rdquo;
                </p>
                {results.map((coach, index) => (
                  <CoachResultCard key={coach.expert_id} coach={coach} rank={index + 1} />
                ))}
              </div>
            )}
          </div>
        </ScrollArea>
      </Card>
    </div>
  );
}
