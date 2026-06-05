import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Novel To Screenplay',
  description: 'AI 小说转剧本工具 - 将多章节小说自动转换为结构化YAML剧本',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="bg-gray-950 text-gray-100 min-h-screen">{children}</body>
    </html>
  )
}
