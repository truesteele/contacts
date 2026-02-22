'use client';

import { useState, useRef, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { ArrowLeft, Search, Copy, Check, Mail, Database, Loader2, ExternalLink } from 'lucide-react';
import Link from 'next/link';

interface EmailResult {
  email: string;
  source: 'database' | 'gmail' | 'tomba';
  type: string;
  confidence: number;
  details?: string;
}

interface LookupResult {
  contact: {
    name: string | null;
    company: string | null;
    title: string | null;
    headline: string | null;
    linkedin_url: string | null;
    profile_pic: string | null;
  } | null;
  emails: EmailResult[];
  gmail_searched: boolean;
  tomba_searched: boolean;
  in_database: boolean;
  gmail_candidates_found?: number;
  message?: string;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="min-w-[36px] min-h-[36px] flex items-center justify-center rounded-md hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
      title="Copy email"
    >
      {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
    </button>
  );
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  let color = 'bg-gray-100 text-gray-600';
  if (confidence >= 90) color = 'bg-green-100 text-green-700';
  else if (confidence >= 70) color = 'bg-yellow-100 text-yellow-700';
  else if (confidence >= 50) color = 'bg-orange-100 text-orange-700';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {confidence}%
    </span>
  );
}

function SourceBadge({ source }: { source: 'database' | 'gmail' | 'tomba' }) {
  if (source === 'database') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
        <Database className="w-3 h-3" />
        Database
      </span>
    );
  }
  if (source === 'tomba') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
        <Search className="w-3 h-3" />
        Tomba
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-50 text-purple-700">
      <Mail className="w-3 h-3" />
      Gmail
    </span>
  );
}

export default function EmailLookupPage() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LookupResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;

    // Basic validation
    if (!trimmed.includes('linkedin.com/in/')) {
      setError('Please enter a valid LinkedIn profile URL (e.g., linkedin.com/in/username)');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch('/api/email-lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ linkedin_url: trimmed }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.error || `Server error (${res.status})`);
      }

      const data: LookupResult = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setUrl('');
    setResult(null);
    setError(null);
    inputRef.current?.focus();
  }

  return (
    <div className="min-h-dvh bg-background flex flex-col">
      {/* Header */}
      <div className="page-header mx-4 mt-4">
        <Link href="/" className="page-back" aria-label="Back to dashboard">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center text-violet-600">
          <Mail className="w-4 h-4" />
        </div>
        <h1 className="text-lg font-semibold tracking-tight">Email Finder</h1>
      </div>

      <div className="flex-1 px-4 py-6 max-w-lg mx-auto w-full space-y-4">
        {/* Search form */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
            <input
              ref={inputRef}
              type="text"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="linkedin.com/in/username"
              className="w-full pl-10 pr-4 py-3 text-base border rounded-lg bg-card focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
              autoComplete="off"
              disabled={loading}
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading || !url.trim()}
              className="flex-1 min-h-[44px] px-4 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium text-sm hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Searching...
                </>
              ) : (
                'Find Email'
              )}
            </button>
            {(result || error) && (
              <button
                type="button"
                onClick={handleClear}
                className="min-h-[44px] px-4 py-2.5 border rounded-lg text-sm text-muted-foreground hover:bg-secondary transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        </form>

        {/* Error */}
        {error && (
          <div className="px-4 py-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Loading hint */}
        {loading && (
          <div className="text-center text-sm text-muted-foreground py-4">
            Checking database, Gmail, and Tomba...
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-3">
            {/* Contact info */}
            {result.contact && (
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    {result.contact.profile_pic ? (
                      <img
                        src={result.contact.profile_pic}
                        alt=""
                        className="w-12 h-12 rounded-full object-cover bg-muted flex-shrink-0"
                        onError={e => {
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                      />
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center text-lg font-semibold flex-shrink-0">
                        {(result.contact.name || '?')
                          .split(' ')
                          .map(w => w[0])
                          .join('')
                          .toUpperCase()
                          .slice(0, 2)}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-base truncate">{result.contact.name}</h3>
                        {result.contact.linkedin_url && (
                          <a
                            href={result.contact.linkedin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-muted-foreground/50 hover:text-blue-600 flex-shrink-0"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>
                      {(result.contact.title || result.contact.company) && (
                        <p className="text-sm text-muted-foreground truncate">
                          {result.contact.title || ''}
                          {result.contact.title && result.contact.company ? ' @ ' : ''}
                          {result.contact.company || ''}
                        </p>
                      )}
                      {result.contact.headline &&
                        result.contact.headline !== result.contact.title && (
                          <p className="text-xs text-muted-foreground/70 truncate mt-0.5">
                            {result.contact.headline}
                          </p>
                        )}
                    </div>
                  </div>
                  {result.in_database && (
                    <div className="mt-2 pt-2 border-t">
                      <span className="text-xs text-green-600 font-medium">In your network</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Emails found */}
            {result.emails.length > 0 ? (
              <Card>
                <CardContent className="p-4 space-y-3">
                  <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                    Email{result.emails.length > 1 ? 's' : ''} Found
                  </h4>
                  {result.emails.map((em, i) => (
                    <div key={i} className="flex items-center gap-2 py-1">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-sm font-medium break-all">
                            {em.email}
                          </span>
                          <ConfidenceBadge confidence={em.confidence} />
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <SourceBadge source={em.source} />
                          <span className="text-xs text-muted-foreground capitalize">{em.type}</span>
                        </div>
                        {em.details && (
                          <p className="text-xs text-muted-foreground mt-1">{em.details}</p>
                        )}
                      </div>
                      <CopyButton text={em.email} />
                    </div>
                  ))}
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="p-4 text-center text-sm text-muted-foreground">
                  <p>
                    No email found
                    {result.gmail_searched || result.tomba_searched
                      ? ` after checking ${[
                          result.in_database && 'database',
                          result.gmail_searched && 'Gmail',
                          result.tomba_searched && 'Tomba',
                        ].filter(Boolean).join(', ')}.`
                      : '.'}
                  </p>
                  {result.gmail_candidates_found ? (
                    <p className="mt-1 text-xs">
                      {result.gmail_candidates_found} Gmail candidate{result.gmail_candidates_found > 1 ? 's' : ''} checked, none passed verification.
                    </p>
                  ) : null}
                  {result.message && <p className="mt-1 text-xs">{result.message}</p>}
                </CardContent>
              </Card>
            )}

            {/* Search info */}
            {(result.gmail_searched || result.tomba_searched) && (
              <p className="text-xs text-center text-muted-foreground">
                {[
                  result.gmail_searched && '5 Gmail accounts',
                  result.tomba_searched && 'Tomba API',
                ].filter(Boolean).join(' + ')} searched
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
