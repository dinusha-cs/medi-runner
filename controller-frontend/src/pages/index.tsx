import React from 'react';
import Head from 'next/head';
import { Toaster } from 'react-hot-toast';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAppStore, useRobots, useSelectedRobot } from '@/store';
import { RobotList } from '@/components/RobotList';
import { ControlPanel } from '@/components/ControlPanel';
import { MissionManager } from '@/components/MissionManager';
import { SystemStatus } from '@/components/SystemStatus';
import { CameraView } from '@/components/CameraView';
import { EmergencyButton } from '@/components/EmergencyButton';

const WEBSOCKET_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:3001';

const Dashboard: React.FC = () => {
  const robots = useRobots();
  const selectedRobot = useSelectedRobot();
  const { selectRobot } = useAppStore();
  const { isConnected, sendCommand, emergencyStop } = useWebSocket(WEBSOCKET_URL);

  return (
    <>
      <Head>
        <title>Medi Runner Challenge 2025 - Dashboard</title>
        <meta name="description" content="Real-time robot control dashboard" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        <Toaster position="top-right" />
        
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center space-x-4">
                <h1 className="text-xl font-bold text-gray-900">
                  Medi Runner Challenge 2025
                </h1>
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${
                    isConnected ? 'bg-green-500' : 'bg-red-500'
                  }`} />
                  <span className="text-sm text-gray-600">
                    {isConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
              </div>
              
              <div className="flex items-center space-x-4">
                <SystemStatus />
                <EmergencyButton onEmergencyStop={emergencyStop} />
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Left Panel - Robot List */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Robots ({robots.length})
                </h2>
                <RobotList 
                  robots={robots}
                  selectedRobotId={selectedRobot?.id}
                  onSelectRobot={selectRobot}
                />
              </div>
            </div>

            {/* Center Panel - Main Controls */}
            <div className="lg:col-span-2 space-y-8">
              {selectedRobot ? (
                <>
                  {/* Robot Control Panel */}
                  <div className="bg-white rounded-lg shadow-sm">
                    <div className="p-6 border-b">
                      <h2 className="text-lg font-semibold text-gray-900">
                        Control Panel - {selectedRobot.name}
                      </h2>
                    </div>
                    <ControlPanel 
                      robot={selectedRobot}
                      onCommand={sendCommand}
                      disabled={!isConnected}
                    />
                  </div>

                  {/* Mission Manager */}
                  <div className="bg-white rounded-lg shadow-sm">
                    <div className="p-6 border-b">
                      <h2 className="text-lg font-semibold text-gray-900">
                        Mission Control
                      </h2>
                    </div>
                    <MissionManager 
                      robotId={selectedRobot.id}
                      currentMission={selectedRobot.mission}
                      onCommand={sendCommand}
                      disabled={!isConnected}
                    />
                  </div>
                </>
              ) : (
                <div className="bg-white rounded-lg shadow-sm p-12 text-center">
                  <div className="text-gray-500">
                    <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
                      <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                        <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      No Robot Selected
                    </h3>
                    <p>Select a robot from the list to view controls and manage missions.</p>
                  </div>
                </div>
              )}
            </div>

            {/* Right Panel - Camera Feeds */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-lg shadow-sm">
                <div className="p-6 border-b">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Camera Feeds
                  </h2>
                </div>
                <CameraView robotId={selectedRobot?.id} />
              </div>
            </div>
          </div>
        </main>
      </div>
    </>
  );
};

export default Dashboard;