import type { Metadata } from 'next'
import Sidebar from '@/components/Sidebar'
import './globals.css'

export const metadata: Metadata = {
  title: { default: 'AcquireOS', template: '%s · AcquireOS' },
  description: 'Outbound pipeline system — infrastructure, cadence, copy and data planners.',
  // Internal tooling. Nothing here should be indexed.
  robots: { index: false, follow: false, nocache: true },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <div className="flex min-h-screen flex-col lg:flex-row">
          <Sidebar />
          <main className="min-w-0 flex-1">
            <div className="mx-auto max-w-[1120px] px-5 py-8 sm:px-8 lg:px-12 lg:py-11">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  )
}
