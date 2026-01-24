import { motion, AnimatePresence } from 'framer-motion';
import { 
  WifiOff, 
  RefreshCw, 
  Check, 
  Cloud,
  CloudOff,
  Loader2,
} from 'lucide-react';
import { useNetworkStatus } from '../../contexts/NetworkStatusContext';

/**
 * NetworkStatusBadge Component
 * Displays offline/syncing status badges
 * 
 * Sprint 4 FE-A: UI badges for "Offline Mode" and "Syncing..."
 * 
 * @param {Object} props
 * @param {'badge' | 'pill' | 'minimal' | 'floating'} props.variant - Display style
 * @param {'sm' | 'md' | 'lg'} props.size - Badge size
 * @param {boolean} props.showWhenOnline - Show "Online" state (default: false)
 * @param {boolean} props.animate - Enable animations (default: true)
 * @param {string} props.className - Additional CSS classes
 */
export default function NetworkStatusBadge({
  variant = 'pill',
  size = 'md',
  showWhenOnline = false,
  animate = true,
  className = '',
}) {
  const { 
    isOnline, 
    isSyncing, 
    syncProgress,
    pendingChanges,
  } = useNetworkStatus();

  // Size configurations
  const sizes = {
    sm: {
      padding: 'px-2 py-0.5',
      text: 'text-xs',
      icon: 'w-3 h-3',
      gap: 'gap-1',
    },
    md: {
      padding: 'px-3 py-1',
      text: 'text-sm',
      icon: 'w-4 h-4',
      gap: 'gap-1.5',
    },
    lg: {
      padding: 'px-4 py-1.5',
      text: 'text-base',
      icon: 'w-5 h-5',
      gap: 'gap-2',
    },
  };

  const sizeConfig = sizes[size] || sizes.md;

  // Determine current state
  const getState = () => {
    if (!isOnline) return 'offline';
    if (isSyncing) return 'syncing';
    if (pendingChanges > 0) return 'pending';
    return 'online';
  };

  const state = getState();

  // State configurations
  const states = {
    offline: {
      icon: WifiOff,
      label: 'Offline',
      bgColor: 'bg-amber-500/20',
      borderColor: 'border-amber-500/30',
      textColor: 'text-amber-400',
      iconColor: 'text-amber-400',
      pulseColor: 'bg-amber-400',
    },
    syncing: {
      icon: RefreshCw,
      label: syncProgress 
        ? `Syncing ${syncProgress.current}/${syncProgress.total}...`
        : 'Syncing...',
      bgColor: 'bg-cyan-500/20',
      borderColor: 'border-cyan-500/30',
      textColor: 'text-cyan-400',
      iconColor: 'text-cyan-400',
      pulseColor: 'bg-cyan-400',
      spinning: true,
    },
    pending: {
      icon: Cloud,
      label: `${pendingChanges} pending`,
      bgColor: 'bg-violet-500/20',
      borderColor: 'border-violet-500/30',
      textColor: 'text-violet-400',
      iconColor: 'text-violet-400',
      pulseColor: 'bg-violet-400',
    },
    online: {
      icon: Check,
      label: 'Online',
      bgColor: 'bg-emerald-500/20',
      borderColor: 'border-emerald-500/30',
      textColor: 'text-emerald-400',
      iconColor: 'text-emerald-400',
      pulseColor: 'bg-emerald-400',
    },
  };

  const currentState = states[state];
  const Icon = currentState.icon;

  // Don't show if online and showWhenOnline is false
  if (state === 'online' && !showWhenOnline) {
    return null;
  }

  // Render based on variant
  const renderBadge = () => {
    switch (variant) {
      case 'minimal':
        return (
          <div className={`flex items-center ${sizeConfig.gap} ${className}`}>
            <div className="relative">
              <Icon 
                className={`${sizeConfig.icon} ${currentState.iconColor} ${currentState.spinning ? 'animate-spin' : ''}`} 
              />
              {(state === 'offline' || state === 'pending') && animate && (
                <span className={`absolute -top-0.5 -right-0.5 w-2 h-2 ${currentState.pulseColor} rounded-full animate-pulse`} />
              )}
            </div>
          </div>
        );

      case 'badge':
        return (
          <div 
            className={`
              inline-flex items-center ${sizeConfig.gap} ${sizeConfig.padding}
              ${currentState.bgColor} ${currentState.textColor}
              rounded-md font-medium ${sizeConfig.text}
              ${className}
            `}
          >
            <Icon 
              className={`${sizeConfig.icon} ${currentState.spinning ? 'animate-spin' : ''}`} 
            />
            <span>{currentState.label}</span>
          </div>
        );

      case 'floating':
        return (
          <div 
            className={`
              fixed bottom-4 left-4 z-50
              flex items-center ${sizeConfig.gap} ${sizeConfig.padding}
              ${currentState.bgColor} ${currentState.textColor}
              border ${currentState.borderColor}
              rounded-full backdrop-blur-xl shadow-lg
              font-medium ${sizeConfig.text}
              ${className}
            `}
          >
            {animate && (state === 'offline' || state === 'syncing') && (
              <span className={`absolute -top-1 -right-1 w-3 h-3 ${currentState.pulseColor} rounded-full animate-ping opacity-75`} />
            )}
            <Icon 
              className={`${sizeConfig.icon} ${currentState.spinning ? 'animate-spin' : ''}`} 
            />
            <span>{currentState.label}</span>
          </div>
        );

      case 'pill':
      default:
        return (
          <div 
            className={`
              inline-flex items-center ${sizeConfig.gap} ${sizeConfig.padding}
              ${currentState.bgColor} ${currentState.textColor}
              border ${currentState.borderColor}
              rounded-full font-medium ${sizeConfig.text}
              ${className}
            `}
          >
            {animate && (state === 'offline' || state === 'syncing') && (
              <span className={`relative flex h-2 w-2 mr-1`}>
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${currentState.pulseColor} opacity-75`} />
                <span className={`relative inline-flex rounded-full h-2 w-2 ${currentState.pulseColor}`} />
              </span>
            )}
            <Icon 
              className={`${sizeConfig.icon} ${currentState.spinning ? 'animate-spin' : ''}`} 
            />
            <span className="whitespace-nowrap">{currentState.label}</span>
          </div>
        );
    }
  };

  // Wrap with AnimatePresence for smooth transitions
  if (animate) {
    return (
      <AnimatePresence mode="wait">
        <motion.div
          key={state}
          initial={{ opacity: 0, scale: 0.9, y: -10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 10 }}
          transition={{ duration: 0.2 }}
        >
          {renderBadge()}
        </motion.div>
      </AnimatePresence>
    );
  }

  return renderBadge();
}

/**
 * NetworkStatusIndicator - Compact dot indicator
 * Shows a simple colored dot for network status
 */
export function NetworkStatusIndicator({ className = '' }) {
  const { isOnline, isSyncing } = useNetworkStatus();

  const getColor = () => {
    if (!isOnline) return 'bg-amber-400';
    if (isSyncing) return 'bg-cyan-400';
    return 'bg-emerald-400';
  };

  return (
    <span className={`relative flex h-2.5 w-2.5 ${className}`}>
      {(!isOnline || isSyncing) && (
        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${getColor()} opacity-75`} />
      )}
      <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${getColor()}`} />
    </span>
  );
}

/**
 * OfflineBanner - Full-width banner for offline mode
 * Shows at the top of the page when offline
 */
export function OfflineBanner({ className = '' }) {
  const { isOnline, isSyncing, pendingChanges } = useNetworkStatus();

  if (isOnline && !isSyncing) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        className={`
          w-full overflow-hidden
          ${!isOnline 
            ? 'bg-amber-500/10 border-b border-amber-500/20' 
            : 'bg-cyan-500/10 border-b border-cyan-500/20'
          }
          ${className}
        `}
      >
        <div className="flex items-center justify-center gap-2 py-2 px-4">
          {!isOnline ? (
            <>
              <WifiOff className="w-4 h-4 text-amber-400" />
              <span className="text-sm text-amber-400 font-medium">
                You're offline. Changes will sync when you're back online.
              </span>
              {pendingChanges > 0 && (
                <span className="px-2 py-0.5 bg-amber-500/20 rounded-full text-xs text-amber-400">
                  {pendingChanges} pending
                </span>
              )}
            </>
          ) : (
            <>
              <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
              <span className="text-sm text-cyan-400 font-medium">
                Syncing your data...
              </span>
            </>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
