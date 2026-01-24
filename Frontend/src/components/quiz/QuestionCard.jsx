import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, X, Lightbulb, Volume2 } from 'lucide-react';

/**
 * QuestionCard Component
 * Interactive question card with multiple choice options
 * Designed to be engaging and accessible for rural students
 */
export default function QuestionCard({
  question,
  questionNumber,
  totalQuestions,
  selectedAnswer,
  onSelectAnswer,
  showResult = false,
  isCorrect = null,
  disabled = false,
}) {
  const [hoveredOption, setHoveredOption] = useState(null);

  const getOptionStyle = (option, index) => {
    const isSelected = selectedAnswer === option;
    const isCorrectAnswer = question.correct_answer === option;
    
    if (showResult) {
      if (isCorrectAnswer) {
        return 'border-emerald-500 bg-emerald-500/20 text-emerald-300';
      }
      if (isSelected && !isCorrectAnswer) {
        return 'border-red-500 bg-red-500/20 text-red-300';
      }
      return 'border-white/10 bg-white/5 text-white/50';
    }
    
    if (isSelected) {
      return 'border-violet-500 bg-violet-500/20 text-violet-300 shadow-lg shadow-violet-500/20';
    }
    
    return 'border-white/10 bg-white/5 hover:border-violet-400/50 hover:bg-violet-500/10 text-white';
  };

  const optionLabels = ['A', 'B', 'C', 'D'];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="w-full max-w-2xl mx-auto"
    >
      {/* Question Header with Number Badge */}
      <div className="flex items-start gap-4 mb-6">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 500, delay: 0.1 }}
          className="flex-shrink-0 w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/30"
        >
          <span className="text-white font-bold text-lg">{questionNumber}</span>
        </motion.div>
        
        <div className="flex-1">
          <div className="text-xs text-white/50 mb-1 uppercase tracking-wider">
            Question {questionNumber} of {totalQuestions}
          </div>
          <h3 className="text-lg sm:text-xl font-medium text-white leading-relaxed">
            {question.question_text}
          </h3>
        </div>
      </div>

      {/* Hint Badge - For engagement */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.3 }}
        className="flex items-center gap-2 mb-4 px-3 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20 w-fit"
      >
        <Lightbulb className="w-4 h-4 text-amber-400" />
        <span className="text-xs text-amber-300">Select the best answer</span>
      </motion.div>

      {/* Options Grid */}
      <div className="space-y-3">
        {question.options.map((option, index) => (
          <motion.button
            key={`${question.question_id}-option-${index}`}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 * (index + 1) }}
            whileHover={!disabled ? { scale: 1.02, x: 4 } : {}}
            whileTap={!disabled ? { scale: 0.98 } : {}}
            onClick={() => !disabled && onSelectAnswer(option)}
            onMouseEnter={() => setHoveredOption(index)}
            onMouseLeave={() => setHoveredOption(null)}
            disabled={disabled}
            className={`
              w-full p-4 rounded-2xl border-2 text-left
              transition-all duration-200 ease-out
              flex items-center gap-4
              ${getOptionStyle(option, index)}
              ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            {/* Option Label */}
            <div className={`
              w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm
              transition-all duration-200
              ${selectedAnswer === option 
                ? 'bg-violet-500 text-white' 
                : showResult && question.correct_answer === option
                  ? 'bg-emerald-500 text-white'
                  : 'bg-white/10 text-white/70'
              }
            `}>
              {showResult && question.correct_answer === option ? (
                <Check className="w-5 h-5" />
              ) : showResult && selectedAnswer === option && question.correct_answer !== option ? (
                <X className="w-5 h-5" />
              ) : (
                optionLabels[index]
              )}
            </div>

            {/* Option Text */}
            <span className="flex-1 text-base">{option}</span>

            {/* Selection Indicator */}
            <AnimatePresence>
              {selectedAnswer === option && !showResult && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  exit={{ scale: 0 }}
                  className="w-6 h-6 rounded-full bg-violet-500 flex items-center justify-center"
                >
                  <Check className="w-4 h-4 text-white" />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.button>
        ))}
      </div>

      {/* Result Feedback */}
      <AnimatePresence>
        {showResult && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className={`
              mt-6 p-4 rounded-2xl border-2 flex items-center gap-3
              ${isCorrect 
                ? 'bg-emerald-500/10 border-emerald-500/30' 
                : 'bg-red-500/10 border-red-500/30'
              }
            `}
          >
            <div className={`
              w-10 h-10 rounded-xl flex items-center justify-center
              ${isCorrect ? 'bg-emerald-500' : 'bg-red-500'}
            `}>
              {isCorrect ? (
                <Check className="w-5 h-5 text-white" />
              ) : (
                <X className="w-5 h-5 text-white" />
              )}
            </div>
            <div>
              <p className={`font-semibold ${isCorrect ? 'text-emerald-400' : 'text-red-400'}`}>
                {isCorrect ? '🎉 Correct!' : '😔 Not quite right'}
              </p>
              {!isCorrect && (
                <p className="text-sm text-white/60 mt-1">
                  The correct answer is: <span className="text-emerald-400 font-medium">{question.correct_answer}</span>
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
