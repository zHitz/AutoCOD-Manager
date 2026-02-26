import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge } from './ui/Primitives';
import { Zap, Trash, HardDrive, Download, RotateCcw, Power, ShieldCheck, Cpu } from 'lucide-react';

interface ActionCardProps {
  title: string;
  description: string;
  icon: React.ElementType;
  colorClass: string;
  buttonText?: string;
}

const ActionCard: React.FC<ActionCardProps> = ({ title, description, icon: Icon, colorClass, buttonText = "Run Now" }) => {
  const [loading, setLoading] = useState(false);

  const handleRun = () => {
    setLoading(true);
    setTimeout(() => setLoading(false), 2000);
  };

  return (
    <Card className="hover:border-primary/50 transition-colors">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className={`h-4 w-4 ${colorClass}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold"></div>
        <p className="text-xs text-muted-foreground min-h-[40px] mb-4">
          {description}
        </p>
        <Button 
          className="w-full" 
          variant="secondary" 
          size="sm"
          onClick={handleRun}
          disabled={loading}
        >
          {loading ? "Processing..." : buttonText}
        </Button>
      </CardContent>
    </Card>
  );
};

export const ActionsTab: React.FC = () => {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Quick Actions</h2>
        <p className="text-muted-foreground text-sm">Perform system maintenance and batch operations.</p>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
           <ShieldCheck className="w-5 h-5 text-primary" /> System Maintenance
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <ActionCard 
            title="Clear Shader Cache" 
            description="Remove compiled shaders for all emulators to fix graphical glitches."
            icon={Trash}
            colorClass="text-red-500"
            buttonText="Clear Cache"
          />
          <ActionCard 
            title="Release RAM" 
            description="Force close background processes to free up memory for gaming."
            icon={Cpu}
            colorClass="text-blue-500"
            buttonText="Optimize RAM"
          />
          <ActionCard 
            title="Clean Temp Files" 
            description="Delete temporary files created by Android emulators (BlueStacks, Nox)."
            icon={HardDrive}
            colorClass="text-orange-500"
            buttonText="Clean Files"
          />
          <ActionCard 
            title="Reset Networking" 
            description="Restart ADB server and flush DNS to fix connectivity issues."
            icon={RotateCcw}
            colorClass="text-green-500"
            buttonText="Reset Network"
          />
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
           <Download className="w-5 h-5 text-primary" /> Batch Operations
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <ActionCard 
            title="Update All Cores" 
            description="Download the latest nightly cores for RetroArch and standalones."
            icon={Download}
            colorClass="text-indigo-500"
            buttonText="Check Updates"
          />
          <ActionCard 
            title="Backup All Saves" 
            description="Create a compressed archive of all save states and memory cards."
            icon={HardDrive}
            colorClass="text-purple-500"
            buttonText="Start Backup"
          />
          <ActionCard 
            title="Stop All Emulators" 
            description="Immediately terminate all running emulator instances."
            icon={Power}
            colorClass="text-red-600"
            buttonText="Force Stop"
          />
           <ActionCard 
            title="Export Configs" 
            description="Export controller profiles and keymaps to a JSON file."
            icon={Zap}
            colorClass="text-yellow-500"
            buttonText="Export"
          />
        </div>
      </div>
    </div>
  );
};