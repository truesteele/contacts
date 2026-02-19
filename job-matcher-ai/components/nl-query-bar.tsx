'use client';

import { useState, useCallback, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Search, Loader2, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

interface NLQueryBarProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

const SUGGESTED_QUERIES = [
  'Who should I invite to the Outdoorithm fundraiser?',
  'Find Kindora enterprise prospects in my inner circle',
  'Who cares about outdoor equity?',
  'Top donors in my close network',
  'People in philanthropy tech',
];

export function NLQueryBar({ onSearch, isLoading }: NLQueryBarProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = useCallback(() => {
    const trimmed = query.trim();
    if (!trimmed || isLoading) return;
    onSearch(trimmed);
  }, [query, isLoading, onSearch]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleSuggestionClick = useCallback(
    (suggestion: string) => {
      setQuery(suggestion);
      onSearch(suggestion);
    },
    [onSearch]
  );

  return (
    <div className="space-y-3">
      <div className="relative">
        <div className="flex items-start gap-2 rounded-lg border bg-background p-2 shadow-sm focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-1 transition-all duration-200">
          <Sparkles className="w-5 h-5 mt-2 ml-1 text-muted-foreground shrink-0" />
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your network... e.g. 'Who should I invite to the fundraiser?'"
            className="flex-1 bg-transparent border-0 resize-none text-sm leading-relaxed placeholder:text-muted-foreground focus:outline-none min-h-[40px] max-h-[120px] py-1.5"
            rows={1}
            disabled={isLoading}
          />
          <Button
            onClick={handleSubmit}
            disabled={!query.trim() || isLoading}
            size="sm"
            className="shrink-0 mt-0.5"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            <span className="ml-1.5">Search</span>
          </Button>
        </div>
      </div>

      {!query && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-muted-foreground">Try:</span>
          {SUGGESTED_QUERIES.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => handleSuggestionClick(suggestion)}
              disabled={isLoading}
              className={cn(
                'text-xs px-2.5 py-1 rounded-full border bg-muted/50 text-muted-foreground',
                'hover:bg-muted hover:text-foreground hover:border-border',
                'transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
