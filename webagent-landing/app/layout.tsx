import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'WebAgent - The Agentic Web is Here',
  description: 'WebAgent is a fully autonomous AI agent that can understand any website, create a plan, and execute complex tasks on your behalf.',
  keywords: 'AI agent, web automation, autonomous AI, website understanding, task execution',
  authors: [{ name: 'WebAgent Team' }],
  creator: 'WebAgent',
  publisher: 'WebAgent',
  robots: 'index, follow',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://webagentapp.com',
    title: 'WebAgent - The Agentic Web is Here',
    description: 'WebAgent is a fully autonomous AI agent that can understand any website, create a plan, and execute complex tasks on your behalf.',
    siteName: 'WebAgent',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'WebAgent - The Agentic Web is Here',
    description: 'WebAgent is a fully autonomous AI agent that can understand any website, create a plan, and execute complex tasks on your behalf.',
    creator: '@webagentapp',
  },
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#2563eb',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <head>
        <link rel="icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
        <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
        <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
        <link rel="manifest" href="/site.webmanifest" />
      </head>
      <body className="antialiased bg-white text-gray-900">
        {children}
      </body>
    </html>
  )
}
