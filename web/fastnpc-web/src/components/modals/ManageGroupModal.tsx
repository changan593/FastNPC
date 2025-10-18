import type { CharacterItem, MemberBrief } from '../../types'
import { useAuth } from '../../contexts/AuthContext'
import { useGroup } from '../../contexts/GroupContext'

interface ManageGroupModalProps {
  show: boolean
  onClose: () => void
  activeGroupId: number | null
  characters: CharacterItem[]
  groupMemberBriefs: MemberBrief[]
  loadGroupMemberBriefs: () => Promise<void>
  onDeleteGroup: () => void
}

export function ManageGroupModal({ show, onClose, activeGroupId, characters, groupMemberBriefs, loadGroupMemberBriefs, onDeleteGroup }: ManageGroupModalProps) {
  const { api } = useAuth()
  const { newMemberName, setNewMemberName } = useGroup()

  if (!show) return null

  return (
    <div className="modal" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h3>管理群成员</h3>
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ marginBottom: 8 }}>当前成员</h4>
          <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 8, padding: 8 }}>
            {groupMemberBriefs.map((member, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '6px 8px',
                  borderBottom: idx < groupMemberBriefs.length - 1 ? '1px solid #f3f4f6' : 'none',
                }}
              >
                <span>
                  {member.type === 'user' ? '👤' : '🎭'} {member.name}
                </span>
                {member.type === 'character' && (
                  <button
                    style={{
                      fontSize: 12,
                      padding: '2px 8px',
                      background: '#ef4444',
                      color: 'white',
                      border: 'none',
                      borderRadius: 4,
                      cursor: 'pointer',
                    }}
                    onClick={async () => {
                      if (!confirm(`确定移除 ${member.name}？`)) return
                      try {
                        await api.delete(`/api/groups/${activeGroupId}/members/${encodeURIComponent(member.original_name)}`)
                        await loadGroupMemberBriefs()
                      } catch (e: any) {
                        alert(e?.response?.data?.error || '移除失败')
                      }
                    }}
                  >
                    移除
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ marginBottom: 8 }}>添加新成员</h4>
          <div style={{ display: 'flex', gap: 8 }}>
            <select value={newMemberName} onChange={e => setNewMemberName(e.target.value)} style={{ flex: 1, padding: '8px', border: '1px solid #e5e7eb', borderRadius: 8 }}>
              <option value="">选择角色</option>
              {characters
                .filter(c => !groupMemberBriefs.some(m => m.original_name === c.role))
                .map(c => (
                  <option key={c.role} value={c.role}>
                    {c.role}
                  </option>
                ))}
            </select>
            <button
              onClick={async () => {
                if (!newMemberName) {
                  alert('请选择角色')
                  return
                }
                try {
                  await api.post(`/api/groups/${activeGroupId}/members`, {
                    member_name: newMemberName,
                  })
                  await loadGroupMemberBriefs()
                  setNewMemberName('')
                } catch (e: any) {
                  alert(e?.response?.data?.error || '添加失败')
                }
              }}
              style={{ padding: '8px 16px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: 8, cursor: 'pointer' }}
            >
              添加
            </button>
          </div>
        </div>
        <div className="actions" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button onClick={onDeleteGroup} style={{ background: '#ef4444', color: 'white' }}>
            删除群聊
          </button>
          <button onClick={onClose}>关闭</button>
        </div>
      </div>
    </div>
  )
}

