import { useState, useRef, useEffect } from 'react'

const WebcamDetection = ({ onDetection }) => {
  const [isStreaming, setIsStreaming] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)
  const intervalRef = useRef(null)

  const startWebcam = async () => {
    try {
      setError('')
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 } 
      })
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        streamRef.current = stream
        setIsStreaming(true)
      }
    } catch (err) {
      setError('Failed to access webcam: ' + err.message)
      console.error('Webcam error:', err)
    }
  }

  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setIsStreaming(false)
  }

  const captureAndDetect = async () => {
    if (!videoRef.current || !canvasRef.current) return

    const video = videoRef.current
    const canvas = canvasRef.current
    const context = canvas.getContext('2d')

    // Set canvas size to match video
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    // Draw current video frame to canvas
    context.drawImage(video, 0, 0, canvas.width, canvas.height)

    // Convert canvas to blob
    canvas.toBlob(async (blob) => {
      if (!blob) return

      setLoading(true)
      try {
        const formData = new FormData()
        formData.append('file', blob, 'webcam-capture.jpg')

        const response = await fetch('http://localhost:8000/detect', {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const result = await response.json()
        onDetection(result)

        // Draw detection boxes on canvas if we have detections
        if (result.detections && result.detections.length > 0) {
          drawDetections(context, result.detections, canvas.width, canvas.height)
        }
      } catch (err) {
        setError('Detection failed: ' + err.message)
        console.error('Detection error:', err)
      } finally {
        setLoading(false)
      }
    }, 'image/jpeg')
  }

  const drawDetections = (context, detections, imageWidth, imageHeight) => {
    detections.forEach(detection => {
      const [x1, y1, x2, y2] = detection.box
      
      // Set color based on detection type
      let color
      switch (detection.label) {
        case 'fall':
          color = '#FF0000' // Red
          break
        case 'slip':
          color = '#FFA500' // Orange
          break
        case 'person':
          color = '#00FF00' // Green
          break
        default:
          color = '#FFFFFF' // White
      }

      // Draw bounding box
      context.strokeStyle = color
      context.lineWidth = 2
      context.strokeRect(x1, y1, x2 - x1, y2 - y1)

      // Draw label background
      const label = `${detection.label}: ${(detection.confidence * 100).toFixed(1)}%`
      context.font = '16px Arial'
      const textWidth = context.measureText(label).width
      
      context.fillStyle = color
      context.fillRect(x1, y1 - 25, textWidth + 10, 25)

      // Draw label text
      context.fillStyle = '#FFFFFF'
      context.fillText(label, x1 + 5, y1 - 8)
    })
  }

  const startContinuousDetection = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    
    // Capture and detect every 2 seconds
    intervalRef.current = setInterval(captureAndDetect, 2000)
  }

  const stopContinuousDetection = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  useEffect(() => {
    return () => {
      stopWebcam()
    }
  }, [])

  return (
    <div className="webcam-detection">
      <div className="webcam-controls">
        {!isStreaming ? (
          <button className="webcam-btn start" onClick={startWebcam}>
            📹 Start Webcam
          </button>
        ) : (
          <>
            <button className="webcam-btn stop" onClick={stopWebcam}>
              ⏹️ Stop Webcam
            </button>
            <button 
              className="webcam-btn detect" 
              onClick={captureAndDetect}
              disabled={loading}
            >
              {loading ? '🔄 Detecting...' : '🔍 Detect Now'}
            </button>
            <button 
              className="webcam-btn continuous" 
              onClick={startContinuousDetection}
            >
              ▶️ Continuous Detection
            </button>
            <button 
              className="webcam-btn stop-continuous" 
              onClick={stopContinuousDetection}
            >
              ⏸️ Stop Continuous
            </button>
          </>
        )}
      </div>

      {error && (
        <div className="error-message">
          ❌ {error}
        </div>
      )}

      <div className="video-container">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{ display: isStreaming ? 'block' : 'none' }}
        />
        <canvas
          ref={canvasRef}
          style={{ display: isStreaming ? 'block' : 'none' }}
        />
        
        {!isStreaming && (
          <div className="webcam-placeholder">
            <p>📹 Click "Start Webcam" to begin fall detection</p>
          </div>
        )}
      </div>

      {loading && (
        <div className="loading-indicator">
          <p>🔄 Analyzing for falls...</p>
        </div>
      )}
    </div>
  )
}

export default WebcamDetection
