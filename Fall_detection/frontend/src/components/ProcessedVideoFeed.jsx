import React, { useState, useRef, useEffect } from 'react';

export default function ProcessedVideoFeed({ alertActive }) {
  const [status, setStatus] = useState('connecting'); // connecting | live | error
  const [frameUrl, setFrameUrl] = useState('');
  const canvasRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket('ws://localhost:8000/ws/processed_frames');
        
        ws.onopen = () => {
          console.log('✅ Processed video feed connected');
          setStatus('live');
          wsRef.current = ws;
        };
        
        ws.onclose = (event) => {
          console.log('🔌 Processed video feed disconnected, reconnecting...', event.code, event.reason);
          setStatus('connecting');
          wsRef.current = null;
          setTimeout(connect, 3000);
        };
        
        ws.onerror = (error) => {
          console.error('❌ Processed video feed error:', error);
          setStatus('error');
        };
        
        ws.onmessage = (event) => {
          // Receive processed frame as JPEG
          const blob = new Blob([event.data], { type: 'image/jpeg' });
          const url = URL.createObjectURL(blob);
          
          // Clean up previous URL
          if (frameUrl) {
            URL.revokeObjectURL(frameUrl);
          }
          
          setFrameUrl(url);
          
          // Update canvas if available
          if (canvasRef.current) {
            const img = new Image();
            img.onload = () => {
              const ctx = canvasRef.current.getContext('2d');
              canvasRef.current.width = 640;
              canvasRef.current.height = 480;
              ctx.drawImage(img, 0, 0, 640, 480);
            };
            img.src = url;
          }
        };
        
      } catch (error) {
        console.error('❌ Failed to create processed video feed WebSocket:', error);
        setStatus('error');
        setTimeout(connect, 3000);
      }
    };
    
    connect();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (frameUrl) {
        URL.revokeObjectURL(frameUrl);
      }
    };
  }, []);

  return (
    <div style={{
      position: 'relative',
      width: '100%',
      background: '#000',
      borderRadius: 8,
      overflow: 'hidden',
      aspectRatio: '4 / 3',
      border: '1px solid #252d3a',
    }}>
      {/* Corner decorations – surveillance aesthetic */}
      <div style={{
        position: 'absolute', width: 18, height: 18,
        borderTop: '2px solid #475569', borderLeft: '2px solid',
        zIndex: 3, top: 0, left: 0,
      }} />
      <div style={{
        position: 'absolute', width: 18, height: 18,
        borderTop: '2px solid #475569', borderRight: '2px solid',
        zIndex: 3, top: 0, right: 0,
      }} />
      <div style={{
        position: 'absolute', width: 18, height: 18,
        borderBottom: '2px solid #475569', borderLeft: '2px solid',
        zIndex: 3, bottom: 0, left: 0,
      }} />
      <div style={{
        position: 'absolute', width: 18, height: 18,
        borderBottom: '2px solid #475569', borderRight: '2px solid',
        zIndex: 3, bottom: 0, right: 0,
      }} />

      {/* LIVE badge */}
      <div style={{
        position: 'absolute', top: 10, left: 10, zIndex: 4,
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '3px 10px',
        border: '1px solid',
        borderRadius: 3,
        fontSize: 10,
        fontFamily: 'Space Mono, monospace',
        fontWeight: 700,
        letterSpacing: '0.1em',
        backdropFilter: 'blur(4px)',
        background: status === 'live' ? '#22c55e20' : '#f59e0b20',
        borderColor: status === 'live' ? '#22c55e' : '#f59e0b',
        color: status === 'live' ? '#22c55e' : '#f59e0b',
      }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: status === 'live' ? '#22c55e' : '#f59e0b',
          animation: status === 'live' ? 'blink 1.6s ease infinite' : 'none',
        }} />
        {status === 'live' ? 'LIVE' : status === 'connecting' ? 'CONNECTING' : 'ERROR'}
      </div>

      {/* Camera label */}
      <div style={{
        position: 'absolute', top: 10, right: 10, zIndex: 4,
        fontFamily: 'Space Mono, monospace',
        fontSize: 9,
        color: '#475569',
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
      }}>
        PROCESSED FEED · AI DETECTION
      </div>

      {/* Processed video frame */}
      {frameUrl ? (
        <img
          src={frameUrl}
          alt="Processed camera feed with AI detection"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            display: 'block',
            transition: 'border 200ms ease',
            filter: alertActive ? 'brightness(1.08)' : 'none',
            border: alertActive ? '2px solid #ef4444' : '2px solid transparent',
          }}
        />
      ) : (
        <canvas
          ref={canvasRef}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            display: 'block',
          }}
        />
      )}

      {/* Alert overlay banner */}
      {alertActive && (
        <div style={{
          position: 'absolute',
          bottom: 0, left: 0, right: 0,
          zIndex: 5,
          background: 'rgba(239,68,68,0.9)',
          color: '#fff',
          fontFamily: 'Space Mono, monospace',
          fontWeight: 700,
          fontSize: 14,
          letterSpacing: '0.2em',
          textAlign: 'center',
          padding: '8px 0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 10,
          animation: 'blink 0.9s ease infinite',
        }}>
          <span style={{ fontSize: 16 }}>⚠</span>
          FALL DETECTED
          <span style={{ fontSize: 16 }}>⚠</span>
        </div>
      )}

      {/* Connecting / Error overlay */}
      {status !== 'live' && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 6,
          background: 'rgba(10,12,15,0.85)',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          textAlign: 'center',
        }}>
          {status === 'connecting' ? (
            <>
              <div style={{
                width: 32, height: 32,
                border: '3px solid #252d3a',
                borderTopColor: '#f59e0b',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
              }} />
              <p style={{ 
                marginTop: 14, 
                color: '#f59e0b', 
                fontFamily: 'Space Mono, monospace', 
                fontSize: 13 
              }}>
                Establishing processed video feed…
              </p>
            </>
          ) : (
            <>
              <div style={{ fontSize: 36 }}>🤖</div>
              <p style={{ 
                marginTop: 10, 
                color: '#ef4444', 
                fontFamily: 'Space Mono, monospace', 
                fontSize: 13 
              }}>
                AI processing unavailable.<br />Check backend connection.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
