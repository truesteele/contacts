import type { Metadata } from 'next'
import { DM_Sans, DM_Serif_Display, JetBrains_Mono } from 'next/font/google'
import './globals.css'

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
})

const dmSerif = DM_Serif_Display({
  weight: '400',
  subsets: ['latin'],
  variable: '--font-dm-serif',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'SFEF × True Steele — Sprint Tracker',
  description: 'Fundraising Intelligence Sprint for SF Education Fund',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${dmSans.variable} ${dmSerif.variable} ${jetbrainsMono.variable} font-sans antialiased`}>
        <div className="min-h-screen bg-[hsl(40,20%,98%)]">
          <header className="sticky top-0 z-40 bg-white/60 backdrop-blur-sm border-b border-border/40">
            <div className="max-w-5xl mx-auto px-6 py-3">
              <span className="text-xs font-semibold tracking-widest text-muted-foreground/60 uppercase">
                True Steele Labs
              </span>
            </div>
          </header>
          <main className="max-w-5xl mx-auto px-6 py-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
