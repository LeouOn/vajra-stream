/**
 * Sidebar Section — collapsible navigation section wrapper.
 * Accordion-style with title, icon, collapse toggle, and children.
 * @component
 */
import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

const sectionColors = {
  'Audio Control': { icon: 'text-cyan-400', border: 'border-cyan-500/20' },
  'Sessions': { icon: 'text-blue-400', border: 'border-blue-500/20' },
  'Rate Tuner': { icon: 'text-amber-400', border: 'border-amber-500/20' },
  'RNG Attunement': { icon: 'text-green-400', border: 'border-green-500/20' },
  'Crystal Work': { icon: 'text-pink-400', border: 'border-pink-500/20' },
  'Dharma Tales': { icon: 'text-purple-400', border: 'border-purple-500/20' },
  'Chakra Healing': { icon: 'text-red-400', border: 'border-red-500/20' },
  'Blessing Slideshow': { icon: 'text-yellow-400', border: 'border-yellow-500/20' },
  'Populations': { icon: 'text-teal-400', border: 'border-teal-500/20' },
  'Automation': { icon: 'text-orange-400', border: 'border-orange-500/20' },
};

const SidebarSection = ({ title, icon: Icon, children, defaultOpen = true, badge = null }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const colors = sectionColors[title] || { icon: 'text-vajra-cyan', border: 'border-purple-500/20' };

  return (
    <div className="mb-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center justify-between w-full px-3 py-2 text-left hover:bg-gray-700/50 rounded-lg transition-colors group ${isOpen ? colors.border + ' border-l-2' : ''}`}
      >
        <div className="flex items-center gap-2 min-w-0">
          <Icon className={`w-4 h-4 flex-shrink-0 ${colors.icon}`} />
          <span className="text-sm font-medium text-gray-200 truncate">{title}</span>
          {badge != null && (
            <span className="px-1.5 py-0.5 text-xs bg-purple-600 text-white rounded-full flex-shrink-0">
              {badge}
            </span>
          )}
        </div>
        {isOpen ? (
          <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
        )}
      </button>
      <div
        className={`grid transition-grid duration-300 ${
          isOpen ? 'grid-template-rows-[1fr] opacity-100 mt-1' : 'grid-template-rows-[0fr] opacity-0'
        }`}
      >
        <div className="overflow-hidden min-h-0">
          <div className="pl-1">{children}</div>
        </div>
      </div>
    </div>
  );
};

export { SidebarSection };
