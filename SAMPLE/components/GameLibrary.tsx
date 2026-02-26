import React, { useState } from 'react';
import { Game } from '../types';
import { Card, Button, Input, Badge } from './ui/Primitives';
import { Play, Star, Clock, Filter, Search } from 'lucide-react';

interface GameLibraryProps {
  games: Game[];
  onLaunchGame: (gameId: string) => void;
}

export const GameLibrary: React.FC<GameLibraryProps> = ({ games, onLaunchGame }) => {
  const [filter, setFilter] = useState('All');
  const [search, setSearch] = useState('');

  const filteredGames = games.filter(g => {
    const matchesFilter = filter === 'All' || g.platform === filter;
    const matchesSearch = g.title.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const platforms = ['All', ...Array.from(new Set(games.map(g => g.platform)))];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="flex items-center gap-2 overflow-x-auto pb-2 md:pb-0 w-full md:w-auto">
          {platforms.map(p => (
            <Button 
              key={p} 
              variant={filter === p ? "default" : "outline"} 
              size="sm"
              onClick={() => setFilter(p)}
              className="whitespace-nowrap"
            >
              {p}
            </Button>
          ))}
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto">
           <div className="relative flex-1 md:w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input 
                placeholder="Find a game..." 
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
           </div>
           <Button variant="outline" size="icon">
             <Filter className="h-4 w-4" />
           </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
        {filteredGames.map((game) => (
          <div key={game.id} className="group relative bg-card rounded-lg overflow-hidden border border-border shadow-sm hover:shadow-lg hover:border-primary/50 transition-all duration-300">
            {/* Cover Image */}
            <div className="aspect-[3/4] relative overflow-hidden bg-slate-900">
               <img src={game.coverUrl} alt={game.title} className="object-cover w-full h-full transition-transform duration-500 group-hover:scale-110" />
               <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-3">
                  <Button onClick={() => onLaunchGame(game.id)} size="icon" className="rounded-full h-12 w-12 bg-white text-black hover:bg-white/90 hover:scale-105 transition-transform">
                     <Play className="fill-black w-5 h-5 ml-1" />
                  </Button>
                  <span className="text-xs font-semibold text-white tracking-widest uppercase">Play Now</span>
               </div>
               {game.favorite && (
                 <div className="absolute top-2 right-2 text-yellow-400">
                   <Star className="w-5 h-5 fill-yellow-400" />
                 </div>
               )}
            </div>
            
            {/* Info */}
            <div className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <Badge variant="outline" className="text-[10px] h-5 px-1.5">{game.platform}</Badge>
                <div className="flex items-center text-[10px] text-muted-foreground gap-1">
                   <Clock className="w-3 h-3" />
                   {game.playTimeHrs}h
                </div>
              </div>
              <h3 className="font-semibold text-sm truncate" title={game.title}>{game.title}</h3>
              <p className="text-xs text-muted-foreground truncate">Last played: {game.lastPlayed}</p>
            </div>
          </div>
        ))}
      </div>
      
      {filteredGames.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
          <div className="w-16 h-16 rounded-full bg-accent/50 flex items-center justify-center mb-4">
             <Search className="w-8 h-8" />
          </div>
          <p className="text-lg font-medium">No games found</p>
          <p className="text-sm">Try adjusting your filters or search terms.</p>
        </div>
      )}
    </div>
  );
};