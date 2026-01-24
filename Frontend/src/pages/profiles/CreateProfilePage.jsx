import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ArrowLeft, 
  ArrowRight, 
  Check, 
  User, 
  GraduationCap,
  Sparkles,
  Languages
} from 'lucide-react';
import { Button, Input, Card } from '../../components/ui';
import { useProfile } from '../../hooks/useProfile';

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
  { value: 'en', label: 'English', native: 'English' },
  { value: 'hi', label: 'Hindi', native: 'हिंदी' },
  { value: 'ta', label: 'Tamil', native: 'தமிழ்' },
  { value: 'te', label: 'Telugu', native: 'తెలుగు' },
  { value: 'kn', label: 'Kannada', native: 'ಕನ್ನಡ' },
  { value: 'ml', label: 'Malayalam', native: 'മലയാളം' },
  { value: 'mr', label: 'Marathi', native: 'मराठी' },
  { value: 'bn', label: 'Bengali', native: 'বাংলা' },
  { value: 'gu', label: 'Gujarati', native: 'ગુજરાતી' },
  { value: 'pa', label: 'Punjabi', native: 'ਪੰਜਾਬੀ' },
];

export default function CreateProfilePage() {
  const navigate = useNavigate();
  const { createProfile } = useProfile();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    age: '',
    grade: null,
    language: 'en',
    avatar: 1,
  });

  const updateForm = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError('');
  };

  const validateStep = () => {
    switch (step) {
      case 1:
        if (formData.name.trim().length < 2) {
          setError('Please enter a name with at least 2 characters');
          return false;
        }
        if (!formData.age || formData.age < 5 || formData.age > 20) {
          setError('Please enter a valid age between 5 and 20');
          return false;
        }
        return true;
      case 2:
        if (!formData.grade) {
          setError('Please select a grade');
          return false;
        }
        return true;
      case 3:
        return true;
      case 4:
        return true;
      default:
        return true;
    }
  };

  const handleNext = () => {
    if (!validateStep()) return;
    setStep((prev) => prev + 1);
  };

  const handleBack = () => {
    setStep((prev) => prev - 1);
    setError('');
  };

  // Convert numeric grade to backend format (e.g., 6 -> "6th")
  const formatGradeLevel = (grade) => {
    const num = parseInt(grade);
    if (num === 1) return '1st';
    if (num === 2) return '2nd';
    if (num === 3) return '3rd';
    return `${num}th`;
  };

  // Map frontend language codes to backend supported languages
  const mapLanguage = (langCode) => {
    const languageMap = {
      'en': 'English',
      'hi': 'Hindi',
      'ta': 'Tamil',
      'te': 'Telugu',
      'kn': 'Kannada',
      'ml': 'Malayalam',
      'mr': 'Marathi',
      'bn': 'Bengali',
      'gu': 'Gujarati',
      'pa': 'Punjabi',
    };
    return languageMap[langCode] || 'Hindi';
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError('');

    try {
      // Backend expects: name, age, grade_level (e.g., "6th"), preferred_language, avatar
      await createProfile({
        name: formData.name,
        age: parseInt(formData.age),
        grade_level: formatGradeLevel(formData.grade),
        preferred_language: mapLanguage(formData.language),
        avatar: formData.avatar ? `avatar_${formData.avatar}.png` : 'default_avatar.png',
      });
      navigate('/profiles');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const selectedAvatar = avatarOptions.find((a) => a.id === formData.avatar);

  const steps = [
    { number: 1, label: 'Basic Info', icon: User },
    { number: 2, label: 'Grade', icon: GraduationCap },
    { number: 3, label: 'Language', icon: Languages },
    { number: 4, label: 'Avatar', icon: Sparkles },
  ];

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
      <header className="relative z-10 flex items-center gap-4 p-6">
        <Button
          variant="ghost"
          size="sm"
          icon={ArrowLeft}
          onClick={() => navigate('/profiles')}
        >
          Back
        </Button>
        <div>
          <h1 className="text-xl font-bold text-white">Create New Profile</h1>
          <p className="text-sm text-white/50">Step {step} of 4</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 flex flex-col items-center justify-center px-6 pb-12">
        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-4 mb-10 flex-wrap">
          {steps.map((s, index) => {
            const Icon = s.icon;
            return (
              <div key={s.number} className="flex items-center">
                <motion.div
                  initial={false}
                  animate={{
                    scale: step >= s.number ? 1 : 0.9,
                    opacity: step >= s.number ? 1 : 0.5,
                  }}
                  className={`
                    flex items-center gap-2 px-4 py-2 rounded-full
                    ${step === s.number
                      ? 'bg-gradient-to-r from-violet-600 to-indigo-600 shadow-lg shadow-violet-500/30'
                      : step > s.number
                        ? 'bg-emerald-500/20'
                        : 'bg-white/5'
                    }
                  `}
                >
                  <div className={`
                    w-6 h-6 rounded-full flex items-center justify-center
                    ${step > s.number ? 'bg-emerald-500' : ''}
                  `}>
                    {step > s.number ? (
                      <Check className="w-4 h-4 text-white" />
                    ) : (
                      <Icon className={`w-4 h-4 ${step >= s.number ? 'text-white' : 'text-white/40'}`} />
                    )}
                  </div>
                  <span className={`text-sm font-medium hidden sm:block ${
                    step >= s.number ? 'text-white' : 'text-white/40'
                  }`}>
                    {s.label}
                  </span>
                </motion.div>
                {index < steps.length - 1 && (
                  <div className={`w-8 h-0.5 mx-2 rounded ${
                    step > s.number ? 'bg-emerald-500' : 'bg-white/10'
                  }`} />
                )}
              </div>
            );
          })}
        </div>

        {/* Form Card */}
        <Card className="w-full max-w-lg p-8">
          {/* Error Message */}
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
          </AnimatePresence>

          {/* Step Content */}
          <AnimatePresence mode="wait">
            {/* Step 1: Basic Info */}
            {step === 1 && (
              <motion.div
                key="step1"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div className="text-center mb-6">
                  <h2 className="text-2xl font-bold text-white mb-2">Let's Get Started!</h2>
                  <p className="text-white/60">What should we call this learner?</p>
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

            {/* Step 2: Grade Selection */}
            {step === 2 && (
              <motion.div
                key="step2"
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

            {/* Step 3: Language Selection */}
            {step === 3 && (
              <motion.div
                key="step3"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <div className="text-center mb-6">
                  <h2 className="text-2xl font-bold text-white mb-2">Preferred Language</h2>
                  <p className="text-white/60">Choose the language for AI explanations</p>
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

            {/* Step 4: Avatar Selection */}
            {step === 4 && (
              <motion.div
                key="step4"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <div className="text-center mb-6">
                  <h2 className="text-2xl font-bold text-white mb-2">Choose an Avatar</h2>
                  <p className="text-white/60">Pick a buddy for your learning journey!</p>
                </div>

                {/* Selected Avatar Preview */}
                <div className="flex justify-center mb-6">
                  <motion.div
                    key={formData.avatar}
                    initial={{ scale: 0.8, rotate: -10 }}
                    animate={{ scale: 1, rotate: 0 }}
                    className={`
                      w-28 h-28 rounded-full
                      bg-gradient-to-br ${selectedAvatar?.gradient}
                      flex items-center justify-center
                      shadow-2xl
                    `}
                  >
                    <span className="text-5xl">{selectedAvatar?.emoji}</span>
                  </motion.div>
                </div>

                <div className="grid grid-cols-4 sm:grid-cols-6 gap-3">
                  {avatarOptions.map((avatar) => (
                    <motion.button
                      key={avatar.id}
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => updateForm('avatar', avatar.id)}
                      className={`
                        relative w-14 h-14 rounded-full
                        bg-gradient-to-br ${avatar.gradient}
                        flex items-center justify-center
                        transition-all duration-200
                        ${formData.avatar === avatar.id
                          ? 'ring-4 ring-white shadow-lg'
                          : 'opacity-70 hover:opacity-100'
                        }
                      `}
                    >
                      <span className="text-2xl">{avatar.emoji}</span>
                    </motion.button>
                  ))}
                </div>

                {/* Summary */}
                <div className="mt-8 p-4 bg-white/5 rounded-xl">
                  <h3 className="text-sm font-semibold text-white/60 mb-3">Profile Summary</h3>
                  <div className="space-y-2 text-white">
                    <div className="flex justify-between">
                      <span className="text-white/60">Name:</span>
                      <span className="font-medium">{formData.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-white/60">Age:</span>
                      <span className="font-medium">{formData.age} years</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-white/60">Grade:</span>
                      <span className="font-medium">Grade {formData.grade}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-white/60">Language:</span>
                      <span className="font-medium">
                        {languageOptions.find((l) => l.value === formData.language)?.label}
                      </span>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Navigation Buttons */}
          <div className="flex gap-4 mt-8">
            {step > 1 && (
              <Button
                variant="secondary"
                onClick={handleBack}
                icon={ArrowLeft}
                className="flex-1"
              >
                Back
              </Button>
            )}
            {step < 4 ? (
              <Button
                onClick={handleNext}
                icon={ArrowRight}
                iconPosition="right"
                className="flex-1"
              >
                Continue
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                loading={loading}
                icon={Check}
                iconPosition="right"
                className="flex-1"
              >
                Create Profile
              </Button>
            )}
          </div>
        </Card>
      </main>
    </div>
  );
}
