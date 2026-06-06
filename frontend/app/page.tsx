'use client'

import { useState, useRef, useEffect, useCallback } from 'react'

type ScreenplayData = {
  title: string
  genre: string
  characters: Array<{ id: string; name: string; role: string; personality: string }>
  scenes: Array<{
    id: string
    heading: { location: string; time: string }
    participants: string[]
    objective: string
    dialogue: Array<{ speaker: string; content: string; emotion: string }>
  }>
  score?: { structure: number; dialogue: number; pacing: number; character_consistency: number; overall: number }
  consistency_report?: { passed: boolean; issues: string[]; issue_count: number }
}

const stages = ['解析章节', '提取角色', '分析剧情', '拆分场景', '生成对白', '组装剧本']
const MIN_CHAPTERS = 3
const API_BASE = 'http://localhost:8000'

export default function Home() {
  const [text, setText] = useState('')
  const [filename, setFilename] = useState('')
  const [loading, setLoading] = useState(false)
  const [yaml, setYaml] = useState('')
  const [data, setData] = useState<ScreenplayData | null>(null)
  const [error, setError] = useState('')
  const [modifyInstruction, setModifyInstruction] = useState('')
  const [modifying, setModifying] = useState(false)
  const [activeTab, setActiveTab] = useState<'yaml' | 'preview' | 'score'>('preview')
  const [elapsed, setElapsed] = useState(0)
  const [currentStage, setCurrentStage] = useState(-1)
  const [copied, setCopied] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 计时器
  useEffect(() => {
    if (loading) {
      setElapsed(0)
      setCurrentStage(0)
      const start = Date.now()
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - start) / 1000))
      }, 1000)
      // 模拟阶段推进
      const stageInterval = setInterval(() => {
        setCurrentStage(prev => {
          if (prev >= stages.length - 1) {
            clearInterval(stageInterval)
            return prev
          }
          return prev + 1
        })
      }, 15000)
      return () => {
        clearInterval(timerRef.current!)
        clearInterval(stageInterval)
      }
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [loading])

  function resetAll() {
    setText('')
    setFilename('')
    setYaml('')
    setData(null)
    setError('')
    setElapsed(0)
    setCurrentStage(-1)
  }

  async function handleSubmit() {
    if (!text.trim()) return
    setLoading(true)
    setError('')
    setYaml('')
    setData(null)
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 600000)
    try {
      const res = await fetch(`${API_BASE}/api/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        signal: controller.signal,
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '处理失败')
      }
      const result = await res.json()
      setYaml(result.yaml)
      setData(result.data)
    } catch (e: any) {
      if (e.name === 'AbortError') {
        setError('请求超时（10分钟），请减少章节数量后重试')
      } else {
        setError(e.message)
      }
    } finally {
      clearTimeout(timeoutId)
      setLoading(false)
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setFilename(file.name)
    const reader = new FileReader()
    reader.onload = (ev) => setText(ev.target?.result as string)
    reader.readAsText(file)
  }

  async function handleModify() {
    if (!modifyInstruction.trim() || !data) return
    setModifying(true)
    setError('')
    try {
      const res = await fetch(`${API_BASE}/api/modify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ screenplay_data: data, instruction: modifyInstruction }),
      })
      if (!res.ok) throw new Error('修改失败')
      const result = await res.json()
      setYaml(result.yaml)
      setData(result.data)
      setModifyInstruction('')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setModifying(false)
    }
  }

  function downloadYaml() {
    const blob = new Blob([yaml], { type: 'text/yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'screenplay.yaml'
    a.click()
    URL.revokeObjectURL(url)
  }

  async function copyYaml() {
    await navigator.clipboard.writeText(yaml)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Ctrl+Enter / Cmd+Enter 提交
  function handleKeyDown(e: React.KeyboardEvent) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      if (!loading && text.trim()) handleSubmit()
    }
  }

  // 检测章节数量
  const chapterCount = (text.match(/第[零一二三四五六七八九十百千\d]+章/g) || []).length
  const wordCount = text.length
  const canSubmit = !loading && text.trim() && wordCount >= 100

  function formatTime(seconds: number) {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return m > 0 ? `${m}分${s}秒` : `${s}秒`
  }

  return (
    <main className="max-w-7xl mx-auto p-4 md:p-8">
      {/* Header */}
      <header className="text-center mb-8">
        <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
          AI Novel To Screenplay
        </h1>
        <p className="text-gray-400 mt-2">将多章节小说自动转换为结构化 YAML 剧本</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 左侧: 输入区 */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-200">小说输入</h2>
            <div className="flex gap-2">
              {text && (
                <button
                  onClick={resetAll}
                  className="px-3 py-1.5 text-sm rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 border border-gray-700 transition-colors"
                >
                  清空
                </button>
              )}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-3 py-1.5 text-sm rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 transition-colors"
              >
                {filename ? filename : '上传文件'}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.md"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>
          </div>

          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="在此粘贴小说文本（支持 ≥3 章节，自动识别章节标记）...&#10;提示：Ctrl+Enter 快速提交"
            className="w-full h-80 p-4 rounded-xl bg-gray-900 border border-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-y text-sm font-mono text-gray-200 placeholder-gray-600"
          />

          <div className="flex items-center gap-3 flex-wrap">
            <span className={`text-xs ${wordCount >= 100 ? 'text-green-500' : 'text-gray-500'}`}>
              已输入 {wordCount} 字
            </span>
            {chapterCount > 0 && (
              <span className={`text-xs ${chapterCount >= MIN_CHAPTERS ? 'text-green-500' : 'text-yellow-500'}`}>
                检测到 {chapterCount} 章{chapterCount < MIN_CHAPTERS ? ' (建议≥3章)' : ''}
              </span>
            )}
            <button
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="ml-auto px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 font-medium transition-colors"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  处理中 {formatTime(elapsed)}
                  <span className="typing-dot">●</span>
                  <span className="typing-dot">●</span>
                  <span className="typing-dot">●</span>
                </span>
              ) : (
                '开始转换'
              )}
            </button>
          </div>

          {/* 进度提示 */}
          {loading && (
            <div className="p-4 rounded-xl bg-gray-900 border border-gray-700">
              <p className="text-sm text-blue-400 mb-3">Agent 工作流执行中...（已耗时 {formatTime(elapsed)}）</p>
              <div className="flex flex-wrap gap-2">
                {stages.map((s, i) => (
                  <span
                    key={s}
                    className={`px-2 py-1 text-xs rounded transition-colors ${
                      i < currentStage
                        ? 'bg-green-900/50 text-green-400 border border-green-700/50'
                        : i === currentStage
                        ? 'bg-blue-900/50 text-blue-400 border border-blue-700/50 animate-pulse'
                        : 'bg-gray-800 text-gray-600'
                    }`}
                  >
                    {i < currentStage ? '✓ ' : i === currentStage ? '◉ ' : '○ '}
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-red-900/30 border border-red-700">
              <p className="text-red-300 text-sm mb-2">{error}</p>
              <button
                onClick={handleSubmit}
                className="text-xs text-red-400 hover:text-red-300 underline"
              >
                点击重试
              </button>
            </div>
          )}
        </section>

        {/* 右侧: 输出区 */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-200">剧本输出</h2>
            <div className="flex gap-1">
              {(['preview', 'yaml', 'score'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1 text-xs rounded-lg transition-colors ${
                    activeTab === tab
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {tab === 'preview' ? '预览' : tab === 'yaml' ? 'YAML' : '评分'}
                </button>
              ))}
              {yaml && (
                <>
                  <button
                    onClick={copyYaml}
                    className="ml-2 px-3 py-1 text-xs rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors"
                  >
                    {copied ? '已复制' : '复制'}
                  </button>
                  <button
                    onClick={downloadYaml}
                    className="px-3 py-1 text-xs rounded-lg bg-green-700 hover:bg-green-600 text-white transition-colors"
                  >
                    下载
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="h-96 overflow-auto rounded-xl bg-gray-900 border border-gray-700 p-4">
            {!yaml && !loading && (
              <div className="text-center mt-24">
                <p className="text-gray-600 text-sm">转换后的剧本将在此显示</p>
                <p className="text-gray-700 text-xs mt-2">支持粘贴文本或上传 txt/md 文件，至少 3 章</p>
              </div>
            )}

            {activeTab === 'yaml' && yaml && (
              <pre className="text-xs font-mono text-gray-300 whitespace-pre-wrap">{yaml}</pre>
            )}

            {activeTab === 'preview' && data && (
              <PreviewPane data={data} />
            )}

            {activeTab === 'score' && data?.score && (
              <ScorePane score={data.score} consistency={data.consistency_report} />
            )}

            {activeTab === 'score' && !data?.score && data && (
              <p className="text-gray-600 text-sm text-center mt-32">暂无评分数据</p>
            )}
          </div>

          {/* 多轮修改 */}
          {data && (
            <div className="flex gap-2">
              <input
                value={modifyInstruction}
                onChange={(e) => setModifyInstruction(e.target.value)}
                placeholder="修改指令，如：把第三场改成夜晚"
                className="flex-1 px-3 py-2 text-sm rounded-lg bg-gray-900 border border-gray-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 text-gray-200"
                onKeyDown={(e) => e.key === 'Enter' && handleModify()}
              />
              <button
                onClick={handleModify}
                disabled={modifying || !modifyInstruction.trim()}
                className="px-4 py-2 text-sm rounded-lg bg-purple-700 hover:bg-purple-600 disabled:bg-gray-700 disabled:text-gray-500 transition-colors"
              >
                {modifying ? '修改中...' : '修改'}
              </button>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}

function PreviewPane({ data }: { data: ScreenplayData }) {
  return (
    <div className="space-y-4 text-sm">
      <div className="border-b border-gray-800 pb-3">
        <h3 className="text-xl font-bold text-blue-300">{data.title || '未命名剧本'}</h3>
        <span className="text-xs text-gray-500">{data.genre || '未分类'}</span>
      </div>

      {data.characters?.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">角色 ({data.characters.length})</h4>
          <div className="flex flex-wrap gap-2">
            {data.characters.map((c) => (
              <span key={c.id} className="px-2 py-1 rounded-lg bg-gray-800 text-xs">
                <span className={c.role === 'protagonist' ? 'text-yellow-400' : c.role === 'antagonist' ? 'text-red-400' : 'text-gray-300'}>
                  {c.name}
                </span>
                <span className="text-gray-600 ml-1">({c.role})</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {data.scenes?.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">场景 ({data.scenes.length})</h4>
          <div className="space-y-3 max-h-64 overflow-auto">
            {data.scenes.map((scene) => (
              <div key={scene.id} className="p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-blue-400">{scene.id}</span>
                  <span className="text-xs text-gray-500">|</span>
                  <span className="text-sm text-gray-200">{scene.heading?.location}</span>
                  <span className="text-xs text-gray-500">· {scene.heading?.time}</span>
                </div>
                {scene.objective && <p className="text-xs text-gray-400 mb-1">{scene.objective}</p>}
                {scene.dialogue?.length > 0 && (
                  <div className="space-y-1 mt-2">
                    {scene.dialogue.slice(0, 3).map((d, i) => (
                      <p key={i} className="text-xs">
                        <span className="text-yellow-400">{data.characters.find(c => c.id === d.speaker)?.name || d.speaker}:</span>
                        <span className="text-gray-300 ml-1">{d.content}</span>
                        {d.emotion && <span className="text-gray-600 ml-1">[{d.emotion}]</span>}
                      </p>
                    ))}
                    {scene.dialogue.length > 3 && (
                      <p className="text-xs text-gray-600">...还有 {scene.dialogue.length - 3} 句对白</p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ScorePane({ score, consistency }: {
  score: ScreenplayData['score']
  consistency: ScreenplayData['consistency_report']
}) {
  if (!score) return null
  const items = [
    { label: '结构', value: score.structure },
    { label: '对白', value: score.dialogue },
    { label: '节奏', value: score.pacing },
    { label: '角色一致性', value: score.character_consistency },
    { label: '综合', value: score.overall },
  ]
  return (
    <div className="space-y-4 text-sm">
      <div className="grid grid-cols-2 gap-3">
        {items.map(({ label, value }) => (
          <div key={label} className="p-3 rounded-lg bg-gray-800">
            <div className="flex justify-between items-center mb-1">
              <span className="text-gray-400">{label}</span>
              <span className={`font-bold ${value >= 80 ? 'text-green-400' : value >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
                {value}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-gray-700">
              <div
                className={`h-full rounded-full transition-all ${
                  value >= 80 ? 'bg-green-500' : value >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${value}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      {consistency && (
        <div className={`p-3 rounded-lg ${consistency.passed ? 'bg-green-900/20 border border-green-700/50' : 'bg-red-900/20 border border-red-700/50'}`}>
          <span className={consistency.passed ? 'text-green-400' : 'text-red-400'}>
            {consistency.passed ? '✓ 一致性检查通过' : `✗ ${consistency.issue_count} 个一致性问题`}
          </span>
          {consistency.issues?.length > 0 && (
            <ul className="mt-2 space-y-1">
              {consistency.issues.map((issue: string, i: number) => (
                <li key={i} className="text-xs text-red-300/70">{issue}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
