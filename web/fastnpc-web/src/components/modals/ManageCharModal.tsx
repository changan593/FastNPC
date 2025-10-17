interface ManageCharModalProps {
  show: boolean
  onClose: () => void
  activeRole: string
}

export function ManageCharModal({ show, onClose, activeRole }: ManageCharModalProps) {
  if (!show) return null

  return (
    <div className="modal" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h3>管理角色</h3>
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ marginBottom: 8 }}>角色配置</h4>
          <div style={{ padding: 12, border: '1px solid #e5e7eb', borderRadius: 8 }}>
            <a
              href={`/structured/view?role=${encodeURIComponent(activeRole)}`}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'block',
                padding: '10px 16px',
                background: '#3b82f6',
                color: 'white',
                textAlign: 'center',
                borderRadius: 8,
                textDecoration: 'none',
                fontSize: 14,
              }}
            >
              🔧 打开角色配置页面
            </a>
            <div style={{ marginTop: 12, fontSize: 12, color: '#666', lineHeight: 1.6 }}>在配置页面可以查看和编辑角色的详细信息、性格设定、记忆等内容</div>
          </div>
        </div>
        <div className="actions" style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button onClick={onClose}>关闭</button>
        </div>
      </div>
    </div>
  )
}

