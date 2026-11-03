import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import { MAX_RECORD_SECONDS, toWav16k } from '../lib/media'
import { usePrefs } from '../context/PrefsContext'
import { Modal } from './ui'
import Icon from './Icon'

type Phase = 'ask' | 'recording' | 'processing' | 'error'

/** Voice search: record up to 12 s -> 16 kHz WAV -> Gemini transcribes (Vietnamese or English) -> normal search. */
export default function VoiceSearch({ onClose }: { onClose: () => void }) {
  const nav = useNavigate()
  const { track } = usePrefs()
  const [phase, setPhase] = useState<Phase>('ask')
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [heard, setHeard] = useState('')
  const rec = useRef<MediaRecorder | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const chunks = useRef<Blob[]>([])
  const timer = useRef<ReturnType<typeof setInterval>>(undefined)
  const cancelled = useRef(false)

  const release = useCallback(() => {
    clearInterval(timer.current)
    stream.current?.getTracks().forEach((t) => t.stop())
    stream.current = null
  }, [])
  useEffect(() => () => { cancelled.current = true; release(); if (rec.current?.state === 'recording') rec.current.stop() }, [release])

  const fail = (msg: string) => { release(); setError(msg); setPhase('error') }

  const stop = () => { if (rec.current?.state === 'recording') rec.current.stop() }

  const start = async () => {
    setError(null); setSeconds(0)
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') return fail('Trình duyệt này chưa hỗ trợ ghi âm. Hãy dùng Chrome, Edge, Firefox hoặc Safari mới.')
    try { stream.current = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } }) }
    catch (e) {
      const name = e instanceof DOMException ? e.name : ''
      return fail(name === 'NotAllowedError' ? 'Bạn chưa cho phép dùng micro. Hãy bật quyền micro cho trang này rồi thử lại.' : name === 'NotFoundError' ? 'Không tìm thấy micro trên thiết bị.' : 'Không mở được micro.')
    }
    chunks.current = []
    const r = new MediaRecorder(stream.current)
    rec.current = r
    r.ondataavailable = (e) => e.data.size && chunks.current.push(e.data)
    r.onstop = async () => {
      release()
      if (cancelled.current) return
      setPhase('processing')
      try {
        const wav = await toWav16k(new Blob(chunks.current, { type: r.mimeType }))
        const res = await api.upload<{ text: string; language: string }>('/search/voice', wav)
        setHeard(res.text)
        track('SEARCH', { keyword: res.text })
        setTimeout(() => { onClose(); nav(`/san-pham?q=${encodeURIComponent(res.text)}&via=voice`) }, 700)
      } catch (e) { fail(errorMessage(e)) }
    }
    r.start()
    setPhase('recording')
    timer.current = setInterval(() => setSeconds((s) => {
      if (s + 1 >= MAX_RECORD_SECONDS) stop()
      return s + 1
    }), 1000)
  }

  return (
    <Modal title="Tìm kiếm bằng giọng nói" onClose={onClose}>
      <div className="flex flex-col items-center gap-4 py-2 text-center">
        {phase === 'ask' && (<>
          <p className="text-sm text-slate-600">Nhấn nút micro rồi nói điều bạn cần, ví dụ: <i>“giày chạy bộ màu đen dưới 1 triệu”</i>. Hỗ trợ tiếng Việt và tiếng Anh.</p>
          <button className="grid h-20 w-20 place-items-center rounded-full bg-brand-600 text-white shadow-lg hover:bg-brand-700" onClick={start} aria-label="Bắt đầu ghi âm"><Icon name="mic" size={36} /></button>
          <p className="text-xs text-slate-400">Đoạn ghi âm được gửi tới Google Gemini để chuyển thành chữ, không được UniCart lưu lại.</p>
        </>)}
        {phase === 'recording' && (<>
          <button className="relative grid h-20 w-20 place-items-center rounded-full bg-rose-600 text-2xl text-white shadow-lg" onClick={stop} aria-label="Dừng ghi âm">
            <span className="absolute inset-0 animate-ping rounded-full bg-rose-500/40" aria-hidden /><span className="relative">⏹</span>
          </button>
          <p className="text-sm font-medium" role="timer">Đang nghe… {seconds}s / {MAX_RECORD_SECONDS}s</p>
          <p className="text-xs text-slate-500">Nói xong thì nhấn nút để dừng.</p>
        </>)}
        {phase === 'processing' && (heard ? (
          <div><p className="text-xs text-slate-500">Bạn đã nói</p><p className="mt-1 text-lg font-semibold text-slate-900">“{heard}”</p><p className="mt-2 text-sm text-slate-500">Đang tìm sản phẩm…</p></div>
        ) : (<>
          <span className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" aria-hidden />
          <p className="text-sm text-slate-600" role="status">Đang nhận dạng giọng nói…</p>
        </>))}
        {phase === 'error' && (<>
          <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700" role="alert">{error}</p>
          <button className="btn-primary" onClick={() => { setPhase('ask'); setHeard('') }}>Thử lại</button>
        </>)}
      </div>
    </Modal>
  )
}
