import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "True Steele Labs | Projects",
  description: "Project trackers by True Steele Labs",
};

export default function ProjectsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border/50 bg-white/60 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center">
          <span className="text-sm font-medium tracking-widest uppercase text-muted-foreground/70">
            True Steele Labs
          </span>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-6 py-8">
        {children}
      </main>
    </div>
  );
}
