import { useState, useRef, useEffect, useCallback } from 'react'

const SimpleWebcamDetection = ({ onDetection }) => {
  const [isStreaming, setIsStreaming] = useState(false)
  const [isDetecting, setIsDetecting] = useState(false)
  const [error, setError] = useState('')
  const [detections, setDetections] = useState([])
  const [metrics, setMetrics] = useState({ c_motion: 0, sigma_theta: 0, sigma_rho: 0, pose_score: 0 })
  
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)
  const detectionIntervalRef = useRef(null)

  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { 
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        }
      })
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        streamRef.current = stream
        
        // Wait for video to be ready
        videoRef.current.onloadedmetadata = () => {
          videoRef.current.play()
          setIsStreaming(true)
          setError('')
        }
      }
    } catch (err) {
      setError('Failed to access webcam. Please ensure camera permissions are granted.')
      console.error('Webcam error:', err)
    }
  }

  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    
    if (detectionIntervalRef.current) {
      clearInterval(detectionIntervalRef.current)
      detectionIntervalRef.current = null
    }
    
    setIsStreaming(false)
    setIsDetecting(false)
    setDetections([])
    setMetrics({ c_motion: 0, sigma_theta: 0, sigma_rho: 0, pose_score: 0 })
  }

  const captureFrame = useCallback(() => {
    if (!videoRef.current || !canvasRef.current || !isStreaming) return null

    const video = videoRef.current
    const canvas = canvasRef.current
    const context = canvas.getContext('2d')

    // Set canvas size to match video
    canvas.width = video.videoWidth || 640
    canvas.height = video.videoHeight || 480
    
    // Draw current video frame to canvas
    context.drawImage(video, 0, 0, canvas.width, canvas.height)

    return canvas.toDataURL('image/jpeg', 0.8)
  }, [isStreaming])

  const drawDetections = useCallback((detectionData) => {
    if (!canvasRef.current || !videoRef.current) return

    const video = videoRef.current
    const canvas = canvasRef.current
    const context = canvas.getContext('2d')

    // Ensure canvas size matches video
    canvas.width = video.videoWidth || 640
    canvas.height = video.videoHeight || 480

    // Clear and draw video frame
    context.clearRect(0, 0, canvas.width, canvas.height)
    context.drawImage(video, 0, 0, canvas.width, canvas.height)

    // Draw detection boxes
    if (detectionData.detections && detectionData.detections.length > 0) {
      detectionData.detections.forEach(detection => {
        const [x1, y1, x2, y2] = detection.box
        const color = detection.label === 'fall' ? '#ef4444' : 
                     detection.label === 'person' ? '#22c55e' : '#f59e0b'
        
        // Draw bounding box
        context.strokeStyle = color
        context.lineWidth = 3
        context.strokeRect(x1, y1, x2 - x1, y2 - y1)
        
        // Draw label background
        const label = `${detection.label} ${(detection.confidence * 100).toFixed(0)}%`
        context.font = '16px Arial'
        const textWidth = context.measureText(label).width
        
        context.fillStyle = color
        context.fillRect(x1, y1 - 25, textWidth + 8, 25)
        
        // Draw label text
        context.fillStyle = 'white'
        context.fillText(label, x1 + 4, y1 - 8)
      })
    }

    // Draw status banner
    const fallDetected = detectionData.fall_detected || false
    const bannerHeight = 40
    context.fillStyle = fallDetected ? 'rgba(239, 68, 68, 0.8)' : 'rgba(34, 197, 94, 0.8)'
    context.fillRect(0, 0, canvas.width, bannerHeight)
    
    context.fillStyle = 'white'
    context.font = 'bold 18px Arial'
    const statusText = fallDetected ? '🚨 FALL DETECTED!' : `📊 SCANNING...`
    const textWidth = context.measureText(statusText).width
    context.fillText(statusText, (canvas.width - textWidth) / 2, 25)

    // Draw metrics
    context.fillStyle = 'rgba(0, 0, 0, 0.7)'
    context.fillRect(0, canvas.height - 60, canvas.width, 60)
    
    context.fillStyle = 'white'
    context.font = '14px Arial'
    const metricsText = `C_motion: ${(detectionData.metrics?.c_motion || 0).toFixed(1)}% | σ_θ: ${(detectionData.metrics?.sigma_theta || 0).toFixed(1)}° | σ_ρ: ${(detectionData.metrics?.sigma_rho || 0).toFixed(3)} | Pose: ${(detectionData.metrics?.pose_score || 0).toFixed(2)}`
    context.fillText(metricsText, 10, canvas.height - 35)
    
    const immobilityText = `Immobility: ${(detectionData.metrics?.immobility_secs || 0).toFixed(1)}s`
    context.fillText(immobilityText, 10, canvas.height - 15)

    // Draw ellipse if available
    if (detectionData.ellipse) {
      const e = detectionData.ellipse
      context.strokeStyle = fallDetected ? '#ef4444' : '#22c55e'
      context.lineWidth = 2
      context.beginPath()
      context.ellipse(e.cx, e.cy, e.a, e.b, e.theta * Math.PI / 180, 0, 2 * Math.PI)
      context.stroke()
    }

    // Draw pose skeleton if available
    if (detectionData.pose_landmarks) {
      context.strokeStyle = '#3b82f6'
      context.lineWidth = 2
      detectionData.pose_landmarks.forEach(landmark => {
        context.fillStyle = '#3b82f6'
        context.beginPath()
        context.arc(landmark.x, landmark.y, 3, 0, 2 * Math.PI)
        context.fill()
      })
    }

  }, [])

  const runDetection = useCallback(async () => {
    if (!isStreaming || !isDetecting) return

    try {
      const imageData = captureFrame()
      if (!imageData) {
        console.log('Failed to capture frame')
        return
      }

      // Convert data URL to blob
      const response = await fetch(imageData)
      const blob = await response.blob()
      
      // Create FormData for API
      const formData = new FormData()
      formData.append('file', blob, 'webcam_frame.jpg')

      // Send to detection API
      const detectionResponse = await fetch('http://localhost:8000/detect', {
        method: 'POST',
        body: formData
      })

      if (!detectionResponse.ok) {
        throw new Error(`Detection failed: ${detectionResponse.status}`)
      }

      const result = await detectionResponse.json()
      
      setDetections(result.detections || [])
      setMetrics({
        c_motion: result.metrics?.c_motion || 0,
        sigma_theta: result.metrics?.sigma_theta || 0,
        sigma_rho: result.metrics?.sigma_rho || 0,
        pose_score: result.metrics?.pose_score || 0
      })

      // Draw detections on canvas
      drawDetections(result)

      // Notify parent component
      if (onDetection) {
        onDetection(result)
      }

      // Trigger fall alert if detected
      if (result.fall_detected) {
        console.log('🚨 FALL DETECTED!', result)
      }

    } catch (err) {
      console.error('Detection error:', err)
    }

  }, [isStreaming, isDetecting, captureFrame, drawDetections, onDetection])

  const startDetection = async () => {
    if (!isStreaming) return
    
    // Test backend connection
    try {
      console.log('Testing backend connection...')
      const healthResponse = await fetch('http://localhost:8000/')
      if (!healthResponse.ok) {
        throw new Error('Backend not responding')
      }
      console.log('Backend connection OK')
    } catch (err) {
      console.error('Backend connection failed:', err)
      setError('Cannot connect to backend. Please ensure it is running on http://localhost:8000')
      return
    }
    
    console.log('Starting fall detection...')
    setIsDetecting(true)
    setTimeout(runDetection, 500)
  }

  const stopDetection = () => {
    console.log('Stopping detection...')
    setIsDetecting(false)
    if (detectionIntervalRef.current) {
      clearInterval(detectionIntervalRef.current)
      detectionIntervalRef.current = null
    }
  }

  useEffect(() => {
    return () => {
      stopWebcam()
    }
  }, [])

  useEffect(() => {
    if (isDetecting) {
      // Clear any existing interval
      if (detectionIntervalRef.current) {
        clearInterval(detectionIntervalRef.current)
      }
      // Set up new interval for continuous detection
      console.log('Setting up interval for continuous fall detection')
      detectionIntervalRef.current = setInterval(runDetection, 500) // 2 FPS for fall detection
      // Run first detection immediately
      setTimeout(runDetection, 100)
    } else {
      // Clear interval when detection stops
      if (detectionIntervalRef.current) {
        console.log('Clearing fall detection interval')
        clearInterval(detectionIntervalRef.current)
        detectionIntervalRef.current = null
      }
    }
  }, [isDetecting, runDetection])

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      background: '#000',
      borderRadius: 8,
      overflow: 'hidden'
    }}>
      {/* Controls */}
      <div style={{
        padding: '10px',
        background: '#111418',
        borderBottom: '1px solid #252d3a',
        display: 'flex',
        gap: '8px',
        justifyContent: 'center',
        flexWrap: 'wrap'
      }}>
        {!isStreaming ? (
          <button onClick={startWebcam} style={{
            background: '#22c55e',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            padding: '8px 16px',
            fontSize: '12px',
            cursor: 'pointer',
            fontFamily: 'Space Mono, monospace'
          }}>
            📷 Start Webcam
          </button>
        ) : (
          <>
            <button onClick={stopWebcam} style={{
              background: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '8px 16px',
              fontSize: '12px',
              cursor: 'pointer',
              fontFamily: 'Space Mono, monospace'
            }}>
              ⏹️ Stop Webcam
            </button>
            
            {!isDetecting ? (
              <button onClick={startDetection} style={{
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                padding: '8px 16px',
                fontSize: '12px',
                cursor: 'pointer',
                fontFamily: 'Space Mono, monospace'
              }}>
                🔍 Start Detection
              </button>
            ) : (
              <button onClick={stopDetection} style={{
                background: '#f59e0b',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                padding: '8px 16px',
                fontSize: '12px',
                cursor: 'pointer',
                fontFamily: 'Space Mono, monospace'
              }}>
                ⏸️ Stop Detection
              </button>
            )}
          </>
        )}
      </div>

      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid #ef4444',
          color: '#ef4444',
          padding: '8px 12px',
          margin: '8px',
          borderRadius: '4px',
          fontFamily: 'Space Mono, monospace',
          fontSize: '12px',
          textAlign: 'center'
        }}>
          ❌ {error}
        </div>
      )}

      {/* Video/Canvas Container */}
      <div style={{
        position: 'relative',
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#000'
      }}>
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{ 
            display: isStreaming && !isDetecting ? 'block' : 'none',
            width: '100%',
            height: '100%',
            objectFit: 'cover'
          }}
        />
        <canvas
          ref={canvasRef}
          style={{ 
            display: isDetecting ? 'block' : 'none',
            width: '100%',
            height: '100%',
            objectFit: 'cover'
          }}
        />
        
        {!isStreaming && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            color: '#64748b',
            fontFamily: 'Space Mono, monospace',
            fontSize: '14px'
          }}>
            <p>📷 Click "Start Webcam" to begin fall detection</p>
          </div>
        )}
      </div>

      {/* Metrics Display */}
      {isStreaming && (
        <div style={{
          padding: '8px',
          background: '#111418',
          borderTop: '1px solid #252d3a',
          display: 'flex',
          justifyContent: 'space-around',
          fontFamily: 'Space Mono, monospace',
          fontSize: '11px'
        }}>
          <div style={{ color: '#94a3b8' }}>
            C_motion: <span style={{ color: '#22c55e' }}>{metrics.c_motion.toFixed(1)}%</span>
          </div>
          <div style={{ color: '#94a3b8' }}>
            σ_θ: <span style={{ color: '#3b82f6' }}>{metrics.sigma_theta.toFixed(1)}°</span>
          </div>
          <div style={{ color: '#94a3b8' }}>
            σ_ρ: <span style={{ color: '#f59e0b' }}>{metrics.sigma_rho.toFixed(3)}</span>
          </div>
          <div style={{ color: '#94a3b8' }}>
            Pose: <span style={{ color: '#ef4444' }}>{metrics.pose_score.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default SimpleWebcamDetection
