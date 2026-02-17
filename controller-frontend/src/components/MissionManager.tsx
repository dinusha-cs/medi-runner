import React, { useState } from 'react';
import { Play, Pause, Square, Clock, Target, CheckCircle, AlertTriangle } from 'lucide-react';
import { Mission } from '@/types';

interface MissionManagerProps {
  robotId: string;
  currentMission?: Mission | null;
  onCommand: (command: any) => void;
  disabled?: boolean;
}

const sampleMissions: Omit<Mission, 'id'>[] = [
  {
    name: "Medicine Delivery - Room 101",
    description: "Deliver medicine package to patient in Room 101",
    status: 'pending',
    progress: 0,
    steps: [
      { id: 'step1', name: 'Navigate to Pharmacy', type: 'move', description: 'Move to pharmacy station', parameters: { target: 'pharmacy' }, status: 'pending', duration: 30 },
      { id: 'step2', name: 'Pickup Medicine', type: 'pickup', description: 'Collect medicine package', parameters: { item: 'medicine_pack_101' }, status: 'pending', duration: 15 },
      { id: 'step3', name: 'Navigate to Room 101', type: 'move', description: 'Move to patient room', parameters: { target: 'room_101' }, status: 'pending', duration: 45 },
      { id: 'step4', name: 'Deliver Medicine', type: 'drop', description: 'Deliver package to patient', parameters: { location: 'bedside' }, status: 'pending', duration: 10 },
      { id: 'step5', name: 'Return to Base', type: 'move', description: 'Return to charging station', parameters: { target: 'base' }, status: 'pending', duration: 30 }
    ],
    currentStep: 0,
    estimatedDuration: 130
  },
  {
    name: "Medical Supply Transport",
    description: "Transport medical supplies from storage to surgery room",
    status: 'pending',
    progress: 0,
    steps: [
      { id: 'step1', name: 'Navigate to Storage', type: 'move', description: 'Move to medical storage', parameters: { target: 'storage' }, status: 'pending', duration: 20 },
      { id: 'step2', name: 'Load Supplies', type: 'pickup', description: 'Load medical supplies', parameters: { items: ['surgical_kit', 'sterile_equipment'] }, status: 'pending', duration: 25 },
      { id: 'step3', name: 'Navigate to Surgery', type: 'move', description: 'Move to surgery room', parameters: { target: 'surgery_room' }, status: 'pending', duration: 35 },
      { id: 'step4', name: 'Unload Supplies', type: 'drop', description: 'Unload at surgery prep area', parameters: { location: 'prep_area' }, status: 'pending', duration: 15 }
    ],
    currentStep: 0,
    estimatedDuration: 95
  },
  {
    name: "Emergency Response",
    description: "Emergency medicine delivery to ICU",
    status: 'pending',
    progress: 0,
    steps: [
      { id: 'step1', name: 'Priority Navigation', type: 'move', description: 'Fast route to emergency pharmacy', parameters: { target: 'emergency_pharmacy', priority: 'high' }, status: 'pending', duration: 15 },
      { id: 'step2', name: 'Emergency Pickup', type: 'pickup', description: 'Collect emergency medication', parameters: { item: 'emergency_meds', verification: 'required' }, status: 'pending', duration: 10 },
      { id: 'step3', name: 'Rush to ICU', type: 'move', description: 'Priority route to ICU', parameters: { target: 'icu', priority: 'emergency' }, status: 'pending', duration: 20 },
      { id: 'step4', name: 'Emergency Delivery', type: 'drop', description: 'Immediate handoff to medical staff', parameters: { location: 'icu_station', alert: 'staff' }, status: 'pending', duration: 5 }
    ],
    currentStep: 0,
    estimatedDuration: 50
  }
];

export const MissionManager: React.FC<MissionManagerProps> = ({ robotId, currentMission, onCommand, disabled }) => {
  const [selectedMissionIndex, setSelectedMissionIndex] = useState<number | null>(null);

  const startMission = (mission: Omit<Mission, 'id'>) => {
    const missionId = `mission_${Date.now()}`;
    onCommand({
      type: 'mission',
      parameters: {
        action: 'start',
        robotId,
        mission: {
          ...mission,
          id: missionId,
        }
      }
    });
  };

  const pauseMission = () => {
    if (currentMission) {
      onCommand({
        type: 'mission',
        parameters: {
          action: 'pause',
          robotId,
          missionId: currentMission.id,
        }
      });
    }
  };

  const stopMission = () => {
    if (currentMission) {
      onCommand({
        type: 'mission',
        parameters: {
          action: 'stop',
          robotId,
          missionId: currentMission.id,
        }
      });
    }
  };

  const getStepStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'active': return <Clock className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'failed': return <AlertTriangle className="w-4 h-4 text-red-500" />;
      default: return <div className="w-4 h-4 bg-gray-300 rounded-full" />;
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Current Mission Status */}
      {currentMission && (
        <div className="border rounded-lg p-4 bg-blue-50">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{currentMission.name}</h3>
              <p className="text-sm text-gray-600">{currentMission.description}</p>
            </div>
            <div className="flex space-x-2">
              {currentMission.status === 'active' ? (
                <>
                  <button
                    onClick={pauseMission}
                    disabled={disabled}
                    className="btn btn-secondary flex items-center space-x-1"
                  >
                    <Pause className="w-4 h-4" />
                    <span>Pause</span>
                  </button>
                  <button
                    onClick={stopMission}
                    disabled={disabled}
                    className="btn btn-danger flex items-center space-x-1"
                  >
                    <Square className="w-4 h-4" />
                    <span>Stop</span>
                  </button>
                </>
              ) : currentMission.status === 'paused' ? (
                <button
                  onClick={() => startMission(currentMission)}
                  disabled={disabled}
                  className="btn btn-primary flex items-center space-x-1"
                >
                  <Play className="w-4 h-4" />
                  <span>Resume</span>
                </button>
              ) : null}
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mb-4">
            <div className="flex justify-between text-sm mb-1">
              <span>Progress</span>
              <span>{currentMission.progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${currentMission.progress}%` }}
              />
            </div>
          </div>

          {/* Mission Steps */}
          <div className="space-y-2">
            <h4 className="font-medium text-gray-900">Steps:</h4>
            {currentMission.steps.map((step, index) => (
              <div
                key={step.id}
                className={`flex items-center space-x-3 p-2 rounded ${
                  index === currentMission.currentStep ? 'bg-blue-100' : 'bg-white'
                }`}
              >
                {getStepStatusIcon(step.status)}
                <div className="flex-1">
                  <div className="font-medium text-sm">{step.name}</div>
                  <div className="text-xs text-gray-500">{step.description}</div>
                </div>
                <div className="text-xs text-gray-400">{step.duration}s</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Available Missions */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Available Missions</h3>
        
        <div className="grid gap-4">
          {sampleMissions.map((mission, index) => (
            <div
              key={index}
              className={`border rounded-lg p-4 cursor-pointer transition-all ${
                selectedMissionIndex === index
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
              onClick={() => setSelectedMissionIndex(selectedMissionIndex === index ? null : index)}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900">{mission.name}</h4>
                  <p className="text-sm text-gray-600 mt-1">{mission.description}</p>
                  <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                    <div className="flex items-center space-x-1">
                      <Target className="w-3 h-3" />
                      <span>{mission.steps.length} steps</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Clock className="w-3 h-3" />
                      <span>{mission.estimatedDuration}s</span>
                    </div>
                  </div>
                </div>
                
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    startMission(mission);
                  }}
                  disabled={disabled || !!currentMission}
                  className="btn btn-primary flex items-center space-x-1 ml-4"
                >
                  <Play className="w-4 h-4" />
                  <span>Start</span>
                </button>
              </div>

              {/* Expanded Mission Details */}
              {selectedMissionIndex === index && (
                <div className="mt-4 pt-4 border-t border-blue-200">
                  <h5 className="font-medium text-sm text-gray-900 mb-2">Mission Steps:</h5>
                  <div className="space-y-2">
                    {mission.steps.map((step, stepIndex) => (
                      <div key={step.id} className="flex items-center space-x-3 text-sm">
                        <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center text-xs font-medium">
                          {stepIndex + 1}
                        </div>
                        <div className="flex-1">
                          <div className="font-medium">{step.name}</div>
                          <div className="text-gray-500">{step.description}</div>
                        </div>
                        <div className="text-gray-400">{step.duration}s</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};