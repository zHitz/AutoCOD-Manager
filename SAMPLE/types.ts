export interface Emulator {
  id: string;
  name: string;
  version: string;
  status: 'running' | 'stopped' | 'updating';
  icon: string;
  core: string;
  lastPlayed?: string;
}

export interface Game {
  id: string;
  title: string;
  platform: string;
  coverUrl: string;
  playTimeHrs: number;
  lastPlayed: string;
  emulatorId: string;
  favorite: boolean;
}

export interface SystemStats {
  cpuUsage: number;
  gpuUsage: number;
  ramUsage: number;
  fps: number;
  temperature: number;
}

export enum ViewState {
  DASHBOARD = 'DASHBOARD',
  LIBRARY = 'LIBRARY',
  EMULATORS = 'EMULATORS',
  ACTIONS = 'ACTIONS',
  SETTINGS = 'SETTINGS',
}