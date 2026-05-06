/**
 * Vajra.Stream - Organized Sidebar with Collapsible Sections
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Volume2, Clock, Heart, Sparkles, Zap, Users, Settings, Play, Pause, Square } from 'lucide-react';

const SidebarSection = ({ title, icon: Icon, children, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="mb-4">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-3 py-2 text-left hover:bg-gray-700/50 rounded-lg transition-colors"
      >
        <div className="flex items-center space-x-2">
          <Icon className="w-4 h-4 text-vajra-cyan" />
          <span className="text-sm font-medium text-gray-200">{title}</span>
        </div>
        {isOpen ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400" />
        )}
      </button>
      {isOpen && <div className="mt-2 pl-2">{children}</div>}
    </div>
  );
};

export { SidebarSection };
