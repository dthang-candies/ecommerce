import { useEffect, useRef, useState, type DragEvent } from 'react'
import Icon from './Icon'

/** Choose / drop / paste / photograph an image. Calls onPick with the File. */
export default function ImagePicker({ onPick, compact }: { onPick: (f: File) => void; compact?: boolean }) {
  const input = useRef<HTMLInputElement>(null)
  const camera = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)

  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const f = [...(e.clipboardData?.files ?? [])].find((x) => x.type.startsWith('image/'))
      if (f) { e.preventDefault(); onPick(f) }
    }
    document.addEventListener('paste', onPaste)
    return () => document.removeEventListener('paste', onPaste)
  }, [onPick])

  const drop = (e: DragEvent) => {
    e.preventDefault(); setOver(false)
    const f = [...e.dataTransfer.files].find((x) => x.type.startsWith('image/'))
    if (f) onPick(f)
  }
  const chosen = (e: React.ChangeEvent<HTMLInputElement>) => { const f = e.target.files?.[0]; if (f) onPick(f); e.target.value = '' }

  return (
    <div>
      <div onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)} onDrop={drop}
        className={`flex flex-col items-center gap-3 rounded-2xl border-2 border-dashed p-6 text-center transition ${over ? 'border-brand-600 bg-brand-50' : 'border-slate-300 bg-slate-50'} ${compact ? '' : 'py-12'}`}>
        <Icon name="image" size={40} className="text-slate-400" strokeWidth={1.5} />
        <p className="text-sm text-slate-600">Kéo thả ảnh vào đây, dán ảnh (Ctrl/⌘ + V) hoặc chọn từ thiết bị</p>
        <div className="flex flex-wrap justify-center gap-2">
          <button type="button" className="btn-primary" onClick={() => input.current?.click()}>Chọn ảnh</button>
          <button type="button" className="btn-secondary" onClick={() => camera.current?.click()}><Icon name="camera" size={18} />Chụp ảnh</button>
        </div>
        <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={chosen} aria-label="Chọn ảnh" />
        <input ref={camera} type="file" accept="image/*" capture="environment" className="sr-only" onChange={chosen} aria-label="Chụp ảnh" />
      </div>
      <p className="mt-2 text-center text-xs text-slate-400">Ảnh được thu nhỏ trên máy bạn và gửi tới Google Gemini để nhận diện sản phẩm, không được UniCart lưu lại.</p>
    </div>
  )
}
