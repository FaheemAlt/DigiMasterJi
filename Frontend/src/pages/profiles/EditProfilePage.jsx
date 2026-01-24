import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ArrowLeft, 
  Save, 
  User, 
  GraduationCap,
  Sparkles,
  Languages,
  Loader2
} from 'lucide-react';
import { Button, Input, Card } from '../../components/ui';
import { profilesApi } from '../../api/profiles';

// Avatar options
const avatarOptions = [
  { id: 1, emoji: '🦊', gradient: 'from-orange-400 to-rose-500', name: 'Fox' },
  { id: 2, emoji: '🐼', gradient: 'from-slate-400 to-slate-600', name: 'Panda' },
  { id: 3, emoji: '🦁', gradient: 'from-amber-400 to-orange-500', name: 'Lion' },
  { id: 4, emoji: '🐯', gradient: 'from-amber-500 to-orange-600', name: 'Tiger' },
  { id: 5, emoji: '🐨', gradient: 'from-gray-400 to-gray-500', name: 'Koala' },
  { id: 6, emoji: '🐸', gradient: 'from-emerald-400 to-green-500', name: 'Frog' },
  { id: 7, emoji: '🦋', gradient: 'from-violet-400 to-purple-500', name: 'Butterfly' },
  { id: 8, emoji: '🦄', gradient: 'from-pink-400 to-rose-500', name: 'Unicorn' },
  { id: 9, emoji: '🐙', gradient: 'from-rose-400 to-pink-500', name: 'Octopus' },
  { id: 10, emoji: '🦉', gradient: 'from-amber-600 to-yellow-700', name: 'Owl' },
  { id: 11, emoji: '🐬', gradient: 'from-cyan-400 to-blue-500', name: 'Dolphin' },
  { id: 12, emoji: '🦜', gradient: 'from-emerald-400 to-teal-500', name: 'Parrot' },
];

// Grade options
const gradeOptions = [
  { value: 1, label: 'Grade 1', description: 'Age 6-7' },
  { value: 2, label: 'Grade 2', description: 'Age 7-8' },
  { value: 3, label: 'Grade 3', description: 'Age 8-9' },
  { value: 4, label: 'Grade 4', description: 'Age 9-10' },
  { value: 5, label: 'Grade 5', description: 'Age 10-11' },
  { value: 6, label: 'Grade 6', description: 'Age 11-12' },
  { value: 7, label: 'Grade 7', description: 'Age 12-13' },
  { value: 8, label: 'Grade 8', description: 'Age 13-14' },
  { value: 9, label: 'Grade 9', description: 'Age 14-15' },
  { value: 10, label: 'Grade 10', description: 'Age 15-16' },
  { value: 11, label: 'Grade 11', description: 'Age 16-17' },
  { value: 12, label: 'Grade 12', description: 'Age 17-18' },
];

// Language options
const languageOptions = [
  { value: 'en', label: 'English', native: 'English', backend: 'English' },
  { value: 'hi', label: 'Hindi', native: 'हिंदी', backend: 'Hindi' },
  { value: 'ta', label: 'Tamil', native: 'தமிழ்', backend: 'Tamil' },
  { value: 'te', label: 'Telugu', native: 'తెలుగు', backend: 'Telugu' },
  { value: 'kn', label: 'Kannada', native: 'ಕನ್ನಡ', backend: 'Kannada' },
  { value: 'ml', label: 'Malayalam', native: 'മലയാളം', backend: 'Malayalam' },
  { value: 'mr', label: 'Marathi', native: 'मराठी', backend: 'Marathi' },
  { value: 'bn', label: 'Bengali', native: 'বাংলা', backend: 'Bengali' },
  { value: 'gu', label: 'Gujarati', native: 'ગુજરાતી', backend: 'Gujarati' },
  { value: 'pa', label: 'Punjabi', native: 'ਪੰਜਾਬੀ', backend: 'Punjabi' },
];

// Parse avatar from backend format (e.g., "avatar_1.png" -> 1)
const parseAvatarId = (avatarValue) => {
  if (typeof avatarValue === 'number') return avatarValue;
  if (typeof avatarValue === 'string') {
    const match = avatarValue.match(/(\d+)/);
    if (match) return parseInt(match[1], 10);
  }
  return 1;
};

// Parse grade from backend format (e.g., "6th" -> 6)
const parseGradeLevel = (gradeLevel) => {
  if (typeof gradeLevel === 'number') return gradeLevel;
  if (typeof gradeLevel === 'string') {
    const match = gradeLevel.match(/(\d+)/);
    if (match) return parseInt(match[1], 10);
  }
  return null;
};

// Map backend language to frontend code
const mapBackendLanguage = (backendLang) => {
  const found = languageOptions.find(l => 
    l.backend.toLowerCase() === backendLang?.toLowerCase() ||
    l.label.toLowerCase() === backendLang?.toLowerCase()
  );
  return found?.value || 'en';
};

// Convert numeric grade to backend format (e.g., 6 -> "6th")
const formatGradeLevel = (grade) => {
  const num = parseInt(grade);
  if (num === 1) return '1st';
  if (num === 2) return '2nd';
  if (num === 3) return '3rd';
  return `${num}th`;
};

// Map frontend language code to backend format
const mapLanguageToBackend = (langCode) => {
  const found = languageOptions.find(l => l.value === langCode);
  return found?.backend || 'Hindi';
};

export default function EditProfilePage() {
  const navigate = useNavigate();
  const { profileId } = useParams();
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState('basic');

  const [formData, setFormData] = useState({
    name: '',
    age: '',
    grade: null,
    language: 'en',
    avatar: 1,
  });

  // Fetch profile data on mount
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setLoading(true);
        const response = await profilesApi.getProfileById(profileId);
        const profile = response.data;
        
        setFormData({
          name: profile.name || '',
          age: profile.age || '',
          grade: parseGradeLevel(profile.grade_level),
          language: mapBackendLanguage(profile.preferred_language),
          avatar: parseAvatarId(profile.avatar),
        });
      } catch (err) {
        console.error('Failed to fetch profile:', err);
        setError('Failed to load profile. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    if (profileId) {
      fetchProfile();
    }
  }, [profileId]);

  const updateForm = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError('');
    setSuccess('');
  };

  const validateForm = () => {
    if (formData.name.trim().length < 2) {
      setError('Please enter a name with at least 2 characters');
      setActiveTab('basic');
      return false;
    }
    if (!formData.age || formData.age < 5 || formData.age > 20) {
      setError('Please enter a valid age between 5 and 20');
      setActiveTab('basic');
      return false;
    }
    if (!formData.grade) {
      setError('Please select a grade');
      setActiveTab('grade');
      return false;
    }
    return true;
  };

  const handleSave = async () => {
    if (!validateForm()) return;

    setSaving(true);
    setError('');
    setSuccess('');

    try {
      await profilesApi.updateProfile(profileId, {
        name: formData.name,
        age: parseInt(formData.age),
        grade_level: formatGradeLevel(formData.grade),
        preferred_language: mapLanguageToBackend(formData.language),
        avatar: `avatar_${formData.avatar}.png`,
      });
      
      setSuccess('Profile updated successfully!');
      setTimeout(() => {
        navigate('/profiles');
      }, 1000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update profile. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const selectedAvatar = avatarOptions.find((a) => a.id === formData.avatar);

  const tabs = [
    { id: 'basic', label: 'Basic Info', icon: User },
    { id: 'grade', label: 'Grade', icon: GraduationCap },
    { id: 'language', label: 'Language', icon: Languages },
    { id: 'avatar', label: 'Avatar', icon: Sparkles },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-violet-950 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-violet-500 animate-spin mx-auto mb-4" />
          <p className="text-white/60">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-violet-950 to-slate-950 relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{ x: [0, 100, 0], y: [0, -50, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          className="absolute -top-40 -left-40 w-[500px] h-[500px] bg-violet-600/20 rounded-full blur-3xl"
        />
        <motion.div
          animate={{ x: [0, -50, 0], y: [0, 100, 0] }}
          transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
          className="absolute -bottom-40 -right-40 w-[500px] h-[500px] bg-indigo-600/20 rounded-full blur-3xl"
        />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px]" />
      </div>

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between p-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            icon={ArrowLeft}
            onClick={() => navigate('/profiles')}
          >
            Back
          </Button>
          <div>
            <h1 className="text-xl font-bold text-white">Edit Profile</h1>
            <p className="text-sm text-white/50">{formData.name || 'Loading...'}</p>
          </div>
        </div>

        <Button
          variant="primary"
          icon={saving ? Loader2 : Save}
          onClick={handleSave}
          disabled={saving}
          className={saving ? 'animate-pulse' : ''}
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </Button>
      </header>

      {/* Main Content */}
      <main className="relative z-10 flex flex-col items-center px-6 pb-12">
        {/* Preview Avatar */}
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="mb-8"
        >
          <div className={`
            relative w-28 h-28 rounded-full mb-2
            bg-gradient-to-br ${selectedAvatar?.gradient || 'from-violet-400 to-purple-500'}
            flex items-center justify-center
            shadow-2xl shadow-violet-500/30
          `}>
            <span className="text-5xl">{selectedAvatar?.emoji || '🦄'}</span>
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="flex items-center justify-center gap-2 mb-8 flex-wrap">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <motion.button
                key={tab.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-full transition-all
                  ${activeTab === tab.id
                    ? 'bg-gradient-to-r from-violet-600 to-indigo-600 shadow-lg shadow-violet-500/30'
                    : 'bg-white/5 hover:bg-white/10'
                  }
                `}
              >
                <Icon className={`w-4 h-4 ${activeTab === tab.id ? 'text-white' : 'text-white/60'}`} />
                <span className={`text-sm font-medium ${activeTab === tab.id ? 'text-white' : 'text-white/60'}`}>
                  {tab.label}
                </span>
              </motion.button>
            );
          })}
        </div>

        {/* Form Card */}
        <Card className="w-full max-w-lg p-8">
          {/* Messages */}
          <AnimatePresence mode="wait">
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="mb-6 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl"
              >
                <p className="text-sm text-rose-400 text-center">{error}</p>
              </motion.div>
            )}
            {success && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="mb-6 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl"
              >
                <p className="text-sm text-emerald-400 text-center">{success}</p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Tab Content */}
          <AnimatePresence mode="wait">
            {/* Basic Info Tab */}
            {activeTab === 'basic' && (
              <motion.div
                key="basic"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div className="text-center mb-6">
                  <h2 className="text-2xl font-bold text-white mb-2">Basic Information</h2>
                  <p className="text-white/60">Update the learner's details</p>
                </div>

                <Input
                  label="Profile Name"
                  placeholder="Enter name (e.g., Aarav, Priya)"
                  value={formData.name}
                  onChange={(e) => updateForm('name', e.target.value)}
                  icon={User}
                />

                <Input
                  label="Age"
                  type="number"
                  placeholder="Enter age"
                  value={formData.age}
                  onChange={(e) => updateForm('age', e.target.value)}
                  min={5}
                  max={20}
                />
              </motion.div>
            )}

            {/* Grade Tab */}
            {activeTab === 'grade' && (
              <motion.div
                key="grade"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <div className="text-center mb-6">
                  <h2 className="text-2xl font-bold text-white mb-2">Select Grade</h2>
                  <p className="text-white/60">This helps us personalize the learning experience</p>
                </div>

                <div className="grid grid-cols-3 sm:grid-cols-4 gap-3 max-h-[400px] overflow-y-auto pr-2">
                  {gradeOptions.map((grade) => (
                    <motion.button
                      key={grade.value}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => updateForm('grade', grade.value)}
                      className={`
                        p-4 rounded-xl text-center transition-all duration-200
                        ${formData.grade === grade.value
                          ? 'bg-gradient-to-br from-violet-600 to-indigo-600 shadow-lg shadow-violet-500/30'
                          : 'bg-white/5 border border-white/10 hover:bg-white/10'
                        }
                      `}
                    >
                      <span className="block text-lg font-bold text-white">{grade.value}</span>
                      <span className="text-xs text-white/60">{grade.description}</span>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Language Tab */}
            {activeTab === 'language' && (
              <motion.div
                key="language"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <div className="text-center mb-6">
                  <h2 className="text-2xl font-bold text-white mb-2">Preferred Language</h2>
                  <p className="text-white/60">Choose the language for lessons</p>
                </div>

                <div className="grid grid-cols-2 gap-3 max-h-[400px] overflow-y-auto pr-2">
                  {languageOptions.map((lang) => (
                    <motion.button
                      key={lang.value}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => updateForm('language', lang.value)}
                      className={`
                        p-4 rounded-xl text-left transition-all duration-200
                        ${formData.language === lang.value
                          ? 'bg-gradient-to-br from-violet-600 to-indigo-600 shadow-lg shadow-violet-500/30'
                          : 'bg-white/5 border border-white/10 hover:bg-white/10'
                        }
                      `}
                    >
                      <span className="block text-lg font-bold text-white">{lang.native}</span>
                      <span className="text-sm text-white/60">{lang.label}</span>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Avatar Tab */}
            {activeTab === 'avatar' && (
              <motion.div
                key="avatar"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <div className="text-center mb-6">
                  <h2 className="text-2xl font-bold text-white mb-2">Choose Avatar</h2>
                  <p className="text-white/60">Pick a fun character!</p>
                </div>

                <div className="grid grid-cols-3 sm:grid-cols-4 gap-4 max-h-[400px] overflow-y-auto pr-2">
                  {avatarOptions.map((avatar) => (
                    <motion.button
                      key={avatar.id}
                      whileHover={{ scale: 1.1, rotate: [0, -5, 5, 0] }}
                      whileTap={{ scale: 0.9 }}
                      onClick={() => updateForm('avatar', avatar.id)}
                      className={`
                        relative p-3 rounded-xl flex flex-col items-center gap-2
                        transition-all duration-200
                        ${formData.avatar === avatar.id
                          ? 'bg-white/10 ring-2 ring-violet-500'
                          : 'bg-white/5 hover:bg-white/10'
                        }
                      `}
                    >
                      <div className={`
                        w-16 h-16 rounded-full
                        bg-gradient-to-br ${avatar.gradient}
                        flex items-center justify-center
                        shadow-lg
                      `}>
                        <span className="text-3xl">{avatar.emoji}</span>
                      </div>
                      <span className="text-xs text-white/60">{avatar.name}</span>
                      
                      {formData.avatar === avatar.id && (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          className="absolute -top-1 -right-1 w-5 h-5 bg-violet-500 rounded-full flex items-center justify-center"
                        >
                          <span className="text-white text-xs">✓</span>
                        </motion.div>
                      )}
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Card>
      </main>
    </div>
  );
}
