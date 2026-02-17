import React from 'react';
import clsx from 'clsx';
import { 
  Battery, 
  Wifi, 
  WifiOff, 
  Activity, 
  MapPin,
  Gauge,
  AlertTriangle,
  CheckCircle,
  XCircle
} from 'lucide-react';
import { RobotState } from '@/types';

interface RobotCardProps {
  robot: RobotState;
  selected?: boolean;
  onClick?: () => void;
}

export const RobotCard: React.FC<RobotCardProps> = ({ robot, selected, onClick }) => {
  const getStatusColor = () => {
    switch (robot.status) {
      case 'connected': return 'text-green-500 bg-green-100';
      case 'disconnected': return 'text-red-500 bg-red-100';
      case 'error': return 'text-orange-500 bg-orange-100';
      default: return 'text-gray-500 bg-gray-100';
    }
  };

  const getStatusIcon = () => {
    switch (robot.status) {
      case 'connected': return <CheckCircle className="w-4 h-4" />;
      case 'disconnected': return <XCircle className="w-4 h-4" />;
      case 'error': return <AlertTriangle className="w-4 h-4" />;
      default: return <Activity className="w-4 h-4" />;
    }
  };

  const getBatteryColor = () => {
    if (robot.battery.level > 50) return 'text-green-500';
    if (robot.battery.level > 25) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div
      className={clsx(
        'p-4 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:shadow-md',
        selected 
          ? 'border-blue-500 bg-blue-50' 
          : 'border-gray-200 bg-white hover:border-gray-300'
      )}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div className={clsx('p-1 rounded-full', getStatusColor())}>
            {getStatusIcon()}
          </div>
          <h3 className="font-semibold text-gray-900">{robot.name}</h3>
        </div>
        
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          {robot.status === 'connected' ? (
            <Wifi className="w-4 h-4 text-green-500" />
          ) : (
            <WifiOff className="w-4 h-4 text-red-500" />
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="flex items-center space-x-1">
          <Battery className={clsx('w-4 h-4', getBatteryColor())} />
          <span className={clsx('text-sm font-medium', getBatteryColor())}>
            {robot.battery.level}%
          </span>
          {robot.battery.charging && (
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          )}
        </div>
        
        <div className="flex items-center space-x-1">
          <MapPin className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-600">
            ({robot.position.x.toFixed(1)}, {robot.position.y.toFixed(1)})
          </span>
        </div>
      </div>

      {robot.mission && (
        <div className="bg-blue-50 p-2 rounded">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-blue-700">
              {robot.mission.name}
            </span>
            <span className="text-xs text-blue-600">
              {robot.mission.progress}%
            </span>
          </div>
          <div className="w-full bg-blue-200 rounded-full h-1.5">
            <div
              className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${robot.mission.progress}%` }}
            />
          </div>
        </div>
      )}

      <div className="mt-2 text-xs text-gray-500">
        Last update: {new Date(robot.lastUpdate).toLocaleTimeString()}
      </div>
    </div>
  );
};

interface RobotListProps {
  robots: RobotState[];
  selectedRobotId?: string | null;
  onSelectRobot?: (robotId: string) => void;
}

export const RobotList: React.FC<RobotListProps> = ({ 
  robots, 
  selectedRobotId, 
  onSelectRobot 
}) => {
  if (robots.length === 0) {
    return (
      <div className=\"text-center py-8 text-gray-500\">
        <Activity className=\"w-12 h-12 mx-auto mb-4 opacity-50\" />
        <p>No robots connected</p>
        <p className=\"text-sm\">Waiting for robot connections...</p>
      </div>
    );
  }

  return (
    <div className=\"grid gap-4 md:grid-cols-2 lg:grid-cols-3\">
      {robots.map((robot) => (
        <RobotCard
          key={robot.id}
          robot={robot}
          selected={selectedRobotId === robot.id}
          onClick={() => onSelectRobot?.(robot.id)}
        />
      ))}
    </div>
  );
};