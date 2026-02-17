import React from 'react';
import { Activity, Cpu, HardDrive, Wifi, Clock, Users, Target } from 'lucide-react';
import { useAppStore } from '@/store';

export const SystemStatus: React.FC = () => {
  const { systemStatus, robots, connectionStatus, lastHeartbeat } = useAppStore();

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'text-green-500 bg-green-100';
      case 'connecting': return 'text-yellow-500 bg-yellow-100';
      case 'disconnected': return 'text-red-500 bg-red-100';
      default: return 'text-gray-500 bg-gray-100';
    }
  };

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const getLastHeartbeatText = () => {
    if (!lastHeartbeat) return 'Never';
    const timeDiff = Date.now() - lastHeartbeat.getTime();
    if (timeDiff < 1000) return 'Just now';
    if (timeDiff < 60000) return `${Math.floor(timeDiff / 1000)}s ago`;
    return `${Math.floor(timeDiff / 60000)}m ago`;
  };

  return (
    <div className="flex items-center space-x-4 text-sm">
      {/* Connection Status */}
      <div className="flex items-center space-x-2">
        <div className={`p-1 rounded-full ${getConnectionStatusColor()}`}>
          <Wifi className="w-4 h-4" />
        </div>
        <span className="text-gray-700 capitalize">{connectionStatus}</span>
      </div>

      {/* System Metrics */}
      {systemStatus && (
        <>
          <div className="flex items-center space-x-1 text-gray-600">
            <Cpu className="w-4 h-4" />
            <span>{systemStatus.cpuUsage.toFixed(1)}%</span>
          </div>

          <div className="flex items-center space-x-1 text-gray-600">
            <HardDrive className="w-4 h-4" />
            <span>{systemStatus.memoryUsage.toFixed(1)}%</span>
          </div>

          <div className="flex items-center space-x-1 text-gray-600">
            <Clock className="w-4 h-4" />
            <span>{formatUptime(systemStatus.uptime)}</span>
          </div>
        </>
      )}

      {/* Robot Count */}
      <div className="flex items-center space-x-1 text-gray-600">
        <Users className="w-4 h-4" />
        <span>{Object.keys(robots).length} robots</span>
      </div>

      {/* Last Heartbeat */}
      <div className="text-xs text-gray-500">
        Last update: {getLastHeartbeatText()}
      </div>
    </div>
  );
};