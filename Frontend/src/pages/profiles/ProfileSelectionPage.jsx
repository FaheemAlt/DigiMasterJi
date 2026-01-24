import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Settings, LogOut, Sparkles, Edit2, Trash2, Shield } from 'lucide-react';
import { profilesApi } from '../../api/profiles';
import { Button, Card, NetworkStatusBadge, LowBandwidthToggle } from '../../components/ui';
import { useAuth } from '../../hooks/useAuth';
import { useProfile } from '../../hooks/useProfile';

// Avatar options with gradients
const avatarOptions = [
  { id: 1, emoji: '🦊', gradient: 'from-orange-400 to-rose-500' },
  { id: 2, emoji: '🐼', gradient: 'from-slate-400 to-slate-600' },
  { id: 3, emoji: '🦁', gradient: 'from-amber-400 to-orange-500' },
  { id: 4, emoji: '🐯', gradient: 'from-amber-500 to-orange-600' },
  { id: 5, emoji: '🐨', gradient: 'from-gray-400 to-gray-500' },
  { id: 6, emoji: '🐸', gradient: 'from-emerald-400 to-green-500' },
  { id: 7, emoji: '🦋', gradient: 'from-violet-400 to-purple-500' },
  { id: 8, emoji: '🦄', gradient: 'from-pink-400 to-rose-500' },
  { id: 9, emoji: '🐙', gradient: 'from-rose-400 to-pink-500' },
  { id: 10, emoji: '🦉', gradient: 'from-amber-600 to-yellow-700' },
  { id: 11, emoji: '🐬', gradient: 'from-cyan-400 to-blue-500' },
  { id: 12, emoji: '🦜', gradient: 'from-emerald-400 to-teal-500' },
];

// Handle both numeric id and string avatar from backend (e.g., "avatar_1.png" or just 1)
const getAvatarById = (avatarValue) => {
  if (typeof avatarValue === 'number') {
    return avatarOptions.find((a) => a.id === avatarValue) || avatarOptions[0];
  }
  if (typeof avatarValue === 'string') {
    // Extract number from string like "avatar_1.png"
    const match = avatarValue.match(/(\d+)/);
    if (match) {
      const id = parseInt(match[1], 10);
      return avatarOptions.find((a) => a.id === id) || avatarOptions[0];
    }
  }
  return avatarOptions[0];
};

export default function ProfileSelectionPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { profiles, loading, refreshProfiles, activateProfile } = useProfile();
  
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [isManaging, setIsManaging] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [isActivating, setIsActivating] = useState(false); // Prevent double-activation

  useEffect(() => {
    refreshProfiles();
  }, [refreshProfiles]);

  const handleSelectProfile = async (profile) => {
    if (isManaging) return;
    
    // Backend returns _id, handle both id and _id
    const profileId = profile._id || profile.id;
    
    // Prevent double-clicking or re-activation
    if (selectedProfile || isActivating) return;
    
    setSelectedProfile(profileId);
    setIsActivating(true);
    
    try {
      await activateProfile(profileId);
      
      // Navigate immediately - animation is handled by CSS transitions
      navigate('/chat');
    } catch (err) {
      console.error('Failed to access profile:', err);
      setSelectedProfile(null);
      setIsActivating(false);
    }
  };

  const handleDeleteProfile = async (profile) => {
    const profileId = profile._id || profile.id;
    setDeletingId(profileId);
    try {
      await profilesApi.deleteProfile(profileId);
      await refreshProfiles();
    } catch (err) {
      console.error('Failed to delete profile:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleLogout = () => {
    logout();
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-violet-950 to-slate-950 relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{
            x: [0, 100, 0],
            y: [0, -50, 0],
          }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          className="absolute -top-40 -left-40 w-[500px] h-[500px] bg-violet-600/20 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            x: [0, -50, 0],
            y: [0, 100, 0],
          }}
          transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
          className="absolute -bottom-40 -right-40 w-[500px] h-[500px] bg-indigo-600/20 rounded-full blur-3xl"
        />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px]" />
      </div>

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between p-6">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-3"
        >
          <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-violet-500/30">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-white">
            DigiMaster<span className="text-violet-400">Ji</span>
          </span>
          {/* Network Status Badge */}
          <NetworkStatusBadge variant="pill" size="sm" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-3"
        >
          {/* Low Bandwidth Toggle - For rural users with poor connectivity */}
          <LowBandwidthToggle size="md" showTooltip={true} />
          
          <Button
            variant="secondary"
            size="sm"
            icon={Shield}
            onClick={() => navigate('/admin')}
          >
            Admin
          </Button>
          <Button
            variant="secondary"
            size="sm"
            icon={isManaging ? Edit2 : Settings}
            onClick={() => setIsManaging(!isManaging)}
          >
            {isManaging ? 'Done' : 'Manage'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon={LogOut}
            onClick={handleLogout}
          >
            Logout
          </Button>
        </motion.div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-120px)] px-6">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl font-bold text-white mb-3">Who's Learning Today?</h1>
          <p className="text-lg text-white/60">Select a profile to continue</p>
        </motion.div>

        {loading ? (
          <div className="flex items-center justify-center">
            <div className="w-12 h-12 border-4 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
          </div>
        ) : (
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6 max-w-5xl"
          >
            {/* Existing Profiles */}
            <AnimatePresence>
              {profiles.map((profile) => {
                const profileId = profile._id || profile.id;
                const avatar = getAvatarById(profile.avatar);
                return (
                  <motion.div
                    key={profileId}
                    variants={itemVariants}
                    exit={{ opacity: 0, scale: 0.8 }}
                    layout
                    className="relative group"
                  >
                    <motion.button
                      onClick={() => handleSelectProfile(profile)}
                      whileHover={!isManaging ? { scale: 1.05 } : {}}
                      whileTap={!isManaging ? { scale: 0.95 } : {}}
                      className={`
                        relative flex flex-col items-center p-6 rounded-2xl
                        bg-white/5 backdrop-blur-sm border border-white/10
                        transition-all duration-300
                        ${!isManaging ? 'hover:bg-white/10 hover:border-violet-500/30 cursor-pointer' : ''}
                        ${selectedProfile === profileId ? 'ring-4 ring-violet-500 border-transparent' : ''}
                      `}
                    >
                      {/* Avatar */}
                      <div className={`
                        relative w-24 h-24 rounded-full mb-4
                        bg-gradient-to-br ${avatar.gradient}
                        flex items-center justify-center
                        shadow-lg
                      `}>
                        <span className="text-4xl">{avatar.emoji}</span>
                        
                        {/* Selection indicator */}
                        {selectedProfile === profileId && (
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="absolute inset-0 rounded-full border-4 border-white"
                          />
                        )}
                      </div>

                      {/* Name */}
                      <span className="text-lg font-semibold text-white mb-1">
                        {profile.name}
                      </span>

                      {/* Grade/Level - backend uses grade_level */}
                      <span className="text-sm text-white/50">
                        {profile.grade_level || `Grade ${profile.grade}`}
                      </span>

                      {/* XP Badge - backend uses gamification.xp */}
                      {(profile.gamification?.xp > 0 || profile.xp > 0) && (
                        <div className="mt-2 px-2 py-1 bg-violet-500/20 rounded-full">
                          <span className="text-xs text-violet-300 font-medium">
                            {profile.gamification?.xp || profile.xp} XP
                          </span>
                        </div>
                      )}
                    </motion.button>

                    {/* Management Actions */}
                    {isManaging && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="absolute -top-2 -right-2 flex gap-1"
                      >
                        <button
                          onClick={() => navigate(`/profiles/${profileId}/edit`)}
                          className="w-8 h-8 bg-violet-500 rounded-full flex items-center justify-center shadow-lg hover:bg-violet-600 transition-colors"
                        >
                          <Edit2 className="w-4 h-4 text-white" />
                        </button>
                        <button
                          onClick={() => handleDeleteProfile(profile)}
                          disabled={deletingId === profileId}
                          className="w-8 h-8 bg-rose-500 rounded-full flex items-center justify-center shadow-lg hover:bg-rose-600 transition-colors disabled:opacity-50"
                        >
                          {deletingId === profileId ? (
                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          ) : (
                            <Trash2 className="w-4 h-4 text-white" />
                          )}
                        </button>
                      </motion.div>
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>

            {/* Add Profile Button */}
            <motion.button
              variants={itemVariants}
              onClick={() => navigate('/profiles/create')}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="
                flex flex-col items-center justify-center p-6 rounded-2xl
                bg-white/5 backdrop-blur-sm border-2 border-dashed border-white/20
                hover:bg-white/10 hover:border-violet-500/50
                transition-all duration-300 cursor-pointer
                min-h-[200px]
              "
            >
              <div className="w-24 h-24 rounded-full bg-white/10 flex items-center justify-center mb-4">
                <Plus className="w-10 h-10 text-white/50" />
              </div>
              <span className="text-lg font-semibold text-white/50">Add Profile</span>
            </motion.button>
          </motion.div>
        )}
      </main>
    </div>
  );
}
