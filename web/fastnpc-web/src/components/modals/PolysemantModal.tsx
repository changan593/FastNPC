interface PolysemantModalProps {
  show: boolean
  onClose: () => void
  newRole: string
  polyOptions: { text: string; href: string; snippet?: string }[]
  polyLoading: boolean
  polyRoute: string
  polyChoiceIdx: number | null
  setPolyChoiceIdx: (idx: number | null) => void
  setPolyChoiceHref: (href: string) => void
  onConfirm: () => void
}

export function PolysemantModal({
  show,
  onClose,
  newRole,
  polyOptions,
  polyLoading,
  polyRoute,
  polyChoiceIdx,
  setPolyChoiceIdx,
  setPolyChoiceHref,
  onConfirm,
}: PolysemantModalProps) {
  if (!show) return null

  return (
    <div className="modal" style={{ alignItems: 'center', justifyContent: 'center' }}>
      <div className="dialog" style={{ width: '80vw', maxWidth: '1200px', height: '70vh', display: 'flex', flexDirection: 'column' }}>
        <h3>选择同名词条</h3>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '8px 0' }}>
          <span style={{ fontSize: 16, fontWeight: 500 }}>🎭 {newRole}</span>
          <span className="muted">{polyLoading ? '加载中…' : `共 ${polyOptions.length} 项`}</span>
          {polyRoute ? <span className="muted" style={{ marginLeft: 8 }}>来源: {polyRoute}</span> : null}
        </div>
        <div style={{ flex: 1, overflow: 'auto', marginTop: 8 }}>
          {/* 多列卡片布局：点击文本块即可选择，选中高亮 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
            {polyOptions.map((it: any, idx: number) => {
              const selected = polyChoiceIdx === idx
              return (
                <div
                  key={idx}
                  onClick={() => {
                    setPolyChoiceIdx(idx)
                    setPolyChoiceHref(it.href)
                  }}
                  style={{
                    border: '1px solid',
                    borderColor: selected ? '#2563eb' : '#e5e7eb',
                    background: selected ? 'rgba(37,99,235,0.06)' : 'white',
                    borderRadius: 8,
                    padding: 12,
                    cursor: 'pointer',
                    transition: 'border-color .15s ease, background .15s ease',
                  }}
                >
                  <div style={{ fontWeight: 600, lineHeight: 1.5, wordBreak: 'break-word', whiteSpace: 'normal' }}>{it.text}</div>
                  {it.snippet ? <div className="muted" style={{ marginTop: 4, fontSize: 12, lineHeight: 1.5, wordBreak: 'break-word' }}>{it.snippet}</div> : null}
                  {it.href ? (
                    <div className="muted" style={{ marginTop: 6, fontSize: 12, wordBreak: 'break-all' }}>
                      <a href={it.href} target="_blank" rel="noreferrer">
                        {it.href}
                      </a>
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>
        </div>
        <div className="actions">
          <button onClick={onClose}>取消</button>
          <button className="primary" onClick={onConfirm} disabled={polyChoiceIdx === null}>
            选择
          </button>
        </div>
      </div>
    </div>
  )
}

