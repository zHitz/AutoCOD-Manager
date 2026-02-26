import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, Badge, Button } from './ui/Primitives';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Play, Pause, RefreshCw, Cpu, Monitor, Zap } from 'lucide-react';
import { Emulator, SystemStats } from '../types';

interface DashboardProps {
  stats: SystemStats;
  emulators: Emulator[];
  onToggleEmulator: (id: string) => void;
}

const data = [
  { name: '0s', cpu: 10, gpu: 20 },
  { name: '10s', cpu: 25, gpu: 35 },
  { name: '20s', cpu: 45, gpu: 50 },
  { name: '30s', cpu: 30, gpu: 45 },
  { name: '40s', cpu: 60, gpu: 70 },
  { name: '50s', cpu: 55, gpu: 65 },
  { name: '60s', cpu: 40, gpu: 45 },
];

export const EmulatorDashboard: React.FC<DashboardProps> = ({ stats, emulators, onToggleEmulator }) => {
  return (
    <div className="space-y-6">
      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border-indigo-500/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">CPU Load</CardTitle>
            <Cpu className="w-4 h-4 text-indigo-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-indigo-600">{stats.cpuUsage}%</div>
            <p className="text-xs text-muted-foreground mt-1">i9-13900K @ 5.2GHz</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border-emerald-500/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">GPU Load</CardTitle>
            <Monitor className="w-4 h-4 text-emerald-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-600">{stats.gpuUsage}%</div>
            <p className="text-xs text-muted-foreground mt-1">RTX 4090 • {stats.temperature}°C</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-orange-500/10 to-red-500/10 border-orange-500/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Memory</CardTitle>
            <Zap className="w-4 h-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats.ramUsage} GB</div>
            <p className="text-xs text-muted-foreground mt-1">32GB DDR5 Total</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Chart */}
      <Card className="col-span-3 h-[300px]">
        <CardHeader>
          <CardTitle>System Performance</CardTitle>
        </CardHeader>
        <CardContent className="h-[250px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorGpu" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#059669" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#059669" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
              <XAxis dataKey="name" stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e5e7eb', borderRadius: '0.5rem', color: '#1f2937' }} 
                itemStyle={{ color: '#1f2937' }}
              />
              <Area type="monotone" dataKey="cpu" stroke="#4f46e5" fillOpacity={1} fill="url(#colorCpu)" strokeWidth={2} />
              <Area type="monotone" dataKey="gpu" stroke="#059669" fillOpacity={1} fill="url(#colorGpu)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Emulators List */}
      <div className="grid grid-cols-1 gap-4">
        <h2 className="text-lg font-semibold tracking-tight">Installed Emulators</h2>
        {emulators.map((emu) => (
          <Card key={emu.id} className="flex items-center p-4 gap-4 hover:bg-accent/50 transition-colors">
            <div className="w-12 h-12 rounded bg-slate-100 flex items-center justify-center text-lg font-bold text-slate-500 border border-slate-200">
              {emu.id.substring(0, 2).toUpperCase()}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">{emu.name}</h3>
                <Badge variant={emu.status === 'running' ? 'success' : 'secondary'} className="text-[10px] uppercase tracking-wider">
                  {emu.status}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">Version: {emu.version} • Core: {emu.core}</p>
            </div>
            <div className="flex items-center gap-2">
               {emu.status === 'updating' ? (
                  <Button disabled size="sm" variant="outline" className="gap-2">
                    <RefreshCw className="w-3 h-3 animate-spin" /> Updating
                  </Button>
               ) : (
                  <>
                     <Button size="sm" variant="outline">Config</Button>
                     <Button 
                       size="sm" 
                       variant={emu.status === 'running' ? "destructive" : "default"} 
                       onClick={() => onToggleEmulator(emu.id)}
                       className="w-24 gap-2"
                     >
                        {emu.status === 'running' ? <><Pause className="w-3 h-3"/> Stop</> : <><Play className="w-3 h-3"/> Launch</>}
                     </Button>
                  </>
               )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};