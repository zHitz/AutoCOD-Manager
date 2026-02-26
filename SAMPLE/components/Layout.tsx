import React, { useState, useRef, useEffect } from 'react';
import { LayoutDashboard, Gamepad2, Settings, MonitorPlay, Zap, Search, Bell, User, LogOut, CreditCard, CheckCircle2, Info, X } from 'lucide-react';
import { ViewState } from '../types';
import { cn } from './ui/Primitives';

interface LayoutProps {
  children: React.ReactNode;
  currentView: ViewState;
  onNavigate: (view: ViewState) => void;
}

export const Layout: React.FC<LayoutProps> = ({ children, currentView, onNavigate }) => {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  
  // Close menus when clicking outside
  const userMenuRef = useRef<HTMLDivElement>(null);
  const notifMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
      if (notifMenuRef.current && !notifMenuRef.current.contains(event.target as Node)) {
        setIsNotificationsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const navItems = [
    { icon: LayoutDashboard, label: 'Dashboard', view: ViewState.DASHBOARD },
    { icon: Gamepad2, label: 'Library', view: ViewState.LIBRARY },
    { icon: MonitorPlay, label: 'Emulators', view: ViewState.EMULATORS },
    { icon: Zap, label: 'Actions', view: ViewState.ACTIONS },
    { icon: Settings, label: 'Settings', view: ViewState.SETTINGS },
  ];

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-card flex flex-col z-20">
        <div className="p-6 flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Gamepad2 className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-xl tracking-tight">OmniEmu</span>
        </div>

        <nav className="flex-1 px-4 space-y-2 mt-4">
          {navItems.map((item) => (
            <button
              key={item.label}
              onClick={() => onNavigate(item.view)}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors",
                currentView === item.view
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </button>
          ))}
        </nav>

        {/* User Profile Section with Popup Menu */}
        <div className="p-4 border-t border-border relative" ref={userMenuRef}>
          {isUserMenuOpen && (
            <div className="absolute bottom-full left-4 right-4 mb-2 bg-popover text-popover-foreground border border-border rounded-lg shadow-xl p-1 animate-in slide-in-from-bottom-2 fade-in duration-200">
              <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent hover:text-accent-foreground transition-colors text-left">
                <User className="w-4 h-4" /> Profile
              </button>
              <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent hover:text-accent-foreground transition-colors text-left">
                <CreditCard className="w-4 h-4" /> Billing
              </button>
              <div className="h-px bg-border my-1" />
              <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-destructive hover:text-destructive-foreground transition-colors text-left text-red-500">
                <LogOut className="w-4 h-4" /> Log out
              </button>
            </div>
          )}
          
          <button 
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            className={cn(
              "flex items-center gap-3 px-4 py-3 rounded-lg w-full text-left transition-all border border-transparent",
              isUserMenuOpen ? "bg-accent border-border shadow-sm" : "bg-accent/50 hover:bg-accent"
            )}
          >
            <div className="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center text-white font-bold shrink-0">
              U
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-medium truncate">User Admin</span>
              <span className="text-xs text-muted-foreground truncate">Pro License</span>
            </div>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-border bg-card/50 backdrop-blur px-8 flex items-center justify-between z-10">
          <div className="flex items-center gap-4 text-muted-foreground">
             <span className="font-medium text-foreground">
               {currentView.charAt(0) + currentView.slice(1).toLowerCase()}
             </span>
          </div>
          <div className="flex items-center gap-4">
             <div className="relative hidden md:block">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input 
                  type="text" 
                  placeholder="Search..." 
                  className="h-9 w-64 rounded-full bg-accent/50 border-none pl-10 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-muted-foreground/70"
                />
             </div>
             
             {/* Notification Bell with Dropdown */}
             <div className="relative" ref={notifMenuRef}>
                <button 
                  onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
                  className={cn(
                    "relative p-2 rounded-full transition-colors",
                    isNotificationsOpen ? "bg-accent text-accent-foreground" : "hover:bg-accent text-muted-foreground"
                  )}
                >
                  <Bell className="w-5 h-5" />
                  <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500 border border-card" />
                </button>

                {isNotificationsOpen && (
                  <div className="absolute top-full right-0 mt-2 w-80 bg-popover text-popover-foreground border border-border rounded-lg shadow-xl overflow-hidden animate-in slide-in-from-top-2 fade-in duration-200">
                    <div className="flex items-center justify-between p-4 border-b border-border bg-accent/20">
                      <h4 className="font-semibold text-sm">Notifications</h4>
                      <button className="text-xs text-primary hover:underline">Mark all read</button>
                    </div>
                    <div className="max-h-[300px] overflow-y-auto">
                      <div className="p-4 border-b border-border/50 hover:bg-accent/30 transition-colors cursor-pointer flex gap-3">
                        <div className="mt-1">
                           <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">Yuzu Updated</p>
                          <p className="text-xs text-muted-foreground mt-1">Successfully updated to Early Access 3653.</p>
                          <span className="text-[10px] text-muted-foreground mt-2 block">2 mins ago</span>
                        </div>
                      </div>
                      <div className="p-4 border-b border-border/50 hover:bg-accent/30 transition-colors cursor-pointer flex gap-3">
                        <div className="mt-1">
                           <Info className="w-4 h-4 text-blue-500" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">Backup Completed</p>
                          <p className="text-xs text-muted-foreground mt-1">Daily save data backup finished successfully.</p>
                          <span className="text-[10px] text-muted-foreground mt-2 block">1 hour ago</span>
                        </div>
                      </div>
                       <div className="p-4 hover:bg-accent/30 transition-colors cursor-pointer flex gap-3">
                        <div className="mt-1">
                           <Zap className="w-4 h-4 text-yellow-500" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">High CPU Usage</p>
                          <p className="text-xs text-muted-foreground mt-1">System performance is optimized for gaming.</p>
                          <span className="text-[10px] text-muted-foreground mt-2 block">3 hours ago</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
             </div>
          </div>
        </header>
        <div className="flex-1 overflow-auto p-8">
            <div className="max-w-7xl mx-auto space-y-8">
              {children}
            </div>
        </div>
      </main>
    </div>
  );
};