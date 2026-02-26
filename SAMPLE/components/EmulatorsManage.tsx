import React, { useState, useEffect, useRef } from 'react';
import { Emulator } from '../types';
import { Card, Button, Badge, Switch } from './ui/Primitives';
import { 
  Settings, Power, RefreshCw, Camera, Maximize2, 
  Mic, MicOff, Volume2, VolumeX, Play, Square, Activity,
  LayoutTemplate, Grid, Monitor
} from 'lucide-react';

interface EmulatorsManageProps {
  emulators: Emulator[];
  onUpdate: (id: string) => void;
  onDelete: (id: string) => void;
  onToggle: (id: string) => void;
}

// Mock mapping for emulator "screens"
const getScreenImage = (id: string) => {
  const images: Record<string, string> = {
    'bluestacks': 'https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&q=80&w=1000',
    'yuzu': 'https://images.unsplash.com/photo-1612287230217-12742251039d?auto=format&fit=crop&q=80&w=1000',
    'pcsx2': 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&q=80&w=1000',
    'ldplayer': 'https://images.unsplash.com/photo-1538481199705-c710c4e965fc?auto=format&fit=crop&q=80&w=1000',
  };
  return images[id] || 'https://images.unsplash.com/photo-1551103782-8ab07afd45c1?auto=format&fit=crop&q=80&w=1000';
};

const MonitorCard: React.FC<{ emu: Emulator; onToggle: (id: string) => void }> = ({ emu, onToggle }) => {
  const [fps, setFps] = useState(60);
  const [isMuted, setIsMuted] = useState(false);
  
  // Simulate live stats
  useEffect(() => {
    const interval = setInterval(() => {
      setFps(prev => Math.max(30, Math.min(144, prev + (Math.random() * 10 - 5))));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Card className="overflow-hidden border-2 border-primary/20 bg-black relative group shadow-xl h-full flex flex-col">
      {/* Screen Content */}
      <div className="aspect-video relative bg-slate-900 flex-1">
        <img 
          src={getScreenImage(emu.id)} 
          alt="Monitor" 
          className="w-full h-full object-cover opacity-80 group-hover:opacity-60 transition-opacity duration-300"
        />
        
        {/* Live Overlay UI */}
        <div className="absolute inset-0 p-4 flex flex-col justify-between">
          {/* Top Bar */}
          <div className="flex items-start justify-between">
             <div className="flex items-center gap-2 bg-black/60 backdrop-blur-md text-white px-3 py-1.5 rounded-full border border-white/10">
                <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <span className="text-xs font-bold tracking-wider">LIVE</span>
                <div className="w-px h-3 bg-white/20 mx-1" />
                <span className="text-xs font-mono">{emu.name}</span>
             </div>

             <div className="flex gap-2">
                <div className="bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 flex items-center gap-2">
                   <Activity className="w-3 h-3 text-green-400" />
                   <span className="text-xs font-mono text-green-400 font-bold">{Math.round(fps)} FPS</span>
                </div>
             </div>
          </div>

          {/* Center Action (Hidden by default, shown on hover) */}
          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
             <Button 
                size="lg" 
                variant="destructive" 
                className="pointer-events-auto rounded-full w-16 h-16 shadow-2xl"
                onClick={() => onToggle(emu.id)}
             >
                <Square className="w-6 h-6 fill-current" />
             </Button>
          </div>

          {/* Bottom Control Bar */}
          <div className="bg-black/80 backdrop-blur-md rounded-xl p-2 border border-white/10 flex items-center justify-between translate-y-full group-hover:translate-y-0 transition-transform duration-300">
             <div className="flex items-center gap-1">
                <Button size="icon" variant="ghost" className="text-white hover:bg-white/20 h-8 w-8" onClick={() => setIsMuted(!isMuted)}>
                   {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                </Button>
                <Button size="icon" variant="ghost" className="text-white hover:bg-white/20 h-8 w-8">
                   <Mic className="w-4 h-4" />
                </Button>
             </div>

             <div className="flex items-center gap-2">
                <Button size="sm" variant="secondary" className="h-7 text-xs gap-1 bg-white/10 hover:bg-white/20 text-white border-0">
                   <RefreshCw className="w-3 h-3" /> Restart
                </Button>
                <Button size="sm" variant="secondary" className="h-7 text-xs gap-1 bg-white/10 hover:bg-white/20 text-white border-0">
                   <Camera className="w-3 h-3" /> Snap
                </Button>
                <Button size="sm" variant="secondary" className="h-7 text-xs gap-1 bg-white/10 hover:bg-white/20 text-white border-0">
                   <Settings className="w-3 h-3" /> Config
                </Button>
             </div>

             <Button size="icon" variant="ghost" className="text-white hover:bg-white/20 h-8 w-8">
                <Maximize2 className="w-4 h-4" />
             </Button>
          </div>
        </div>
      </div>
    </Card>
  );
};

export const EmulatorsManage: React.FC<EmulatorsManageProps> = ({ emulators, onUpdate, onDelete, onToggle }) => {
  const runningEmulators = emulators.filter(e => e.status === 'running');
  const stoppedEmulators = emulators.filter(e => e.status !== 'running');

  // Monitor Settings State
  const [gridCols, setGridCols] = useState(2);
  const [autoResize, setAutoResize] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (settingsRef.current && !settingsRef.current.contains(event.target as Node)) {
        setShowSettings(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="space-y-8">
      {/* Header with Settings */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-2xl font-bold tracking-tight">Monitor & Control</h2>
          <p className="text-muted-foreground text-sm">Real-time management of active emulator instances.</p>
        </div>
        
        {/* Settings Dropdown */}
        <div className="relative" ref={settingsRef}>
          <Button 
            variant="outline" 
            size="sm" 
            className="gap-2"
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings className="w-4 h-4" /> View Options
          </Button>

          {showSettings && (
            <div className="absolute right-0 top-full mt-2 w-72 bg-popover text-popover-foreground border border-border rounded-lg shadow-xl p-4 z-50 animate-in slide-in-from-top-2 fade-in duration-200">
               <div className="flex items-center gap-2 mb-4 border-b border-border pb-2">
                 <LayoutTemplate className="w-4 h-4 text-primary" />
                 <h4 className="font-semibold text-sm">Grid Arrangement</h4>
               </div>
               
               <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Auto-Resize Windows</span>
                    <Switch checked={autoResize} onCheckedChange={setAutoResize} />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Automatically adjust grid based on window size.
                  </p>

                  <div className={`space-y-2 transition-opacity ${autoResize ? 'opacity-50 pointer-events-none' : ''}`}>
                     <span className="text-sm font-medium block">Windows per row</span>
                     <div className="grid grid-cols-4 gap-2">
                       {[1, 2, 3, 4].map(n => (
                         <Button 
                           key={n} 
                           variant={gridCols === n ? "default" : "outline"} 
                           size="sm" 
                           className="h-8 w-full p-0"
                           onClick={() => setGridCols(n)}
                         >
                           {n}
                         </Button>
                       ))}
                     </div>
                  </div>
               </div>
            </div>
          )}
        </div>
      </div>

      {/* Active Monitors Grid */}
      {runningEmulators.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-green-600 animate-pulse">
               <div className="w-2 h-2 rounded-full bg-green-600" />
               Active Sessions ({runningEmulators.length})
            </div>
          </div>
          
          <div 
            className={`grid gap-6 ${autoResize ? 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3' : ''}`}
            style={!autoResize ? { gridTemplateColumns: `repeat(${gridCols}, minmax(0, 1fr))` } : undefined}
          >
            {runningEmulators.map(emu => (
              <MonitorCard key={emu.id} emu={emu} onToggle={onToggle} />
            ))}
          </div>
        </div>
      ) : (
        <Card className="border-dashed flex flex-col items-center justify-center py-12 text-muted-foreground bg-accent/20">
           <Monitor className="w-12 h-12 mb-4 opacity-50" />
           <h3 className="text-lg font-medium">No Active Emulators</h3>
           <p className="text-sm">Launch an emulator from the library below to start monitoring.</p>
        </Card>
      )}

      {/* Available / Stopped Emulators List */}
      <div className="space-y-4 pt-4 border-t border-border">
        <div className="flex items-center justify-between">
           <h3 className="text-lg font-semibold tracking-tight">Installed Library</h3>
           <Button variant="outline" size="sm" className="gap-2">
              <RefreshCw className="w-3 h-3" /> Check Updates
           </Button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {stoppedEmulators.map((emu) => (
            <Card key={emu.id} className="group hover:border-primary/50 transition-colors p-4 flex items-center gap-4">
              <div className="w-14 h-14 rounded-lg bg-accent flex items-center justify-center text-xl font-bold text-muted-foreground group-hover:text-primary transition-colors">
                {emu.id.substring(0, 2).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <h4 className="font-semibold truncate">{emu.name}</h4>
                  <Badge variant="outline" className="text-[10px]">{emu.version}</Badge>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" className="h-7 text-xs w-full gap-1" onClick={() => onToggle(emu.id)}>
                     <Play className="w-3 h-3" /> Launch
                  </Button>
                  <Button size="icon" variant="ghost" className="h-7 w-7" title="Settings">
                     <Settings className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
          
          {/* Add New Placeholder */}
          <button className="border-2 border-dashed border-border rounded-lg p-4 flex flex-col items-center justify-center text-muted-foreground hover:border-primary hover:text-primary transition-colors gap-2 h-[88px]">
             <span className="font-medium text-sm">+ Add Instance</span>
          </button>
        </div>
      </div>
    </div>
  );
};