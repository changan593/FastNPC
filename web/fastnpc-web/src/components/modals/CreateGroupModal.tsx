import type { CharacterItem } from '../../types'
import { useAuth } from '../../contexts/AuthContext'

interface CreateGroupModalProps {
  show: boolean
  onClose: () => void
  characters: CharacterItem[]
  selectedMembers: string[]
  setSelectedMembers: (members: string[]) => void
  newGroupName: string
  setNewGroupName: (name: string) => void
  onSuccess: (groupId: number) => void
}

export function CreateGroupModal({
  show,
  onClose,
  characters,
  selectedMembers,
  setSelectedMembers,
  newGroupName,
  setNewGroupName,
  onSuccess,
}: CreateGroupModalProps) {
  const { api } = useAuth()

  async function handleCreate() {
    if (!newGroupName.trim()) {
      alert('请输入群聊名称')
      return
    }
    if (selectedMembers.length === 0) {
      alert('请至少选择一个角色')
      return
    }
    try {
      const { data } = await api.post('/api/groups', {
        name: newGroupName.trim(),
        members: selectedMembers,
      })
      onSuccess(data.group_id)
      onClose()
      setNewGroupName('')
      setSelectedMembers([])
    } catch (e: any) {
      alert(e?.response?.data?.error || '创建失败')
    }
  }

  if (!show) return null

  return (
    <div className="modal" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h3>创建群聊</h3>
        <label>
          群聊名称
          <input value={newGroupName} onChange={e => setNewGroupName(e.target.value)} placeholder="输入群聊名称" />
        </label>
        <label>
          选择成员（角色）
          <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #ccc', padding: 8 }}>
            {characters.map(c => (
              <label key={c.role} style={{ display: 'block' }}>
                <input
                  type="checkbox"
                  checked={selectedMembers.includes(c.role)}
                  onChange={e => {
                    if (e.target.checked) {
                      setSelectedMembers([...selectedMembers, c.role])
                    } else {
                      setSelectedMembers(selectedMembers.filter(m => m !== c.role))
                    }
                  }}
                />
                {c.role}
              </label>
            ))}
          </div>
        </label>
        <div className="actions">
          <button onClick={handleCreate}>创建</button>
          <button onClick={onClose}>取消</button>
        </div>
      </div>
    </div>
  )
}

