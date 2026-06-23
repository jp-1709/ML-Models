import React, { useEffect, useRef } from 'react';

export default function WebcamSender() {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const wsRef = useRef(null);

    useEffect(() => {
        // 1. Get webcam stream with better error handling
        const getWebcam = async () => {
            // Check if mediaDevices is supported
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                console.error('❌ getUserMedia is not supported in this browser');
                return;
            }
            
            try {
                // Request camera permissions first
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        width: { ideal: 640, max: 640 },
                        height: { ideal: 480, max: 480 },
                        facingMode: 'user'
                    } 
                });
                
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                    console.log('✅ Webcam access granted');
                }
            } catch (err) {
                console.error('❌ Error accessing webcam:', err);
                
                // Handle specific permission errors
                if (err.name === 'NotAllowedError') {
                    console.error('🚫 Camera permission denied by user');
                    alert('Camera access was denied. Please allow camera permissions in your browser settings to use fall detection.');
                } else if (err.name === 'NotFoundError') {
                    console.error('📷 No camera device found');
                    alert('No camera device found. Please connect a camera to use fall detection.');
                } else if (err.name === 'NotReadableError') {
                    console.error('🔒 Camera is already in use by another application');
                    alert('Camera is already in use. Please close other applications using the camera.');
                } else {
                    console.error('❌ Unknown webcam error:', err);
                    
                    // Try a more permissive fallback
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({ 
                            video: true 
                        });
                        if (videoRef.current) {
                            videoRef.current.srcObject = stream;
                            console.log('✅ Webcam access granted (fallback)');
                        }
                    } catch (fallbackErr) {
                        console.error('❌ Webcam access completely failed:', fallbackErr);
                        alert('Unable to access camera. Fall detection will not work without camera access.');
                    }
                }
            }
        };
        
        getWebcam();

        // 2. Setup WebSocket with better error handling
        const connect = () => {
            try {
                const ws = new WebSocket(`ws://localhost:8000/ws/video_stream`);
                
                ws.onopen = () => {
                    console.log('✅ Webcam WebSocket connected');
                    wsRef.current = ws;
                };
                
                ws.onclose = (event) => {
                    console.log('🔌 Webcam WebSocket disconnected, reconnecting...', event.code, event.reason);
                    wsRef.current = null;
                    setTimeout(connect, 3000);
                };
                
                ws.onerror = (error) => {
                    console.error('❌ Webcam WebSocket error:', error);
                };
                
                ws.onmessage = (event) => {
                    // Handle any messages from server if needed
                    console.log('📨 WebSocket message:', event.data);
                };
                
            } catch (error) {
                console.error('❌ Failed to create WebSocket:', error);
                setTimeout(connect, 3000);
            }
        };
        connect();

        // 3. Setup capture loop with better error handling
        let requestAnimFrameId;
        const sendFrame = () => {
            try {
                if (wsRef.current?.readyState === WebSocket.OPEN && videoRef.current && canvasRef.current) {
                    const video = videoRef.current;
                    const canvas = canvasRef.current;
                    const ctx = canvas.getContext('2d');
                    
                    if (video.readyState === video.HAVE_ENOUGH_DATA) {
                        canvas.width = 640;
                        canvas.height = 480;
                        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                        
                        canvas.toBlob(blob => {
                            if (blob && wsRef.current?.readyState === WebSocket.OPEN) {
                                wsRef.current.send(blob);
                            }
                        }, 'image/jpeg', 0.7); // Better quality for detection
                    }
                }
            } catch (error) {
                console.error('❌ Error sending frame:', error);
            }

            // Limit to ~15 FPS for better performance
            setTimeout(() => {
                requestAnimFrameId = requestAnimationFrame(sendFrame);
            }, 66); // ~15 FPS
        };
        
        // Start capture loop after a short delay
        setTimeout(() => {
            requestAnimFrameId = requestAnimationFrame(sendFrame);
        }, 1000);

        return () => {
            cancelAnimationFrame(requestAnimFrameId);
            wsRef.current?.close();
            if (videoRef.current?.srcObject) {
                const tracks = videoRef.current.srcObject.getTracks();
                tracks.forEach(t => t.stop());
            }
        };
    }, []);

    return (
        <div style={{ display: 'none' }}>
            <video ref={videoRef} autoPlay playsInline muted />
            <canvas ref={canvasRef} width={640} height={480} />
        </div>
    );
}
