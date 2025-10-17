import { useAuth } from '../contexts/AuthContext'

export function AuthView({ onLoginSuccess }: { onLoginSuccess: () => Promise<void> }) {
  const {
    authMode,
    setAuthMode,
    authForm,
    setAuthForm,
    agreedToTerms,
    setAgreedToTerms,
    showTerms,
    setShowTerms,
    doLogin,
    doRegister,
  } = useAuth()

  async function handleLogin() {
    await doLogin()
    await onLoginSuccess()
  }

  async function handleRegister() {
    await doRegister()
    await onLoginSuccess()
  }

  return (
    <>
      <div className="auth-wrap">
        <div className="auth-background-text">FastNPC</div>
        <div className="auth-card">
          <h2>{authMode === 'login' ? '登录' : '注册'}</h2>
          <label>
            用户名
            <input
              value={authForm.username}
              onChange={e => setAuthForm({ ...authForm, username: e.target.value })}
              placeholder="用户名"
            />
          </label>
          <label>
            密码
            <input
              type="password"
              value={authForm.password}
              onChange={e => setAuthForm({ ...authForm, password: e.target.value })}
              placeholder="密码"
            />
          </label>
          {authMode === 'register' && (
            <div className="terms-agreement">
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={agreedToTerms}
                  onChange={e => setAgreedToTerms(e.target.checked)}
                  style={{ cursor: 'pointer' }}
                />
                <span style={{ fontSize: '14px', color: '#6b7280' }}>
                  我已阅读并同意
                  <a
                    href="#"
                    onClick={e => {
                      e.preventDefault()
                      setShowTerms(true)
                    }}
                    style={{ color: '#667eea', textDecoration: 'none', marginLeft: '4px', marginRight: '4px' }}
                  >
                    《用户服务协议》
                  </a>
                </span>
              </label>
            </div>
          )}
          <div className="actions">
            {authMode === 'login' ? (
              <>
                <button onClick={handleLogin} className="primary">
                  登录
                </button>
                <button onClick={() => setAuthMode('register')}>没有账号？去注册</button>
              </>
            ) : (
              <>
                <button onClick={handleRegister} className="primary">
                  注册并登录
                </button>
                <button onClick={() => setAuthMode('login')}>已有账号？去登录</button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 用户协议模态框 */}
      {showTerms && (
        <div className="modal" onClick={() => setShowTerms(false)}>
          <div
            className="dialog"
            style={{ maxWidth: '800px', maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="feedback-header">
              <h3>📜 用户服务协议</h3>
              <button className="close-btn" onClick={() => setShowTerms(false)}>
                ×
              </button>
            </div>
            <div style={{ flex: 1, overflow: 'auto', padding: '20px', fontSize: '14px', lineHeight: '1.8' }}>
              <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#374151' }}>
                <h2 style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '16px' }}>FastNPC 用户服务协议</h2>
                <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '24px' }}>最后更新时间：2025年1月17日</p>

                <p style={{ marginBottom: '16px' }}>欢迎使用 FastNPC！本服务协议（以下简称"本协议"）是您与 FastNPC 项目（以下简称"我们"或"本服务"）之间的法律协议。</p>

                <p style={{ fontWeight: 'bold', marginBottom: '16px', color: '#dc2626' }}>
                  ⚠️ 重要提示：使用本服务即表示您同意本协议的所有条款。如果您不同意本协议的任何部分，请勿使用本服务。
                </p>

                <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px' }}>1. 服务使用</h3>
                <p style={{ marginBottom: '8px' }}>• 您必须年满 13 周岁才能使用本服务</p>
                <p style={{ marginBottom: '8px' }}>• 您同意提供真实、准确的注册信息</p>
                <p style={{ marginBottom: '16px' }}>• 您有责任维护账户密码的安全性</p>

                <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px' }}>2. 禁止行为</h3>
                <p style={{ marginBottom: '8px' }}>在使用本服务时，禁止以下行为：</p>
                <p style={{ marginBottom: '8px' }}>• 发布侵犯他人知识产权的内容</p>
                <p style={{ marginBottom: '8px' }}>• 发布威胁、骚扰、诽谤他人的内容</p>
                <p style={{ marginBottom: '8px' }}>• 发布暴力、色情、淫秽内容</p>
                <p style={{ marginBottom: '8px' }}>• 试图破解、反向工程本服务</p>
                <p style={{ marginBottom: '16px' }}>• 从事任何非法活动</p>

                <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px' }}>3. AI 内容免责</h3>
                <p style={{ marginBottom: '8px' }}>• AI 生成的内容可能不准确，仅供娱乐参考</p>
                <p style={{ marginBottom: '8px' }}>• 不要依赖 AI 内容做重要决策</p>
                <p style={{ marginBottom: '16px' }}>• 您对使用 AI 生成内容的后果负全部责任</p>

                <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px' }}>4. 知识产权与内容所有权</h3>
                <p style={{ fontWeight: 'bold', marginBottom: '12px', color: '#059669' }}>✅ 重要：您创建的所有角色和内容的版权归您所有</p>
                <p style={{ marginBottom: '8px' }}>• 您创建的 AI 角色、对话记录等，所有权完全归您</p>
                <p style={{ marginBottom: '8px' }}>• 我们有权删除违规内容，无需事先通知</p>
                <p style={{ marginBottom: '8px', color: '#dc2626' }}>⚠️ 我们不对数据丢失、误删承担责任</p>
                <p style={{ marginBottom: '16px' }}>• 建议您定期备份重要数据</p>

                <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px' }}>5. 隐私保护</h3>
                <p style={{ marginBottom: '8px' }}>• 我们收集必要的注册和使用数据</p>
                <p style={{ marginBottom: '8px' }}>• 我们不会出售您的个人信息</p>
                <p style={{ marginBottom: '16px' }}>• 我们采取合理措施保护您的数据安全</p>

                <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px' }}>6. 免责声明</h3>
                <p style={{ marginBottom: '8px' }}>• 本服务按"现状"提供，不保证无错误</p>
                <p style={{ marginBottom: '8px', fontWeight: 'bold', color: '#dc2626' }}>• 我们不对数据丢失、损坏、误删承担任何责任</p>
                <p style={{ marginBottom: '8px' }}>• 我们不对服务中断或 AI 内容准确性负责</p>
                <p style={{ marginBottom: '16px', background: '#fef3c7', padding: '8px', borderRadius: '4px', color: '#92400e' }}>
                  💡 本服务为免费服务，不承担任何赔偿责任
                </p>

                <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px' }}>7. 服务变更与终止</h3>
                <p style={{ marginBottom: '8px' }}>• 我们可能随时修改、暂停或终止服务</p>
                <p style={{ marginBottom: '8px' }}>• 我们保留暂停或终止违规账户的权利</p>
                <p style={{ marginBottom: '16px' }}>• 账户终止后，您的数据可能被删除</p>

                <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px' }}>8. 联系我们</h3>
                <p style={{ marginBottom: '8px' }}>如对本协议有疑问，请通过以下方式联系：</p>
                <p style={{ marginBottom: '8px' }}>• 使用应用内的"我要反馈"功能</p>
                <p style={{ marginBottom: '16px' }}>• GitHub: https://github.com/changan593/FastNPC</p>

                <p style={{ fontWeight: 'bold', marginTop: '32px', padding: '16px', background: '#fef3c7', borderRadius: '8px', color: '#92400e' }}>
                  ⚠️ 再次提醒：使用本服务即表示您已阅读、理解并同意本协议的所有条款。
                </p>

                <p style={{ marginTop: '24px', fontSize: '12px', color: '#6b7280', textAlign: 'center' }}>FastNPC 是一个开源项目，遵循 MIT 许可证</p>
              </div>
            </div>
            <div className="feedback-actions">
              <button
                className="btn-primary"
                onClick={() => {
                  setShowTerms(false)
                  setAgreedToTerms(true)
                }}
              >
                我已阅读并同意
              </button>
              <button className="btn-secondary" onClick={() => setShowTerms(false)}>
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

