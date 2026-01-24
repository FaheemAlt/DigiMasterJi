import { motion } from 'framer-motion';
import { Check, Circle, HelpCircle } from 'lucide-react';

/**
 * QuizProgress Component
 * Visual progress indicator for quiz completion
 * Shows answered, current, and remaining questions
 */
export default function QuizProgress({
  currentQuestion,
  totalQuestions,
  answeredQuestions = {},
  correctAnswers = {},
  showResults = false,
}) {
  const progressPercentage = ((currentQuestion) / totalQuestions) * 100;

  return (
    <div className="w-full max-w-2xl mx-auto mb-8">
      {/* Progress Bar */}
      <div className="relative">
        {/* Background Track */}
        <div className="h-3 bg-white/10 rounded-full overflow-hidden backdrop-blur-sm">
          {/* Animated Progress Fill */}
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progressPercentage}%` }}
            transition={{ type: 'spring', stiffness: 100, damping: 20 }}
            className="h-full bg-gradient-to-r from-violet-500 via-indigo-500 to-purple-500 rounded-full relative"
          >
            {/* Shimmer Effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
          </motion.div>
        </div>

        {/* Progress Text */}
        <div className="flex justify-between items-center mt-2">
          <span className="text-sm text-white/60">
            Progress: {currentQuestion}/{totalQuestions}
          </span>
          <span className="text-sm font-medium text-violet-400">
            {Math.round(progressPercentage)}% Complete
          </span>
        </div>
      </div>

      {/* Question Dots Indicator */}
      <div className="flex justify-center gap-2 mt-4 flex-wrap">
        {Array.from({ length: totalQuestions }, (_, index) => {
          const questionNum = index + 1;
          const isAnswered = answeredQuestions[questionNum] !== undefined;
          const isCurrent = questionNum === currentQuestion;
          const isCorrect = showResults && correctAnswers[questionNum];
          const isWrong = showResults && isAnswered && !correctAnswers[questionNum];

          return (
            <motion.div
              key={index}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: index * 0.05 }}
              className={`
                w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold
                transition-all duration-300 ease-out
                ${isCurrent 
                  ? 'bg-gradient-to-br from-violet-500 to-indigo-600 text-white shadow-lg shadow-violet-500/40 scale-110' 
                  : isCorrect 
                    ? 'bg-emerald-500/20 border-2 border-emerald-500 text-emerald-400'
                    : isWrong
                      ? 'bg-red-500/20 border-2 border-red-500 text-red-400'
                      : isAnswered 
                        ? 'bg-violet-500/20 border-2 border-violet-500 text-violet-400' 
                        : 'bg-white/5 border-2 border-white/20 text-white/40'
                }
              `}
            >
              {showResults ? (
                isCorrect ? (
                  <Check className="w-4 h-4" />
                ) : isWrong ? (
                  <span>✗</span>
                ) : (
                  questionNum
                )
              ) : isAnswered ? (
                <Check className="w-4 h-4" />
              ) : (
                questionNum
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Encouraging Message */}
      <motion.div
        key={currentQuestion}
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mt-4"
      >
        <p className="text-sm text-white/50">
          {currentQuestion === 1 && "Let's begin! 🚀"}
          {currentQuestion > 1 && currentQuestion < totalQuestions && "Keep going! You're doing great! 💪"}
          {currentQuestion === totalQuestions && "Last question! You've got this! 🌟"}
        </p>
      </motion.div>
    </div>
  );
}
