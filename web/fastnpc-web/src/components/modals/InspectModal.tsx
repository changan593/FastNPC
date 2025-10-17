interface InspectModalProps {
  show: boolean
  text: string
  onClose: () => void
}

export function InspectModal({ show, text, onClose }: InspectModalProps) {
  if (!show) return null

  return (
    <div className="modal" onClick={onClose}>
      <div
        className="dialog"
        onClick={e => e.stopPropagation()}
        style={{ width: '80vw', maxWidth: '1200px', height: '70vh', display: 'flex', flexDirection: 'column' }}
      >
        <h3>最终发送内容</h3>
        <pre className="json-view" style={{ flex: 1, overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {text}
        </pre>
        <div className="actions">
          <button
            onClick={() => {
              navigator.clipboard?.writeText(text).catch(() => {})
            }}
          >
            复制
          </button>
          <button className="primary" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>
    </div>
  )
}

