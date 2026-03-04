import React, { useState, useEffect, useRef } from 'react'
import api from '../lib/api'
import './ChatWindow.css'

function ChatWindow({ recipient, onBack }) {
  const [messages, setMessages] = useState([])
  const [newMessage, setNewMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [uploading, setUploading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    loadMessages()
    // Poll for new messages every 2 seconds
    const interval = setInterval(loadMessages, 2000)
    return () => clearInterval(interval)
  }, [recipient])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadMessages = async () => {
    try {
      const response = await api.get('/messages')
      // Filter messages for current recipient
      const filteredMessages = response.data.messages.filter(
        (msg) => msg.sender === recipient || msg.recipient === recipient
      )
      setMessages(filteredMessages)
    } catch (error) {
      console.error('Failed to load messages:', error)
    }
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!newMessage.trim() || sending) return

    try {
      setSending(true)
      await api.post('/messages/send', {
        recipient_username: recipient,
        message: newMessage,
      })
      setNewMessage('')
      // Reload messages after sending
      setTimeout(loadMessages, 500)
    } catch (error) {
      alert('Failed to send message: ' + error.message)
    } finally {
      setSending(false)
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    try {
      setUploading(true)
      const formData = new FormData()
      formData.append('file', file)
      formData.append('recipient_username', recipient)

      await api.post('/files/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      alert('File uploaded successfully!')
      setTimeout(loadMessages, 500)
    } catch (error) {
      alert('Failed to upload file: ' + error.message)
    } finally {
      setUploading(false)
      e.target.value = '' // Reset file input
    }
  }

  return (
    <div className="chat-window">
      <div className="chat-header">
        <button onClick={onBack} className="back-button">
          ← Back
        </button>
        <div className="chat-recipient">
          <div className="recipient-avatar">
            {recipient.charAt(0).toUpperCase()}
          </div>
          <div className="recipient-name">{recipient}</div>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-messages">
            <p>No messages yet</p>
            <p className="hint">Start a conversation!</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`message ${msg.sender === recipient ? 'received' : 'sent'}`}
            >
              {msg.message.startsWith('FILE:') ? (
                <FileMessage message={msg.message} />
              ) : (
                <div className="message-text">{msg.message}</div>
              )}
              <div className="message-time">
                {new Date().toLocaleTimeString()}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <form onSubmit={handleSendMessage} className="chat-input-form">
          <label className="file-upload-label">
            <input
              type="file"
              onChange={handleFileUpload}
              disabled={uploading}
              style={{ display: 'none' }}
            />
            {uploading ? '📤 Uploading...' : '📎'}
          </label>
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Type a message..."
            className="chat-input"
            disabled={sending}
          />
          <button
            type="submit"
            disabled={!newMessage.trim() || sending}
            className="send-button"
          >
            {sending ? 'Sending...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  )
}

function FileMessage({ message }) {
  const parts = message.split(':')
  if (parts.length >= 3 && parts[0] === 'FILE') {
    const filename = parts[1]
    const fileData = parts.slice(2).join(':')
    
    const handleDownload = () => {
      try {
        const binaryString = atob(fileData)
        const bytes = new Uint8Array(binaryString.length)
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i)
        }
        const blob = new Blob([bytes])
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      } catch (error) {
        alert('Failed to download file')
      }
    }

    return (
      <div className="file-message">
        <div className="file-icon">📎</div>
        <div className="file-info">
          <div className="file-name">{filename}</div>
          <button onClick={handleDownload} className="download-button">
            Download
          </button>
        </div>
      </div>
    )
  }

  return <div className="message-text">{message}</div>
}

export default ChatWindow
