'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, Loader2, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface CSVExport {
  csv_content: string;
  filename: string;
}

const SUGGESTED_QUERIES = [
  'Who should I invite to the Outdoorithm fundraiser?',
  'Who cares about outdoor equity in my network?',
  'Find Kindora enterprise prospects in my inner circle',
  'Who are the top donors in my close network?',
  'Find people similar to Fred Blackwell',
  'Who works in philanthropy tech?',
];

export function NetworkIntelligence() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [csvExports, setCSVExports] = useState<CSVExport[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const downloadCSV = (csvExport: CSVExport) => {
    const blob = new Blob([csvExport.csv_content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = csvExport.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const sendMessage = async (messageContent?: string) => {
    const content = messageContent || input;
    if (!content.trim()) return;

    const userMessage: Message = { role: 'user', content };
    const newMessages = [...messages, userMessage];

    setMessages(newMessages);
    if (!messageContent) setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/network-intel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newMessages }),
      });

      if (!response.ok) throw new Error('Failed to send message');

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error('No reader available');

      let assistantMessage = '';
      setMessages([...newMessages, { role: 'assistant', content: '' }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') break;

            try {
              const parsed = JSON.parse(data);

              if (parsed.text) {
                assistantMessage += parsed.text;
                setMessages([...newMessages, { role: 'assistant', content: assistantMessage }]);
              } else if (parsed.tool_use) {
                const toolInfo = `\n\n*Searching: ${parsed.tool_use.name}*\n`;
                assistantMessage += toolInfo;
                setMessages([...newMessages, { role: 'assistant', content: assistantMessage }]);
              } else if (parsed.csv_export) {
                setCSVExports((prev) => [...prev, parsed.csv_export]);
              }
            } catch {
              // Skip invalid JSON
            }
          }
        }
      }
    } catch (error) {
      console.error('Network Intel error:', error);
      setMessages([
        ...newMessages,
        { role: 'assistant', content: 'Sorry, there was an error processing your request.' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="mb-4">
        <h2 className="text-2xl font-bold mb-1">Network Intelligence</h2>
        <p className="text-muted-foreground text-sm">
          Search, analyze, and activate your professional network with AI
        </p>
      </div>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            {messages.length === 0 && (
              <div className="py-8">
                <p className="text-center text-muted-foreground mb-6">
                  Ask me anything about your network — who to invite, who cares about a topic, outreach strategy, and more.
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {SUGGESTED_QUERIES.map((query) => (
                    <button
                      key={query}
                      onClick={() => sendMessage(query)}
                      disabled={isLoading}
                      className="px-3 py-1.5 text-sm rounded-full border bg-background hover:bg-muted transition-colors text-left"
                    >
                      {query}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-4 ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  }`}
                >
                  {message.role === 'assistant' ? (
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-lg p-4">
                  <Loader2 className="w-5 h-5 animate-spin" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {csvExports.length > 0 && (
          <div className="border-t px-4 py-2 flex gap-2 flex-wrap">
            {csvExports.map((exp, i) => (
              <Button
                key={i}
                variant="outline"
                size="sm"
                onClick={() => downloadCSV(exp)}
                className="flex items-center gap-1"
              >
                <Download className="w-3 h-3" />
                {exp.filename}
              </Button>
            ))}
          </div>
        )}

        <div className="border-t p-4">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your network..."
              className="flex-1 px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none min-h-[48px] max-h-[200px] text-sm"
              disabled={isLoading}
              rows={1}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  handleSubmit(e as any);
                }
                if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
                  e.preventDefault();
                  handleSubmit(e as any);
                }
              }}
            />
            <Button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="self-end"
            >
              <Send className="w-4 h-4" />
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}
