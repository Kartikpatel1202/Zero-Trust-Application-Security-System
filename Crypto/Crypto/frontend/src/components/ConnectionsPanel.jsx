import React from 'react'
import './ConnectionsPanel.css'

function ConnectionsPanel({ connections, currentChat, setCurrentChat }) {
  if (connections.length === 0) {
    return (
      <div className="connections-empty">
        <p>No connections yet</p>
        <p className="hint">Go to "Find Users" to connect</p>
      </div>
    )
  }

  return (
    <div className="connections-panel">
      <div className="connections-header">
        <h3>Connections ({connections.length})</h3>
      </div>
      <div className="connections-list">
        {connections.map((username) => (
          <div
            key={username}
            className={`connection-item ${currentChat === username ? 'active' : ''}`}
            onClick={() => setCurrentChat(username)}
          >
            <div className="connection-avatar">
              {username.charAt(0).toUpperCase()}
            </div>
            <div className="connection-info">
              <div className="connection-name">{username}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ConnectionsPanel
