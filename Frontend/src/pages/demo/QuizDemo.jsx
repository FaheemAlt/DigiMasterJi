import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { QuestionCard, QuizProgress, ConfettiEffect } from '../../components/quiz';
import { StreakWidget, XPProgressWidget } from '../../components/gamification';
import { Button } from '../../components/ui';

/**
 * QuizDemo Page
 * Preview of all quiz components and features
 * No authentication required - perfect for showcasing work!
 */
export default function QuizDemo() {
  const [currentView, setCurrentView] = useState('overview'); // overview, question, results, dashboard
  const [showConfetti, setShowConfetti] = useState(false);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

  // Mock data
  const mockProfile = {
    name: "Aarav",
    gamification: {
      xp: 850,
      current_streak_days: 5,
      last_activity_date: new Date().toISOString(),
      badges: ['first_quiz', 'streak_3', 'math_wizard', 'perfect_score', 'early_bird'],
    }
  };

  const mockQuestions = [
    {
      question_id: "q1",
      question_text: "What gas do plants release during photosynthesis?",
      options: ["Oxygen", "Carbon Dioxide", "Nitrogen", "Helium"],
      correct_answer: "Oxygen",
    },
    {
      question_id: "q2",
      question_text: "पौधे किस प्रक्रिया द्वारा भोजन बनाते हैं?",
      options: ["प्रकाश संश्लेषण", "श्वसन", "वाष्पोत्सर्जन", "परासरण"],
      correct_answer: "प्रकाश संश्लेषण",
    },
    {
      question_id: "q3",
      question_text: "What is the speed of light?",
      options: ["300,000 km/s", "150,000 km/s", "450,000 km/s", "600,000 km/s"],
      correct_answer: "300,000 km/s",
    },
  ];

  const triggerConfetti = () => {
    setShowConfetti(true);
    setTimeout(() => setShowConfetti(false), 3000);
  };

  const views = {
    overview: (
      <div className="space-y-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Quiz System Demo</h1>
          <p className="text-white/60">All Sprint 5 FE-A Components</p>
        </div>

        {/* Gamification Widgets */}
        <div>
          <h2 className="text-xl font-semibold text-white mb-4">📊 Gamification Widgets</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <StreakWidget
              currentStreak={mockProfile.gamification.current_streak_days}
              lastActivityDate={mockProfile.gamification.last_activity_date}
              bestStreak={7}
              size="md"
              showDetails={true}
            />
            <XPProgressWidget
              xp={mockProfile.gamification.xp}
              size="md"
              showDetails={true}
            />
          </div>
        </div>

        {/* Quiz Stats Preview */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gradient-to-br from-orange-500/20 to-amber-500/10 backdrop-blur-xl border border-orange-500/20 rounded-2xl p-4 text-center">
            <div className="text-3xl mb-1">🔥</div>
            <div className="text-2xl font-bold text-orange-400">5</div>
            <div className="text-xs text-white/50">Day Streak</div>
          </div>
          <div className="bg-gradient-to-br from-violet-500/20 to-indigo-500/10 backdrop-blur-xl border border-violet-500/20 rounded-2xl p-4 text-center">
            <div className="text-3xl mb-1">⚡</div>
            <div className="text-2xl font-bold text-violet-400">850</div>
            <div className="text-xs text-white/50">Total XP</div>
          </div>
          <div className="bg-gradient-to-br from-emerald-500/20 to-teal-500/10 backdrop-blur-xl border border-emerald-500/20 rounded-2xl p-4 text-center">
            <div className="text-3xl mb-1">🏆</div>
            <div className="text-2xl font-bold text-emerald-400">Lvl 9</div>
            <div className="text-xs text-white/50">Current Level</div>
          </div>
        </div>

        {/* Navigation Buttons */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={() => setCurrentView('question')}
            className="p-6 rounded-2xl bg-gradient-to-br from-violet-500/20 to-indigo-500/10 border border-violet-500/30 hover:border-violet-400/50 transition-all"
          >
            <div className="text-4xl mb-2">📝</div>
            <h3 className="text-lg font-semibold text-white mb-1">Question Card</h3>
            <p className="text-sm text-white/50">Interactive quiz questions</p>
          </button>
          
          <button
            onClick={() => setCurrentView('results')}
            className="p-6 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 border border-emerald-500/30 hover:border-emerald-400/50 transition-all"
          >
            <div className="text-4xl mb-2">🎉</div>
            <h3 className="text-lg font-semibold text-white mb-1">Results & Confetti</h3>
            <p className="text-sm text-white/50">Celebration animations</p>
          </button>

          <button
            onClick={() => setCurrentView('dashboard')}
            className="p-6 rounded-2xl bg-gradient-to-br from-amber-500/20 to-orange-500/10 border border-amber-500/30 hover:border-amber-400/50 transition-all"
          >
            <div className="text-4xl mb-2">🏅</div>
            <h3 className="text-lg font-semibold text-white mb-1">Dashboard</h3>
            <p className="text-sm text-white/50">Badges & leaderboard</p>
          </button>
        </div>
      </div>
    ),

    question: (
      <div className="space-y-6">
        <button
          onClick={() => setCurrentView('overview')}
          className="flex items-center gap-2 text-white/60 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Overview
        </button>

        <div className="text-center mb-4">
          <h2 className="text-2xl font-bold text-white mb-2">Interactive Question Card</h2>
          <p className="text-white/50">Select an answer to see the interactive states</p>
        </div>

        <QuizProgress
          currentQuestion={currentQuestionIndex + 1}
          totalQuestions={mockQuestions.length}
          answeredQuestions={{
            1: true,
            2: selectedAnswer ? true : false,
          }}
        />

        <QuestionCard
          question={mockQuestions[currentQuestionIndex]}
          questionNumber={currentQuestionIndex + 1}
          totalQuestions={mockQuestions.length}
          selectedAnswer={selectedAnswer}
          onSelectAnswer={setSelectedAnswer}
        />

        <div className="flex justify-between">
          <Button
            variant="secondary"
            onClick={() => {
              if (currentQuestionIndex > 0) {
                setCurrentQuestionIndex(prev => prev - 1);
                setSelectedAnswer(null);
              }
            }}
            disabled={currentQuestionIndex === 0}
          >
            Previous
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              if (currentQuestionIndex < mockQuestions.length - 1) {
                setCurrentQuestionIndex(prev => prev + 1);
                setSelectedAnswer(null);
              }
            }}
            disabled={currentQuestionIndex === mockQuestions.length - 1}
          >
            Next
          </Button>
        </div>
      </div>
    ),

    results: (
      <div className="space-y-6">
        <button
          onClick={() => setCurrentView('overview')}
          className="flex items-center gap-2 text-white/60 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Overview
        </button>

        <ConfettiEffect isActive={showConfetti} intensity="high" />

        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-white mb-2">Quiz Results Celebration</h2>
          <p className="text-white/50">Click the button below to trigger confetti!</p>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 text-center"
        >
          <motion.div
            animate={{ rotate: [0, 10, -10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="text-7xl mb-6"
          >
            🏆
          </motion.div>

          <h1 className="text-3xl font-bold text-white mb-2">Excellent!</h1>
          <p className="text-white/60 mb-6">You completed the quiz!</p>

          {/* Score Circle */}
          <div className="relative w-40 h-40 mx-auto mb-8">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="80"
                cy="80"
                r="70"
                fill="none"
                stroke="rgba(255,255,255,0.1)"
                strokeWidth="12"
              />
              <motion.circle
                cx="80"
                cy="80"
                r="70"
                fill="none"
                stroke="#10B981"
                strokeWidth="12"
                strokeLinecap="round"
                strokeDasharray={440}
                initial={{ strokeDashoffset: 440 }}
                animate={{ strokeDashoffset: 440 - (440 * 90 / 100) }}
                transition={{ duration: 1, delay: 0.5 }}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-4xl font-bold text-emerald-400">90%</span>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="bg-white/5 rounded-2xl p-4">
              <div className="text-2xl mb-1">✓</div>
              <div className="text-xl font-bold text-emerald-400">9</div>
              <div className="text-xs text-white/50">Correct</div>
            </div>
            <div className="bg-white/5 rounded-2xl p-4">
              <div className="text-2xl mb-1">⚡</div>
              <div className="text-xl font-bold text-violet-400">+50</div>
              <div className="text-xs text-white/50">XP Earned</div>
            </div>
            <div className="bg-white/5 rounded-2xl p-4">
              <div className="text-2xl mb-1">⏱️</div>
              <div className="text-xl font-bold text-blue-400">3:45</div>
              <div className="text-xs text-white/50">Time</div>
            </div>
          </div>

          <Button
            variant="primary"
            size="lg"
            onClick={triggerConfetti}
          >
            🎉 Celebrate Again!
          </Button>
        </motion.div>
      </div>
    ),

    dashboard: (
      <div className="space-y-6">
        <button
          onClick={() => setCurrentView('overview')}
          className="flex items-center gap-2 text-white/60 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Overview
        </button>

        <div className="text-center mb-4">
          <h2 className="text-2xl font-bold text-white mb-2">Gamification Dashboard</h2>
          <p className="text-white/50">{mockProfile.name}'s achievements</p>
        </div>

        {/* Badges */}
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">🏅 Badges Earned (5)</h3>
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
            {[
              { emoji: '🎯', name: 'First Steps' },
              { emoji: '🔥', name: 'On Fire' },
              { emoji: '🧮', name: 'Math Wizard' },
              { emoji: '💯', name: 'Perfectionist' },
              { emoji: '🌅', name: 'Early Bird' },
            ].map((badge, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1 * i }}
                whileHover={{ scale: 1.05 }}
                className="p-4 rounded-2xl bg-white/5 border border-white/10 text-center hover:border-amber-500/30 transition-all"
              >
                <div className="text-3xl mb-2">{badge.emoji}</div>
                <div className="text-xs font-medium text-white truncate">{badge.name}</div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Leaderboard */}
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">👥 Family Leaderboard</h3>
          <div className="space-y-2">
            {[
              { name: 'Aarav', xp: 850, streak: 5, rank: 1, isYou: true },
              { name: 'Priya', xp: 720, streak: 3, rank: 2 },
              { name: 'Rohan', xp: 650, streak: 4, rank: 3 },
            ].map((entry, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 * i }}
                className={`
                  p-4 rounded-2xl flex items-center gap-4
                  ${entry.isYou 
                    ? 'bg-gradient-to-r from-violet-500/20 to-indigo-500/10 border-2 border-violet-500/30' 
                    : 'bg-white/5 border border-white/10'
                  }
                `}
              >
                <div className={`
                  w-10 h-10 rounded-xl flex items-center justify-center font-bold
                  ${i === 0 ? 'bg-amber-500/20 text-amber-400 text-xl' :
                    i === 1 ? 'bg-slate-400/20 text-slate-300' :
                    'bg-amber-600/20 text-amber-600'
                  }
                `}>
                  {i === 0 ? '👑' : entry.rank}
                </div>

                <div className="flex-1">
                  <div className="font-medium text-white flex items-center gap-2">
                    {entry.name}
                    {entry.isYou && (
                      <span className="text-xs px-2 py-0.5 bg-violet-500/20 text-violet-400 rounded-full">
                        You
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-white/50">Level {Math.floor(entry.xp / 100) + 1}</div>
                </div>

                <div className="text-right">
                  <div className="font-bold text-violet-400">{entry.xp} XP</div>
                  <div className="text-xs text-orange-400">🔥 {entry.streak}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    ),
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-violet-950 to-slate-900 overflow-y-auto">
      {/* Background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(120,119,198,0.15),transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,rgba(251,146,60,0.1),transparent_50%)]" />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto px-4 py-8">
        {views[currentView]}
      </div>
    </div>
  );
}
