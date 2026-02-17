import React, { useState, useRef } from 'react';
import { Camera, VideoOff, Maximize2, Minimize2, RotateCw } from 'lucide-react';
import { useCameraFeeds } from '@/store';

interface CameraViewProps {
  robotId?: string;
}

export const CameraView: React.FC<CameraViewProps> = ({ robotId }) => {
  const cameraFeeds = useCameraFeeds();
  const [selectedFeedId, setSelectedFeedId] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Filter camera feeds by robot if robotId is provided
  const filteredFeeds = robotId 
    ? cameraFeeds.filter(feed => feed.id.includes(robotId))
    : cameraFeeds;

  const selectedFeed = selectedFeedId 
    ? cameraFeeds.find(feed => feed.id === selectedFeedId)
    : filteredFeeds[0];

  const toggleFullscreen = () => {
    if (videoRef.current) {
      if (!isFullscreen) {
        videoRef.current.requestFullscreen?.();
      } else {
        document.exitFullscreen?.();
      }
      setIsFullscreen(!isFullscreen);
    }
  };

  const refreshFeed = () => {
    if (videoRef.current && selectedFeed) {
      videoRef.current.load();
    }
  };

  if (filteredFeeds.length === 0) {
    return (
      <div className="p-6 text-center text-gray-500">
        <VideoOff className="w-16 h-16 mx-auto mb-4 opacity-50" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No Camera Feeds
        </h3>
        <p>No camera feeds available for this robot.</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Camera Feed Selection */}
      {filteredFeeds.length > 1 && (
        <div className="p-4 border-b">
          <select
            value={selectedFeedId || ''}
            onChange={(e) => setSelectedFeedId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
          >
            {filteredFeeds.map((feed) => (
              <option key={feed.id} value={feed.id}>
                {feed.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Main Camera Feed */}
      <div className="flex-1 relative bg-black">
        {selectedFeed ? (
          <>
            <video
              ref={videoRef}
              src={selectedFeed.url}
              autoPlay
              muted
              className="w-full h-full object-contain"
              onError={(e) => {
                console.error('Camera feed error:', e);
              }}
            />

            {/* Camera Controls Overlay */}
            <div className="absolute top-2 right-2 flex space-x-2">
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
                <div className={`w-2 h-2 rounded-full ${
                  selectedFeed.status === 'active' ? 'bg-green-500' : 'bg-red-500'
                }`} />
                <span>{selectedFeed.name}</span>
                <span>•</span>
                <span>{selectedFeed.resolution.width}x{selectedFeed.resolution.height}</span>
                <span>•</span>
                <span>{selectedFeed.fps} FPS</span>
                {selectedFeed.latency && (
                  <>
                    <span>•</span>
                    <span>{selectedFeed.latency}ms</span>
                  </>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-white">
            <div className="text-center">
              <Camera className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>Camera feed unavailable</p>
            </div>
          </div>
        )}
      </div>

      {/* Camera Feed Thumbnails */}
      {filteredFeeds.length > 1 && (
        <div className="p-4 border-t bg-gray-50">
          <div className="flex space-x-2 overflow-x-auto">
            {filteredFeeds.map((feed) => (
              <div
                key={feed.id}
                onClick={() => setSelectedFeedId(feed.id)}
                className={`
                  flex-shrink-0 w-24 h-16 bg-black rounded cursor-pointer border-2 transition-all
                  ${selectedFeedId === feed.id || (!selectedFeedId && feed === filteredFeeds[0])
                    ? 'border-blue-500'
                    : 'border-gray-300 hover:border-gray-400'
                  }
                `}
              >
                <div className="w-full h-full flex items-center justify-center text-white text-xs">
                  <div className="text-center">
                    <Camera className="w-6 h-6 mx-auto mb-1 opacity-75" />
                    <div className="truncate px-1">{feed.name}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};