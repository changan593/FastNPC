import type { MemberBrief } from '../types'
import { useAuth } from '../contexts/AuthContext'

interface InfoPanelProps {
  activeType: 'character' | 'group'
  activeRole: string
  activeGroupId: number | null
  charIntro: string
  groupMemberBriefs: MemberBrief[]
  onManageCharacter: () => void
  onManageGroup: () => void
  onShowFeedback: () => void
}

export function InfoPanel({
  activeType,
  activeRole,
  activeGroupId,
  charIntro,
  groupMemberBriefs,
  onManageCharacter,
  onManageGroup,
  onShowFeedback,
}: InfoPanelProps) {
  const { user } = useAuth()

  return (
    <aside className="group-info-panel">
      <div className="info-header">
        <h3>{activeType === 'character' ? '角色简介' : '成员简介'}</h3>
        <button className="manage-btn" onClick={activeType === 'character' ? onManageCharacter : onManageGroup}>
          管理
        </button>
      </div>
      <div className="info-content">
        {activeType === 'character' && activeRole ? (
          <div className="member-brief">
            <div className="member-name">🎭 {activeRole}</div>
            {charIntro ? (
              <div
                className="member-intro"
                style={{
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                  display: 'block',
                  WebkitLineClamp: 'unset',
                  WebkitBoxOrient: 'unset' as any,
                  overflow: 'visible',
                }}
              >
                {charIntro}
              </div>
            ) : (
              <div className="member-intro">暂无简介</div>
            )}
          </div>
        ) : activeType === 'group' && activeGroupId ? (
          groupMemberBriefs.map((member, idx) => (
            <div key={idx} className="member-brief">
              <div className="member-name">
                {member.type === 'user' ? '👤' : '🎭'} {member.name}
              </div>
              <div className="member-intro">{member.brief || '暂无简介'}</div>
            </div>
          ))
        ) : null}
      </div>
      {/* 反馈按钮（非管理员） */}
      {user && user.is_admin !== 1 && (
        <div style={{ padding: '16px', borderTop: '1px solid var(--border)' }}>
          <button className="feedback-btn-sidebar" onClick={onShowFeedback}>
            💬 我要反馈
          </button>
        </div>
      )}
    </aside>
  )
}

