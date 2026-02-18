import React, { useState, useRef, useCallback } from 'react';
import { Camera, VideoOff, Maximize2, Minimize2, RotateCw, CameraIcon } from 'lucide-react';
import { useCameraFeeds } from '@/store';

/**
 * Robot Controller API base URL.
 * The Pi Camera streams MJPEG directly from FastAPI — no WebSocket relay needed.
 *
 * How it works:
 *   FastAPI endpoint:  GET /api/robot/camera/stream
 *     → returns multipart/x-mixed-replace MJPEG stream
 *   Browser <img> tag natively renders the stream with ~100 ms latency.
 *
 * For a single snapshot: GET /api/robot/camera/snapshot  → image/jpeg
 */
const ROBOT_API = process.env.NEXT_PUBLIC_ROBOT_API || 'http://localhost:8000';

interface CameraViewProps {
  robotId?: string;
}

export const CameraView: React.FC<CameraViewProps> = ({ robotId }) => {
  const cameraFeeds = useCameraFeeds();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [streamError, setStreamError] = useState(false);
  const [streamKey, setStreamKey] = useState(0); // bump to force reload
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  // MJPEG stream URL served directly by the Robot Controller API (FastAPI)
  const mjpegUrl = `${ROBOT_API}/api/robot/camera/stream`;
  const snapshotUrl = `${ROBOT_API}/api/robot/camera/snapshot`;

  const toggleFullscreen = useCallback(() => {
    if (containerRef.current) {
      if (!isFullscreen) {
        containerRef.current.requestFullscreen?.();
      } else {
        document.exitFullscreen?.();
      }
      setIsFullscreen(!isFullscreen);
    }
  }, [isFullscreen]);

  const refreshFeed = useCallback(() => {
    // Bump key to unmount/remount the <img>, restarting the MJPEG stream
    setStreamError(false);
    setStreamKey((k) => k + 1);
  }, []);

  const captureSnapshot = useCallback(async () => {
    try {
      const res = await fetch(snapshotUrl);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      // Open snapshot in a new tab (or download)
      const a = document.createElement('a');
      a.href = url;
      a.download = `snapshot_${Date.now()}.jpg`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Snapshot capture failed:', err);
    }
  }, [snapshotUrl]);

  return (
    <div className="h-full flex flex-col">
      {/* Main Camera Feed — MJPEG via <img> tag */}
      <div ref={containerRef} className="flex-1 relative bg-black">
        {!streamError ? (
          <>
            {/*
              MJPEG streams work natively in <img> tags.
              The browser keeps the HTTP connection open and renders
              each JPEG frame as it arrives — no JS decoding needed.
            */}
            <img
              ref={imgRef}
              key={streamKey}
              src={`${mjpegUrl}?t=${streamKey}`}
              alt="Robot Camera Feed"
              className="w-full h-full object-contain"
              onError={() => {
                console.error('MJPEG stream connection failed');
                setStreamError(true);
              }}
              onLoad={() => setStreamError(false)}
            />

            {/* Camera Controls Overlay */}
            <div className="absolute top-2 right-2 flex space-x-2">
              <button
                onClick={captureSnapshot}
                className="p-2 bg-black bg-opacity-50 text-white rounded-lg hover:bg-opacity-75 transition-opacity"
                title="Capture snapshot"
              >
                <CameraIcon className="w-4 h-4" />
              </button>
              <button
                onClick={refreshFeed}
                className="p-2 bg-black bg-opacity-50 text-white rounded-lg hover:bg-opacity-75 transition-opacity"
                title="Refresh feed"
              >
                <RotateCw className="w-4 h-4" />
              </button>
              <button
                onClick={toggleFullscreen}
                className="p-2 bg-black bg-opacity-50 text-white rounded-lg hover:bg-opacity-75 transition-opacity"
                title="Toggle fullscreen"
              >
                {isFullscreen ? (
                  <Minimize2 className="w-4 h-4" />
                ) : (
                  <Maximize2 className="w-4 h-4" />
                )}
              </button>
            </div>

            {/* Feed Info Overlay */}
            <div className="absolute bottom-2 left-2 bg-black bg-opacity-50 text-white text-xs rounded px-2 py-1">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span>Pi Camera V1.3</span>
                <span>&bull;</span>
                <span>640&times;480</span>
                <span>&bull;</span>
                <span>MJPEG Live</span>
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-white">
            <div className="text-center">
              <VideoOff className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium mb-2">Camera Feed Unavailable</h3>
              <p className="text-sm text-gray-400 mb-4">
                Cannot connect to {mjpegUrl}
              </p>
              <button
                onClick={refreshFeed}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <RotateCw className="w-4 h-4 inline mr-2" />
                Retry Connection
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};