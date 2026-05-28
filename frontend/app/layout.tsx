import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Branch — fork conversations on an infinite canvas',
  description:
    'Branch is a spatial AI workspace: fork any message into a new thread on an infinite canvas and merge insights back when you\'re done.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
