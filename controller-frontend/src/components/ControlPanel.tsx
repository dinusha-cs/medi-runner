import React, { useState } from 'react';
import { 
  ArrowUp, 
  ArrowDown, 
  ArrowLeft, 
  ArrowRight, 
  RotateCcw, 
  RotateCw, 
  Square,
  Play,
  Pause,
  Hand
} from 'lucide-react';
import { RobotState, Command } from '@/types';

interface ControlPanelProps {
  robot: RobotState;
  onCommand: (command: Omit<Command, 'id' | 'timestamp' | 'acknowledged' | 'completed'>) => void;
  disabled?: boolean;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({ robot, onCommand, disabled }) => {
  const [speed, setSpeed] = useState(50);
  const [gripperPosition, setGripperPosition] = useState(robot.actuators.gripper.position);

  const sendMoveCommand = (direction: string, distance: number = 1.0) => {
    onCommand({
      type: 'move',
      parameters: {
        direction,
        distance,
        speed: speed / 100,
      },
    });
  };

  const sendRotateCommand = (angle: number) => {
    onCommand({
      type: 'rotate',
      parameters: {
        angle,
        speed: speed / 100,
      },
    });
  };

  const sendStopCommand = () => {
    onCommand({
      type: 'stop',
      parameters: {},
    });
  };

  const sendGripperCommand = (action: 'open' | 'close' | 'position') => {
    onCommand({
      type: 'pickup',
      parameters: {
        action,
        position: action === 'position' ? gripperPosition : undefined,
      },
    });
  };

  return (
    <div className="p-6 space-y-6">
      {/* Speed Control */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Speed: {speed}%
        </label>
        <input
          type="range"
          min="10"
          max="100"
          value={speed}
          onChange={(e) => setSpeed(Number(e.target.value))}
          disabled={disabled}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
        />
      </div>

      {/* Movement Controls */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Movement</h3>
        
        <div className="grid grid-cols-3 gap-2 max-w-xs mx-auto">
          {/* Top row */}
          <div></div>
          <button
            onClick={() => sendMoveCommand('forward')}
            disabled={disabled}
            className="btn btn-secondary p-4 aspect-square flex items-center justify-center"
          >
            <ArrowUp className="w-6 h-6" />
          </button>
          <div></div>

          {/* Middle row */}
          <button
            onClick={() => sendMoveCommand('left')}
            disabled={disabled}
            className="btn btn-secondary p-4 aspect-square flex items-center justify-center"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <button
            onClick={sendStopCommand}
            disabled={disabled}
            className="btn btn-danger p-4 aspect-square flex items-center justify-center"
          >
            <Square className="w-6 h-6" />
          </button>
          <button
            onClick={() => sendMoveCommand('right')}
            disabled={disabled}
            className="btn btn-secondary p-4 aspect-square flex items-center justify-center"
          >
            <ArrowRight className="w-6 h-6" />
          </button>

          {/* Bottom row */}
          <button
            onClick={() => sendRotateCommand(-90)}
            disabled={disabled}
            className="btn btn-secondary p-4 aspect-square flex items-center justify-center"
          >
            <RotateCcw className="w-6 h-6" />
          </button>
          <button
            onClick={() => sendMoveCommand('backward')}
            disabled={disabled}
            className="btn btn-secondary p-4 aspect-square flex items-center justify-center"
          >
            <ArrowDown className="w-6 h-6" />
          </button>
          <button
            onClick={() => sendRotateCommand(90)}
            disabled={disabled}
            className="btn btn-secondary p-4 aspect-square flex items-center justify-center"
          >
            <RotateCw className="w-6 h-6" />
          </button>
        </div>
      </div>

      {/* Gripper Controls */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Gripper Control</h3>
        
        <div className="space-y-3">
          <div className="flex space-x-2">
            <button
              onClick={() => sendGripperCommand('open')}
              disabled={disabled}
              className="btn btn-success flex-1 flex items-center justify-center space-x-2"
            >
              <Hand className="w-4 h-4" />
              <span>Open</span>
            </button>
            <button
              onClick={() => sendGripperCommand('close')}
              disabled={disabled}
              className="btn btn-danger flex-1 flex items-center justify-center space-x-2"
            >
              <Hand className="w-4 h-4" />
              <span>Close</span>
            </button>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Position: {gripperPosition}%
            </label>
            <div className="flex space-x-2">
              <input
                type="range"
                min="0"
                max="100"
                value={gripperPosition}
                onChange={(e) => setGripperPosition(Number(e.target.value))}
                disabled={disabled}
                className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <button
                onClick={() => sendGripperCommand('position')}
                disabled={disabled}
                className="btn btn-primary px-3 py-1 text-sm"
              >
                Set
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Robot Status Display */}
      <div className="border-t pt-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Status</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="space-y-1">
            <div className="text-gray-600">Position:</div>
            <div className="font-mono">
              X: {robot.position.x.toFixed(2)}m<br />
              Y: {robot.position.y.toFixed(2)}m<br />
              θ: {robot.position.rotation.toFixed(1)}°
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-gray-600">Gripper:</div>
            <div>
              Position: {robot.actuators.gripper.position}%<br />
              Force: {robot.actuators.gripper.force}%<br />
              Object: {robot.actuators.gripper.hasObject ? 'Yes' : 'No'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};