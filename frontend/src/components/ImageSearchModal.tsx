import { useNavigate } from 'react-router-dom'
import ImagePicker from './ImagePicker'
import { Modal } from './ui'

export default function ImageSearchModal({ onClose }: { onClose: () => void }) {
  const nav = useNavigate()
  return (
    <Modal title="Tìm kiếm bằng hình ảnh" onClose={onClose}>
      <ImagePicker compact onPick={(file) => { onClose(); nav('/tim-kiem-anh', { state: { file } }) }} />
    </Modal>
  )
}
