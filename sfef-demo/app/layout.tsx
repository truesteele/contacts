import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SF Education Fund | Donor Intelligence Preview',
  description: 'Individual giving intelligence dashboard preview',
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
