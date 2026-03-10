import React, { useState, useEffect } from 'react'
import api from '../lib/api'
import './UsersPanel.css'

function UsersPanel({ onConnectionRequest }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [requesting, setRequesting] = useState(null)

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    try {
      setLoading(true)
      const response = await api.get('/users')
      setUsers(response.data.users)
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRequestConnection = async (username) => {
    try {
      setRequesting(username)
      await api.post('/connections/request', { target_username: username })
      alert(`Connection request sent to ${username}`)
      onConnectionRequest()
    } catch (error) {
      alert('Failed to send connection request: ' + error.message)
    } finally {
      setRequesting(null)
    }
  }

  if (loading) {
    return (
      <div className="users-panel">
        <div className="loading">Loading users...</div>
      </div>
    )
  }

  return (
    <div className="users-panel">
      <div className="users-header">
        <h3>All Users</h3>
        <button onClick={loadUsers} className="refresh-button">
          🔄 Refresh
        </button>
      </div>
      <div className="users-list">
        {users.length === 0 ? (
          <div className="empty-users">No other users found</div>
        ) : (
          users.map((user) => (
            <div key={user.username} className="user-item">
              <div className="user-avatar">
                {user.username.charAt(0).toUpperCase()}
              </div>
              <div className="user-info">
                <div className="user-name">{user.username}</div>
                <div className="user-key">Key: {user.public_key_hex}</div>
              </div>
              <button
                onClick={() => handleRequestConnection(user.username)}
                disabled={requesting === user.username}
                className="connect-button"
              >
                {requesting === user.username ? 'Sending...' : 'Connect'}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default UsersPanel
