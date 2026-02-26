import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, Input, Button, Switch, Label } from './ui/Primitives';
import { Save, Folder, Monitor, Shield, User } from 'lucide-react';

export const Settings: React.FC = () => {
  const [autoUpdate, setAutoUpdate] = useState(true);
  const [discordRich, setDiscordRich] = useState(true);
  const [highPriority, setHighPriority] = useState(false);

  return (
    <div className="max-w-4xl space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Settings</h2>
        <p className="text-muted-foreground text-sm">Manage global application preferences and paths.</p>
      </div>

      <div className="grid gap-6">
        {/* General Settings */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Monitor className="w-5 h-5 text-primary" />
              <CardTitle className="text-lg">General</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Start on Boot</Label>
                <p className="text-sm text-muted-foreground">Launch OmniEmu when Windows starts.</p>
              </div>
              <Switch checked={false} onCheckedChange={() => {}} />
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Auto-Update Emulators</Label>
                <p className="text-sm text-muted-foreground">Automatically check for emulator updates on launch.</p>
              </div>
              <Switch checked={autoUpdate} onCheckedChange={setAutoUpdate} />
            </div>
             <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Discord Rich Presence</Label>
                <p className="text-sm text-muted-foreground">Show currently playing game on Discord.</p>
              </div>
              <Switch checked={discordRich} onCheckedChange={setDiscordRich} />
            </div>
          </CardContent>
        </Card>

        {/* Paths */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Folder className="w-5 h-5 text-primary" />
              <CardTitle className="text-lg">Library Paths</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
             <div className="space-y-2">
               <Label>Games Directory</Label>
               <div className="flex gap-2">
                 <Input defaultValue="C:\Games\ROMs" readOnly />
                 <Button variant="outline" size="icon"><Folder className="w-4 h-4" /></Button>
               </div>
             </div>
             <div className="space-y-2">
               <Label>Screenshots Directory</Label>
               <div className="flex gap-2">
                 <Input defaultValue="C:\Users\Admin\Pictures\OmniEmu" readOnly />
                 <Button variant="outline" size="icon"><Folder className="w-4 h-4" /></Button>
               </div>
             </div>
          </CardContent>
        </Card>

        {/* Performance */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
               <Shield className="w-5 h-5 text-primary" />
              <CardTitle className="text-lg">Performance</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Process High Priority</Label>
                <p className="text-sm text-muted-foreground">Run emulator processes with high priority in Windows.</p>
              </div>
              <Switch checked={highPriority} onCheckedChange={setHighPriority} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
               <div className="space-y-2">
                  <Label>Global FPS Limit</Label>
                  <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <option>Unlimited</option>
                    <option>144 FPS</option>
                    <option>120 FPS</option>
                    <option>60 FPS</option>
                    <option>30 FPS</option>
                  </select>
               </div>
                <div className="space-y-2">
                  <Label>Renderer Backend</Label>
                  <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <option>Auto (Recommended)</option>
                    <option>Vulkan</option>
                    <option>DirectX 12</option>
                    <option>OpenGL</option>
                  </select>
               </div>
            </div>
          </CardContent>
        </Card>

        {/* Account Mockup */}
        <Card>
           <CardHeader>
            <div className="flex items-center gap-2">
               <User className="w-5 h-5 text-primary" />
              <CardTitle className="text-lg">Account</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
             <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-indigo-500 flex items-center justify-center text-white font-bold text-lg">U</div>
                <div>
                   <h4 className="font-semibold">User Admin</h4>
                   <p className="text-sm text-muted-foreground">Pro License Active</p>
                </div>
                <Button variant="outline" className="ml-auto">Manage Subscription</Button>
             </div>
          </CardContent>
        </Card>

        <div className="flex justify-end pt-4">
           <Button className="gap-2">
             <Save className="w-4 h-4" /> Save Changes
           </Button>
        </div>
      </div>
    </div>
  );
};