import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useAppStore, useEmergencyMode } from '@/store';

interface EmergencyButtonProps {
  onEmergencyStop: () => void;
}

export const EmergencyButton: React.FC<EmergencyButtonProps> = ({ onEmergencyStop }) => {
  const { toggleEmergencyMode } = useAppStore();
  const emergencyMode = useEmergencyMode();

  const handleEmergencyClick = () => {
    toggleEmergencyMode();
    onEmergencyStop();
  };

  return (
    <button
      onClick={handleEmergencyClick}
      className={`
        relative px-6 py-3 rounded-lg font-bold text-white transition-all duration-200
        ${emergencyMode 
          ? 'bg-red-600 hover:bg-red-700 shadow-lg animate-pulse' 
          : 'bg-red-500 hover:bg-red-600'
        }
        focus:outline-none focus:ring-4 focus:ring-red-300
        transform hover:scale-105 active:scale-95
      `}
    >
      <div className="flex items-center space-x-2">
        <AlertTriangle className={`w-5 h-5 ${emergencyMode ? 'animate-pulse' : ''}`} />
        <span>EMERGENCY STOP</span>
      </div>
      
      {emergencyMode && (
        <div className="absolute inset-0 rounded-lg bg-red-600 opacity-20 animate-ping" />
      )}
    </button>
  );
};