import { useState, useEffect } from 'react';
import Head from 'next/head';

// Simple robot control interface
export default function Dashboard() {
  const [isConnected, setIsConnected] = useState(false);
  const [robots, setRobots] = useState([]);
  const [selectedRobot, setSelectedRobot] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');

  // Mock robot data
  useEffect(() => {
    // Simulate robot data
    const mockRobots = [
      {
        id: 'robot-001',
        name: 'MediBot Alpha',
        status: 'connected',
        battery: 85,
        position: { x: 10.5, y: 5.2, rotation: 45 },
        mission: {
          name: 'Medicine Delivery',
          progress: 65
        }
      },
      {
        id: 'robot-002', 
        name: 'MediBot Beta',
        status: 'connected',
        battery: 72,
        position: { x: 8.1, y: 12.3, rotation: 180 },
        mission: null
      }
    ];
    
    setRobots(mockRobots);
    setIsConnected(true);
    setConnectionStatus('connected');
  }, []);

  const sendCommand = (command, params = {}) => {
    console.log('Sending command:', command, params);
    // WebSocket command sending would go here
  };

  const emergencyStop = () => {
    sendCommand('emergency_stop');
    alert('EMERGENCY STOP ACTIVATED!');
  };

  return (
    <>
      <Head>
        <title>Medi Runner Challenge 2025 - Dashboard</title>
        <meta name="description" content="Real-time robot control dashboard" />
      </Head>

      <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5', fontFamily: 'Arial, sans-serif' }}>
        {/* Header */}
        <header style={{ backgroundColor: 'white', padding: '1rem', borderBottom: '1px solid #e5e5e5' }}>
          <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#333' }}>
              Medi Runner Challenge 2025
            </h1>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{ 
                  width: '12px', 
                  height: '12px', 
                  borderRadius: '50%', 
                  backgroundColor: isConnected ? '#22c55e' : '#ef4444' 
                }} />
                <span style={{ fontSize: '0.9rem', color: '#666' }}>
                  {connectionStatus}
                </span>
              </div>
              
              <button
                onClick={emergencyStop}
                style={{
                  backgroundColor: '#dc2626',
                  color: 'white',
                  padding: '0.5rem 1rem',
                  border: 'none',
                  borderRadius: '0.5rem',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
              >
                EMERGENCY STOP
              </button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 1fr', gap: '2rem' }}>
            
            {/* Left Panel - Robot List */}
            <div style={{ backgroundColor: 'white', borderRadius: '0.5rem', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 'bold', marginBottom: '1rem' }}>
                Robots ({robots.length})
              </h2>
              
              {robots.map((robot) => (
                <div
                  key={robot.id}
                  onClick={() => setSelectedRobot(robot)}
                  style={{
                    padding: '1rem',
                    border: selectedRobot?.id === robot.id ? '2px solid #3b82f6' : '2px solid #e5e5e5',
                    borderRadius: '0.5rem',
                    marginBottom: '1rem',
                    cursor: 'pointer',
                    backgroundColor: selectedRobot?.id === robot.id ? '#eff6ff' : 'white'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 'bold' }}>{robot.name}</h3>
                    <div style={{ 
                      width: '8px', 
                      height: '8px', 
                      borderRadius: '50%', 
                      backgroundColor: robot.status === 'connected' ? '#22c55e' : '#ef4444' 
                    }} />
                  </div>
                  
                  <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.5rem' }}>
                    Battery: {robot.battery}% | Position: ({robot.position.x.toFixed(1)}, {robot.position.y.toFixed(1)})
                  </div>
                  
                  {robot.mission && (
                    <div style={{ backgroundColor: '#dbeafe', padding: '0.5rem', borderRadius: '0.25rem' }}>
                      <div style={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#1e40af' }}>
                        {robot.mission.name} - {robot.mission.progress}%
                      </div>
                      <div style={{ 
                        width: '100%', 
                        height: '4px', 
                        backgroundColor: '#93c5fd', 
                        borderRadius: '2px',
                        marginTop: '0.25rem'
                      }}>
                        <div style={{ 
                          width: `${robot.mission.progress}%`, 
                          height: '100%', 
                          backgroundColor: '#1e40af', 
                          borderRadius: '2px',
                          transition: 'width 0.3s ease'
                        }} />
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Center Panel - Robot Control */}
            <div style={{ backgroundColor: 'white', borderRadius: '0.5rem', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
              {selectedRobot ? (
                <>
                  <h2 style={{ fontSize: '1.2rem', fontWeight: 'bold', marginBottom: '1rem' }}>
                    Control Panel - {selectedRobot.name}
                  </h2>
                  
                  {/* Movement Controls */}
                  <div style={{ marginBottom: '2rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 'bold', marginBottom: '1rem' }}>Movement</h3>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', maxWidth: '200px', margin: '0 auto' }}>
                      <div></div>
                      <button
                        onClick={() => sendCommand('move', { direction: 'forward' })}
                        style={{ padding: '1rem', backgroundColor: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: '0.5rem', cursor: 'pointer' }}
                      >
                        ↑
                      </button>
                      <div></div>

                      <button
                        onClick={() => sendCommand('move', { direction: 'left' })}
                        style={{ padding: '1rem', backgroundColor: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: '0.5rem', cursor: 'pointer' }}
                      >
                        ←
                      </button>
                      <button
                        onClick={() => sendCommand('stop')}
                        style={{ padding: '1rem', backgroundColor: '#fca5a5', border: '1px solid #f87171', borderRadius: '0.5rem', cursor: 'pointer', color: 'white' }}
                      >
                        ■
                      </button>
                      <button
                        onClick={() => sendCommand('move', { direction: 'right' })}
                        style={{ padding: '1rem', backgroundColor: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: '0.5rem', cursor: 'pointer' }}
                      >
                        →
                      </button>

                      <div></div>
                      <button
                        onClick={() => sendCommand('move', { direction: 'backward' })}
                        style={{ padding: '1rem', backgroundColor: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: '0.5rem', cursor: 'pointer' }}
                      >
                        ↓
                      </button>
                      <div></div>
                    </div>
                  </div>

                  {/* PID Control Section */}
                  <div style={{ marginBottom: '2rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 'bold', marginBottom: '1rem' }}>PID Control</h3>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', marginBottom: '1rem' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '0.25rem' }}>Kp</label>
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          max="10"
                          defaultValue="1.0"
                          style={{ width: '100%', padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '0.25rem' }}
                        />
                      </div>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '0.25rem' }}>Ki</label>
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          max="10"
                          defaultValue="0.0"
                          style={{ width: '100%', padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '0.25rem' }}
                        />
                      </div>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '0.25rem' }}>Kd</label>
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          max="10"
                          defaultValue="0.0"
                          style={{ width: '100%', padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '0.25rem' }}
                        />
                      </div>
                    </div>
                    
                    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                      <button
                        onClick={() => sendCommand('set_pid_values', { kp: 1.0, ki: 0.0, kd: 0.0 })}
                        style={{ flex: 1, padding: '0.5rem', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '0.25rem', cursor: 'pointer' }}
                      >
                        Update PID
                      </button>
                      <button
                        onClick={() => sendCommand('reset_pid')}
                        style={{ flex: 1, padding: '0.5rem', backgroundColor: '#f59e0b', color: 'white', border: 'none', borderRadius: '0.25rem', cursor: 'pointer' }}
                      >
                        Reset PID
                      </button>
                    </div>
                    
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        onClick={() => sendCommand('start_line_following', { base_speed: 50 })}
                        style={{ flex: 1, padding: '0.75rem', backgroundColor: '#10b981', color: 'white', border: 'none', borderRadius: '0.25rem', cursor: 'pointer', fontWeight: 'bold' }}
                      >
                        Start Line Following
                      </button>
                      <button
                        onClick={() => sendCommand('stop_line_following')}
                        style={{ flex: 1, padding: '0.75rem', backgroundColor: '#ef4444', color: 'white', border: 'none', borderRadius: '0.25rem', cursor: 'pointer', fontWeight: 'bold' }}
                      >
                        Stop Line Following
                      </button>
                    </div>
                  </div>

                  {/* Robot Status */}
                  <div style={{ padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>Status</h3>
                    <div style={{ fontSize: '0.9rem', color: '#666' }}>
                      <div>Position: X: {selectedRobot.position.x}m, Y: {selectedRobot.position.y}m</div>
                      <div>Rotation: {selectedRobot.position.rotation}°</div>
                      <div>Battery: {selectedRobot.battery}%</div>
                      <div>Status: {selectedRobot.status}</div>
                    </div>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
                  <div style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>No Robot Selected</div>
                  <div>Select a robot from the list to view controls</div>
                </div>
              )}
            </div>

            {/* Right Panel - Camera/Mission */}
            <div style={{ backgroundColor: 'white', borderRadius: '0.5rem', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 'bold', marginBottom: '1rem' }}>
                Camera Feed
              </h2>
              
              <div style={{ 
                width: '100%', 
                height: '200px', 
                backgroundColor: '#1f2937', 
                borderRadius: '0.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                marginBottom: '1rem'
              }}>
                📷 Camera Feed Placeholder
              </div>
              
              {selectedRobot?.mission && (
                <div style={{ marginTop: '1rem' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>Current Mission</h3>
                  <div style={{ padding: '1rem', backgroundColor: '#dbeafe', borderRadius: '0.5rem' }}>
                    <div style={{ fontWeight: 'bold', color: '#1e40af' }}>{selectedRobot.mission.name}</div>
                    <div style={{ fontSize: '0.8rem', color: '#1e40af', marginTop: '0.25rem' }}>
                      Progress: {selectedRobot.mission.progress}%
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </>
  );
}