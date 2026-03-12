import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Camelback Ventures | Alumni Intelligence',
  description: 'Alumni portfolio intelligence dashboard',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
