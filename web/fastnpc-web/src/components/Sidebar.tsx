import { useState } from 'react'
import type { CharacterItem, GroupItem } from '../types'
import { useCharacter } from '../contexts/CharacterContext'

interface SidebarProps {
  characters: CharacterItem[]
  groups: GroupItem[]
  activeType: 'character' | 'group'
  setActiveType: (type: 'character' | 'group') => void
  activeRole: string
  setActiveRole: (role: string) => void
  activeGroupId: number | null
  setActiveGroupId: (id: number | null) => void
  onCreateCharacter: () => void
  onCreateGroup: () => void
}

export function Sidebar({
  characters,
  groups,
  activeType,
  setActiveType,
  activeRole,
  setActiveRole,
  activeGroupId,
  setActiveGroupId,
  onCreateCharacter,
  onCreateGroup,
}: SidebarProps) {
  const [q, setQ] = useState('')
  const [sort, setSort] = useState<'updated' | 'alpha'>('updated')

  const { menuVisible, setMenuVisible, menuPos, setMenuPos, menuRole, setMenuRole, renaming, setRenaming, newName, setNewName, renameRole, deleteRole, copyRole } =
    useCharacter()

  const allItems = [
    ...characters.map(c => ({
      type: 'character' as const,
      data: c,
      updated_at: c.updated_at,
      name: c.role,
    })),
    ...groups.map(g => ({
      type: 'group' as const,
      data: g,
      updated_at: g.updated_at,
      name: g.name,
    })),
  ]

  const filteredItems = allItems
    .filter(item => !q || item.name.includes(q))
    .sort((a, b) => (sort === 'alpha' ? a.name.localeCompare(b.name) : b.updated_at - a.updated_at))

  return (
    <aside className="sidebar">
      <div className="sidebar-head">
        <div className="app-logo">FastNPC</div>
        <h2>角色/群聊</h2>
      </div>
      <div className="search">
        <input placeholder="搜索" value={q} onChange={e => setQ(e.target.value)} />
        <select value={sort} onChange={e => setSort(e.target.value as any)}>
          <option value="updated">最近更新</option>
          <option value="alpha">按名称</option>
        </select>
      </div>
      <ul className="role-list">
        {filteredItems.map(item => (
          <li
            key={`${item.type}-${item.type === 'character' ? item.data.role : item.data.id}`}
            className={
              (item.type === 'character' && activeType === 'character' && item.data.role === activeRole) ||
              (item.type === 'group' && activeType === 'group' && item.data.id === activeGroupId)
                ? 'active'
                : ''
            }
            onContextMenu={e => {
              if (item.type === 'character') {
                e.preventDefault()
                setMenuRole(item.data.role)
                setMenuPos({ x: e.clientX, y: e.clientY })
                setMenuVisible(true)
              }
            }}
          >
            <div
              className="row"
              onClick={() => {
                if (item.type === 'character') {
                  setActiveType('character')
                  setActiveRole(item.data.role)
                  setActiveGroupId(null)
                } else {
                  setActiveType('group')
                  setActiveGroupId(item.data.id)
                  setActiveRole('')
                }
              }}
            >
              {item.type === 'character' && item.data.avatar_url ? (
                <div 
                  className="avatar" 
                  style={{ 
                    width: 40, 
                    height: 40, 
                    borderRadius: 8, 
                    overflow: 'hidden',
                    marginRight: 12,
                    flexShrink: 0
                  }}
                >
                  <img 
                    src={item.data.avatar_url} 
                    alt={item.name}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                </div>
              ) : null}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="name">
                  {item.type === 'character' ? (
                    item.data.avatar_url ? (
                      item.name
                    ) : (
                      <><span>👤 </span>{item.name}</>
                    )
                  ) : (
                    <><span>💬 </span>{item.name}</>
                  )}
                </div>
                <div className="time">{new Date(item.updated_at * 1000).toLocaleDateString()}</div>
              </div>
            </div>
            {item.type === 'character' && item.data.preview ? (
              <div
                className="muted"
                title={item.data.preview}
                style={{
                  margin: '4px 0 0',
                  fontSize: 12,
                  lineHeight: 1.4,
                  display: '-webkit-box',
                  WebkitLineClamp: 2 as any,
                  WebkitBoxOrient: 'vertical' as any,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {item.data.preview}
              </div>
            ) : null}
            {item.type === 'character' && (
              <div className="ops">
                {renaming === item.data.role ? (
                  <>
                    <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="新名称" />
                    <button onClick={() => renameRole(item.data.role)} className="primary">
                      确定
                    </button>
                    <button
                      onClick={() => {
                        setRenaming('')
                        setNewName('')
                      }}
                    >
                      取消
                    </button>
                  </>
                ) : null}
              </div>
            )}
          </li>
        ))}
      </ul>
      <div className="fab-container">
        <div className="fab-hint">新建</div>
        <div className="fab-buttons">
          <button className="fab" aria-label="创建角色" title="创建角色" onClick={onCreateCharacter}>
            📝 角色
          </button>
          <button className="fab" aria-label="创建群聊" title="创建群聊" onClick={onCreateGroup}>
            💬 群聊
          </button>
        </div>
      </div>

      {/* 右键菜单 */}
      {menuVisible && menuRole && (
        <div
          style={{
            position: 'fixed',
            left: menuPos.x,
            top: menuPos.y,
            zIndex: 1000,
            background: '#fff',
            border: '1px solid #e5e7eb',
            boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
            borderRadius: 8,
            overflow: 'hidden',
          }}
        >
          <button
            style={{ display: 'block', width: 160, textAlign: 'left', padding: '8px 12px' }}
            onClick={() => {
              setRenaming(menuRole)
              setNewName(menuRole)
              setMenuVisible(false)
            }}
          >
            重命名
          </button>
          <button
            style={{ display: 'block', width: 160, textAlign: 'left', padding: '8px 12px' }}
            onClick={() => {
              copyRole(menuRole)
              setMenuVisible(false)
            }}
          >
            复制
          </button>
          <button
            style={{ display: 'block', width: 160, textAlign: 'left', padding: '8px 12px', color: '#b91c1c' }}
            onClick={() => {
              deleteRole(menuRole)
              setMenuVisible(false)
            }}
          >
            删除
          </button>
        </div>
      )}
    </aside>
  )
}

