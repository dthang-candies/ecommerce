/** Browser-side preparation of audio and images for AI search: small, standard formats, nothing stored. */

export const MAX_RECORD_SECONDS = 12

function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const buf = new ArrayBuffer(44 + samples.length * 2)
  const v = new DataView(buf)
  const str = (o: number, s: string) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)))
  str(0, 'RIFF'); v.setUint32(4, 36 + samples.length * 2, true); str(8, 'WAVE'); str(12, 'fmt ')
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true)
  v.setUint32(24, sampleRate, true); v.setUint32(28, sampleRate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true)
  str(36, 'data'); v.setUint32(40, samples.length * 2, true)
  samples.forEach((s, i) => v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, s)) * 0x7fff, true))
  return new Blob([buf], { type: 'audio/wav' })
}

/** MediaRecorder output (webm/opus on Chrome, mp4 on Safari…) -> 16 kHz mono WAV, which every browser can make and Gemini accepts. */
export async function toWav16k(blob: Blob): Promise<Blob> {
  const ctx = new AudioContext()
  try {
    const decoded = await ctx.decodeAudioData(await blob.arrayBuffer())
    const offline = new OfflineAudioContext(1, Math.max(1, Math.ceil(decoded.duration * 16000)), 16000)
    const src = offline.createBufferSource()
    src.buffer = decoded
    src.connect(offline.destination)
    src.start()
    return encodeWav((await offline.startRendering()).getChannelData(0), 16000)
  } finally { void ctx.close() }
}

/** Shrinks a photo to <= 1024 px JPEG (faster upload, less quota, and no EXIF/location is sent). */
export async function prepareImage(file: Blob): Promise<Blob> {
  if (!file.type.startsWith('image/')) throw new Error('Vui lòng chọn một tệp ảnh')
  if (file.size > 20 * 1024 * 1024) throw new Error('Ảnh quá lớn (tối đa 20 MB)')
  let bmp: ImageBitmap
  try { bmp = await createImageBitmap(file) } catch { throw new Error('Không đọc được ảnh này. Hãy dùng ảnh JPEG, PNG hoặc WebP.') }
  const scale = Math.min(1, 1024 / Math.max(bmp.width, bmp.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(bmp.width * scale)); canvas.height = Math.max(1, Math.round(bmp.height * scale))
  const g = canvas.getContext('2d')!
  g.fillStyle = '#fff'; g.fillRect(0, 0, canvas.width, canvas.height)         // transparent PNGs become white, not black
  g.drawImage(bmp, 0, 0, canvas.width, canvas.height)
  bmp.close()
  return new Promise((res, rej) => canvas.toBlob((b) => (b ? res(b) : rej(new Error('Không xử lý được ảnh'))), 'image/jpeg', 0.85))
}
