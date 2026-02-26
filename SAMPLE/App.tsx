import React, { useState, useEffect } from 'react';
import { Layout } from './components/Layout';
import { EmulatorDashboard } from './components/EmulatorDashboard';
import { GameLibrary } from './components/GameLibrary';
import { EmulatorsManage } from './components/EmulatorsManage';
import { ActionsTab } from './components/ActionsTab';
import { Settings } from './components/Settings';
import { ViewState, Emulator, Game, SystemStats } from './types';

// Mock Data
const MOCK_EMULATORS: Emulator[] = [
  { id: 'bluestacks', name: 'BlueStacks 5', version: '5.12.0', status: 'running', core: 'Android 11', icon: '' },
  { id: 'ldplayer', name: 'LDPlayer 9', version: '9.0.48', status: 'stopped', core: 'Android 9', icon: '' },
  { id: 'nox', name: 'NoxPlayer', version: '7.0.5.9', status: 'stopped', core: 'Android 9', icon: '' },
  { id: 'yuzu', name: 'Yuzu', version: 'EA 3652', status: 'stopped', core: 'Switch', icon: '' },
  { id: 'pcsx2', name: 'PCSX2', version: '1.7.4520', status: 'stopped', core: 'PS2', icon: '' },
  { id: 'dolphin', name: 'Dolphin', version: '5.0-1982', status: 'stopped', core: 'GameCube/Wii', icon: '' },
];

const MOCK_GAMES: Game[] = [
  { id: '1', title: 'PUBG Mobile', platform: 'Android', coverUrl: 'https://picsum.photos/300/400?random=10', playTimeHrs: 340, lastPlayed: '10 mins ago', emulatorId: 'bluestacks', favorite: true },
  { id: '2', title: 'Genshin Impact', platform: 'Android', coverUrl: 'https://picsum.photos/300/400?random=11', playTimeHrs: 850, lastPlayed: 'Yesterday', emulatorId: 'ldplayer', favorite: true },
  { id: '3', title: 'Arknights', platform: 'Android', coverUrl: 'https://picsum.photos/300/400?random=12', playTimeHrs: 120, lastPlayed: '3 hours ago', emulatorId: 'bluestacks', favorite: false },
  { id: '4', title: 'The Legend of Zelda: TOTK', platform: 'Switch', coverUrl: 'https://picsum.photos/300/400?random=1', playTimeHrs: 120, lastPlayed: '2 days ago', emulatorId: 'yuzu', favorite: true },
  { id: '5', title: 'God of War II', platform: 'PS2', coverUrl: 'https://picsum.photos/300/400?random=4', playTimeHrs: 40, lastPlayed: 'Last week', emulatorId: 'pcsx2', favorite: false },
  { id: '6', title: 'Super Mario Galaxy 2', platform: 'Wii', coverUrl: 'https://picsum.photos/300/400?random=6', playTimeHrs: 30, lastPlayed: 'A month ago', emulatorId: 'dolphin', favorite: false },
];

export default function App() {
  const [currentView, setCurrentView] = useState<ViewState>(ViewState.DASHBOARD);
  const [emulators, setEmulators] = useState<Emulator[]>(MOCK_EMULATORS);
  const [stats, setStats] = useState<SystemStats>({
    cpuUsage: 15,
    gpuUsage: 5,
    ramUsage: 8.4,
    fps: 144,
    temperature: 42
  });

  // Mock live stats update
  useEffect(() => {
    const interval = setInterval(() => {
      setStats(prev => ({
        ...prev,
        cpuUsage: Math.floor(Math.random() * 20) + 10,
        gpuUsage: Math.floor(Math.random() * 30) + 20,
        ramUsage: Number((Math.random() * 2 + 8).toFixed(1)),
        temperature: Math.floor(Math.random() * 5) + 40,
      }));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleEmulator = (id: string) => {
    setEmulators(prev => prev.map(emu => {
      if (emu.id === id) {
        return { ...emu, status: emu.status === 'running' ? 'stopped' : 'running' };
      }
      return emu;
    }));
  };

  const handleLaunchGame = (id: string) => {
    console.log(`Launching game ${id}...`);
  };

  const handleUpdateEmulator = (id: string) => {
    setEmulators(prev => prev.map(emu => 
      emu.id === id ? { ...emu, status: 'updating' } : emu
    ));
    setTimeout(() => {
      setEmulators(prev => prev.map(emu => 
        emu.id === id ? { ...emu, status: 'stopped', version: 'Latest' } : emu
      ));
    }, 2000);
  };

  const handleDeleteEmulator = (id: string) => {
    if (confirm('Are you sure you want to uninstall this emulator?')) {
       setEmulators(prev => prev.filter(emu => emu.id !== id));
    }
  };

  return (
    <Layout currentView={currentView} onNavigate={setCurrentView}>
      {currentView === ViewState.DASHBOARD && (
        <EmulatorDashboard 
          stats={stats} 
          emulators={emulators} 
          onToggleEmulator={handleToggleEmulator} 
        />
      )}
      
      {currentView === ViewState.LIBRARY && (
        <GameLibrary 
          games={MOCK_GAMES} 
          onLaunchGame={handleLaunchGame} 
        />
      )}

      {currentView === ViewState.EMULATORS && (
        <EmulatorsManage 
          emulators={emulators} 
          onUpdate={handleUpdateEmulator}
          onDelete={handleDeleteEmulator}
          onToggle={handleToggleEmulator}
        />
      )}

      {currentView === ViewState.ACTIONS && (
        <ActionsTab />
      )}

      {currentView === ViewState.SETTINGS && (
        <Settings />
      )}
    </Layout>
  );
}