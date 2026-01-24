import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Wifi, WifiOff } from 'lucide-react';

/**
 * LowBandwidthToggle Component
 * A toggle button for users in rural/low connectivity areas
 * 
 * Sprint 4 FE-A: UI component for Low Bandwidth Mode
 * Functionality to be implemented by FE-B (data saving, reduced media, etc.)
 * 
 * @param {Object} props
 * @param {'sm' | 'md' | 'lg'} props.size - Button size
 * @param {boolean} props.showLabel - Show text label
 * @param {boolean} props.showTooltip - Show tooltip on hover
 * @param {string} props.className - Additional CSS classes
 * @param {function} props.onChange - Callback when mode changes (for FE-B)
 */
export default function LowBandwidthToggle({
  size = 'md',
  showLabel = false,
  showTooltip = true,
  className = '',
  onChange,
}) {
  // Persist preference in localStorage
  const [isLowBandwidth, setIsLowBandwidth] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('lowBandwidthMode') === 'true';
    }
    return false;
  });

  const [showTooltipState, setShowTooltipState] = useState(false);

  // Save preference to localStorage and dispatch event for other components
  useEffect(() => {
    localStorage.setItem('lowBandwidthMode', isLowBandwidth.toString());
    // Dispatch custom event so useLowBandwidthMode hook gets notified
    window.dispatchEvent(new Event('lowBandwidthModeChange'));
    // Call onChange callback for FE-B integration
    onChange?.(isLowBandwidth);
  }, [isLowBandwidth, onChange]);

  const handleToggle = () => {
    setIsLowBandwidth((prev) => !prev);
  };

  // Size configurations
  const sizes = {
    sm: {
      button: 'w-8 h-8',
      icon: 'w-4 h-4',
      text: 'text-xs',
      tooltip: 'text-xs px-2 py-1',
    },
    md: {
      button: 'w-10 h-10',
      icon: 'w-5 h-5',
      text: 'text-sm',
      tooltip: 'text-sm px-3 py-1.5',
    },
    lg: {
      button: 'w-12 h-12',
      icon: 'w-6 h-6',
      text: 'text-base',
      tooltip: 'text-base px-4 py-2',
    },
  };

  const sizeConfig = sizes[size] || sizes.md;

  return (
    <div className={`relative inline-flex items-center gap-2 ${className}`}>
      {/* Toggle Button */}
      <motion.button
        onClick={handleToggle}
        onMouseEnter={() => setShowTooltipState(true)}
        onMouseLeave={() => setShowTooltipState(false)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className={`
          ${sizeConfig.button}
          rounded-xl flex items-center justify-center
          transition-all duration-300
          ${isLowBandwidth
            ? 'bg-amber-500/20 border border-amber-500/30 text-amber-400'
            : 'bg-white/10 border border-white/10 text-white/60 hover:text-white hover:bg-white/20'
          }
        `}
        aria-label={isLowBandwidth ? 'Disable low bandwidth mode' : 'Enable low bandwidth mode'}
        title={isLowBandwidth ? 'Low Bandwidth Mode: ON' : 'Low Bandwidth Mode: OFF'}
      >
        <div className="relative">
          {isLowBandwidth ? (
            // WiFi with slash (Low Bandwidth ON)
            <div className="relative">
              <Wifi className={`${sizeConfig.icon}`} />
              {/* Diagonal slash */}
              <motion.div
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                className="absolute inset-0 flex items-center justify-center"
              >
                <div 
                  className="w-[140%] h-0.5 bg-amber-400 rounded-full -rotate-45 origin-center"
                  style={{ marginLeft: '-20%' }}
                />
              </motion.div>
            </div>
          ) : (
            // Normal WiFi icon
            <Wifi className={`${sizeConfig.icon}`} />
          )}
        </div>
      </motion.button>

      {/* Label (optional) */}
      {showLabel && (
        <span className={`${sizeConfig.text} ${isLowBandwidth ? 'text-amber-400' : 'text-white/60'}`}>
          {isLowBandwidth ? 'Data Saver' : 'Normal'}
        </span>
      )}

      {/* Tooltip */}
      {showTooltip && showTooltipState && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 5 }}
          className={`
            absolute top-full left-1/2 -translate-x-1/2 mt-2
            ${sizeConfig.tooltip}
            bg-slate-900 border border-white/10 rounded-lg
            text-white whitespace-nowrap z-50
            shadow-lg
          `}
        >
          {isLowBandwidth ? (
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              Low Bandwidth Mode: ON
            </span>
          ) : (
            <span>Click to enable Data Saver</span>
          )}
          {/* Tooltip arrow */}
          <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-900 border-l border-t border-white/10 rotate-45" />
        </motion.div>
      )}
    </div>
  );
}

/**
 * Hook to access low bandwidth mode state
 * For FE-B to use when implementing functionality
 */
export function useLowBandwidthMode() {
  const [isLowBandwidth, setIsLowBandwidth] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('lowBandwidthMode') === 'true';
    }
    return false;
  });

  // Listen for storage changes (in case toggle is in another component)
  useEffect(() => {
    const handleStorageChange = () => {
      setIsLowBandwidth(localStorage.getItem('lowBandwidthMode') === 'true');
    };

    // Custom event for same-tab updates
    window.addEventListener('lowBandwidthModeChange', handleStorageChange);
    // Storage event for cross-tab updates
    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('lowBandwidthModeChange', handleStorageChange);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  const setLowBandwidthMode = (enabled) => {
    localStorage.setItem('lowBandwidthMode', enabled.toString());
    setIsLowBandwidth(enabled);
    // Dispatch custom event for same-tab listeners
    window.dispatchEvent(new Event('lowBandwidthModeChange'));
  };

  return {
    isLowBandwidth,
    setLowBandwidthMode,
    toggleLowBandwidth: () => setLowBandwidthMode(!isLowBandwidth),
  };
}
