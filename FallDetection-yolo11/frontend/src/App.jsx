import { useState, useRef } from 'react'
import WebcamDetection from './components/WebcamDetection'
import './App.css'

function App() {
  const [selectedImage, setSelectedImage] = useState(null)
  const [detections, setDetections] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('upload') // 'upload' or 'webcam'
  const fileInputRef = useRef(null)

  const handleImageSelect = (event) => {
    const file = event.target.files[0]
    if (file) {
      setSelectedImage(file)
      setDetections(null)
      setError('')
    }
  }

  const detectFalls = async () => {
    if (!selectedImage) return

    setLoading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', selectedImage)

      const response = await fetch('http://localhost:8000/detect', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      setDetections(result)
    } catch (err) {
      setError(`Detection failed: ${err.message}`)
      console.error('Detection error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleEmergencyDetection = async () => {
    if (!selectedImage) return

    setLoading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', selectedImage)

      const response = await fetch('http://localhost:8000/emergency-alert', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      setDetections({
        ...result,
        emergency: result.emergency,
        isEmergency: true
      })
    } catch (err) {
      setError(`Emergency detection failed: ${err.message}`)
      console.error('Emergency detection error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleWebcamDetection = (result) => {
    setDetections(result)
  }

  const getImageUrl = (file) => {
    return file ? URL.createObjectURL(file) : null
  }

  return (
    <div className="fall-detection-app">
      <header className="app-header">
        <h1>🚨 Fall Detection System</h1>
        <p>Real-time fall and slip detection using YOLO11</p>
      </header>

      <main className="app-main">
        <div className="tab-navigation">
          <button 
            className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            📤 Upload Image
          </button>
          <button 
            className={`tab-btn ${activeTab === 'webcam' ? 'active' : ''}`}
            onClick={() => setActiveTab('webcam')}
          >
            📹 Live Detection
          </button>
        </div>

        {activeTab === 'upload' && (
          <div className="upload-section">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageSelect}
              style={{ display: 'none' }}
            />
            <button 
              className="upload-btn"
              onClick={() => fileInputRef.current?.click()}
            >
              📷 Choose Image
            </button>
            
            {selectedImage && (
              <div className="selected-image-info">
                <p>Selected: {selectedImage.name}</p>
                <div className="detection-buttons">
                  <button 
                    className="detect-btn"
                    onClick={detectFalls}
                    disabled={loading}
                  >
                    {loading ? '🔄 Detecting...' : '🔍 Detect Falls'}
                  </button>
                  <button 
                    className="emergency-btn"
                    onClick={handleEmergencyDetection}
                    disabled={loading}
                  >
                    {loading ? '🔄 Scanning...' : '🚨 Emergency Scan'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'webcam' && (
          <WebcamDetection onDetection={handleWebcamDetection} />
        )}

        {error && (
          <div className="error-message">
            ❌ {error}
          </div>
        )}

        {detections && activeTab === 'upload' && (
          <div className="results-section">
            <div className="image-container">
              <div className="original-image">
                <h3>Original Image</h3>
                {selectedImage ? (
                  <img src={getImageUrl(selectedImage)} alt="Original" />
                ) : (
                  <div className="placeholder">
                    <p>No image selected</p>
                  </div>
                )}
              </div>

              <div className="detected-image">
                <h3>Detection Results</h3>
                <div className="detection-summary">
                  <p className={`message ${detections.emergency ? 'emergency' : detections.fall_count === 0 && detections.slip_count === 0 ? 'success' : 'warning'}`}>
                    {detections.message}
                  </p>
                  <div className="stats">
                    <span className="stat fall">🚨 {detections.fall_count || 0}</span>
                    <span className="stat slip">⚠️ {detections.slip_count || 0}</span>
                    <span className="stat person">👤 {detections.person_count || 0}</span>
                  </div>
                </div>
              </div>
            </div>

            {detections.detections && detections.detections.length > 0 && (
              <div className="detection-details">
                <h3>Detection Details</h3>
                <div className="detections-list">
                  {detections.detections.map((detection, index) => (
                    <div 
                      key={index} 
                      className={`detection-item ${detection.label}`}
                    >
                      <span className="label">
                        {detection.label === 'fall' ? '🚨' : 
                         detection.label === 'slip' ? '⚠️' : 
                         detection.label === 'person' ? '👤' : '❓'} {detection.label}
                      </span>
                      <span className="confidence">
                        {(detection.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {detections.isEmergency && (
              <div className="emergency-alert">
                <h3>🚨 Emergency Alert</h3>
                <p>Timestamp: {detections.timestamp}</p>
                <p>Status: {detections.emergency ? 'EMERGENCY DETECTED' : 'No Emergency'}</p>
                {detections.emergency && (
                  <div className="emergency-actions">
                    <button className="alert-btn">📞 Call Emergency Services</button>
                    <button className="alert-btn">📍 Send Location</button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
