import React, { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'
import api from '../lib/api'
import ChatWindow from './ChatWindow'
import ConnectionsPanel from './ConnectionsPanel'
import UsersPanel from './UsersPanel'
import './Dashboard.css'

function Dashboard({ user }) {
  const [activeTab, setActiveTab] = useState('chat')
  const [currentChat, setCurrentChat] = useState(null)
  const [connections, setConnections] = useState([])
  const [pendingRequests, setPendingRequests] = useState([])
  const [username, setUsername] = useState('')

  useEffect(() => {
    loadUserData()
    loadConnections()
    loadPendingRequests()
    
    // Poll for new messages and requests
    const interval = setInterval(() => {
      loadConnections()
      loadPendingRequests()
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const loadUserData = async () => {
    try {
      const response = await api.get('/users/me')
      setUsername(response.data.username)
    } catch (error) {
      console.error('Failed to load user data:', error)
    }
  }

  const loadConnections = async () => {
    try {
      const response = await api.get('/connections')
      setConnections(response.data.connections)
    } catch (error) {
      console.error('Failed to load connections:', error)
    }
  }

  const loadPendingRequests = async () => {
    try {
      const response = await api.get('/connections/pending')
      setPendingRequests(response.data.pending_requests || [])
    } catch (error) {
      console.error('Failed to load pending requests:', error)
    }
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
    localStorage.removeItem('access_token')
    window.location.href = '/login'
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="header-content">
          <h1>🔐 Secure Messaging</h1>
          <div className="user-info">
            <span>{username || user.email}</span>
            <button onClick={handleLogout} className="logout-button">
              Logout
            </button>
          </div>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="sidebar">
          <div className="tabs">
            <button
              className={`tab ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              💬 Chat
            </button>
            <button
              className={`tab ${activeTab === 'connections' ? 'active' : ''}`}
              onClick={() => setActiveTab('connections')}
            >
              👥 Connections
              {pendingRequests.length > 0 && (
                <span className="badge">{pendingRequests.length}</span>
              )}
            </button>
            <button
              className={`tab ${activeTab === 'users' ? 'active' : ''}`}
              onClick={() => setActiveTab('users')}
            >
              🔍 Find Users
            </button>
          </div>

          {activeTab === 'chat' && (
            <ConnectionsPanel
              connections={connections}
              currentChat={currentChat}
              setCurrentChat={setCurrentChat}
            />
          )}

          {activeTab === 'connections' && (
            <div className="panel-content">
              <ConnectionsPanel
                connections={connections}
                currentChat={currentChat}
                setCurrentChat={setCurrentChat}
              />
              {pendingRequests.length > 0 && (
                <div className="pending-section">
                  <h3>Pending Requests</h3>
                  {pendingRequests.map((req) => (
                    <PendingRequestItem
                      key={req.id}
                      request={req}
                      onAccept={() => {
                        loadConnections()
                        loadPendingRequests()
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'users' && (
            <UsersPanel
              onConnectionRequest={() => {
                loadPendingRequests()
              }}
            />
          )}
        </div>

        <div className="main-content">
          {currentChat ? (
            <ChatWindow
              recipient={currentChat}
              onBack={() => setCurrentChat(null)}
            />
          ) : (
            <div className="empty-state">
              <h2>Select a conversation</h2>
              <p>Choose a connection from the sidebar to start messaging</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function PendingRequestItem({ request, onAccept }) {
  const handleAccept = async () => {
    try {
      await api.post('/connections/accept', {
        requester_username: request.requester_username,
      })
      onAccept()
    } catch (error) {
      alert('Failed to accept connection: ' + error.message)
    }
  }

  return (
    <div className="pending-request-item">
      <span>{request.requester_username}</span>
      <button onClick={handleAccept} className="accept-button">
        Accept
      </button>
    </div>
  )
}

export default Dashboard
