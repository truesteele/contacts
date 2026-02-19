'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Upload, Send, Loader2, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [jobDescription, setJobDescription] = useState<string>('');
  const [uploadedFile, setUploadedFile] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        setJobDescription(data.text);
        setUploadedFile(data.filename);

        // Automatically start search
        const userMessage = `I've uploaded a job description: "${data.filename}". Please analyze it and find the best candidates from my network.`;
        setMessages([{ role: 'user', content: userMessage }]);
        await sendMessage(userMessage, data.text);
      } else {
        alert('Failed to upload PDF: ' + data.error);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Failed to upload file');
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async (messageContent?: string, jobDesc?: string) => {
    const content = messageContent || input;
    if (!content.trim()) return;

    const userMessage: Message = { role: 'user', content };
    const newMessages = messageContent ? [userMessage] : [...messages, userMessage];

    if (!messageContent) {
      setMessages(newMessages);
      setInput('');
    }

    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: newMessages,
          jobDescription: jobDesc || jobDescription,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No reader available');
      }

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

            if (data === '[DONE]') {
              break;
            }

            try {
              const parsed = JSON.parse(data);

              if (parsed.text) {
                assistantMessage += parsed.text;
                setMessages([...newMessages, { role: 'assistant', content: assistantMessage }]);
              } else if (parsed.tool_use) {
                // Show tool usage in the interface
                const toolInfo = `\n\n*Using tool: ${parsed.tool_use.name}*\n`;
                assistantMessage += toolInfo;
                setMessages([...newMessages, { role: 'assistant', content: assistantMessage }]);
              }
            } catch (e) {
              // Skip invalid JSON
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
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
        <h2 className="text-2xl font-bold mb-2">AI Job Search Agent</h2>
        <p className="text-muted-foreground">
          Upload a job description or describe the role you're looking to fill
        </p>
        {uploadedFile && (
          <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
            <FileText className="w-4 h-4" />
            <span>{uploadedFile}</span>
          </div>
        )}
      </div>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
                <p className="text-lg mb-4">Get started by uploading a job description</p>
                <p className="text-sm">Or describe the role you're hiring for</p>
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

        <div className="border-t p-4">
          <form onSubmit={handleSubmit} className="flex flex-col gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileUpload}
              className="hidden"
            />

            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
              >
                <Upload className="w-4 h-4 mr-2" />
                Upload PDF
              </Button>

              <div className="flex-1 text-sm text-muted-foreground flex items-center px-2">
                Or paste job description below
              </div>
            </div>

            <div className="flex gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Paste job description here or ask a question...

Examples:
• Copy/paste full job description from website
• 'Find candidates for a VP of Data role in Mountain View with philanthropy experience'
• 'Search for grants managers in the Bay Area with Salesforce skills'"
                className="flex-1 px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-y min-h-[100px] max-h-[400px] font-mono text-sm"
                disabled={isLoading}
                onKeyDown={(e) => {
                  // Submit on Cmd/Ctrl+Enter, allow normal Enter for new lines
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
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
            </div>

            <div className="text-xs text-muted-foreground">
              💡 Tip: Paste full job descriptions or use Cmd+Enter to send
            </div>
          </form>
        </div>
      </Card>
    </div>
  );
}
