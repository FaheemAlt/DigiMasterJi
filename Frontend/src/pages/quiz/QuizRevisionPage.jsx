import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Calendar,
  Star,
  RefreshCw,
  Search,
  Filter,
  Clock,
} from 'lucide-react';
import { Button, NetworkStatusBadge } from '../../components/ui';
import { useProfile } from '../../hooks/useProfile';
import { quizzesApi } from '../../api/quizzes';
import { syncService } from '../../services/syncService';
import { useNetworkStatus } from '../../contexts/NetworkStatusContext';

/**
 * QuizRevisionPage Component
 * Displays completed quizzes with questions for revision
 * Allows users to review their answers and learn from mistakes
 */
export default function QuizRevisionPage() {
  const navigate = useNavigate();
  const { activeProfile, isProfileSessionValid } = useProfile();
  const { isOnline } = useNetworkStatus();
  
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedQuiz, setExpandedQuiz] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCorrect, setFilterCorrect] = useState('all'); // 'all', 'correct', 'incorrect'

  // Redirect if no active profile
  useEffect(() => {
    if (!isProfileSessionValid()) {
      navigate('/profiles', { replace: true });
    }
  }, [isProfileSessionValid, navigate]);

  // Fetch quizzes on mount
  useEffect(() => {
    if (activeProfile) {
      fetchQuizzes();
    }
  }, [activeProfile]);

  const fetchQuizzes = async () => {
    try {
      setLoading(true);
      setError(null);

      let quizData = [];

      if (isOnline) {
        // Fetch from server
        try {
          const response = await quizzesApi.getQuizzesForRevision();
          // Backend returns array directly
          quizData = response.data || [];
        } catch (err) {
          console.error('Error fetching quizzes from server:', err);
          // Fall back to local data
          quizData = await syncService.getLocalQuizzesForRevision(
            activeProfile._id || activeProfile.id
          );
        }
      } else {
        // Offline - use local data
        quizData = await syncService.getLocalQuizzesForRevision(
          activeProfile._id || activeProfile.id
        );
      }

      setQuizzes(quizData);
    } catch (err) {
      console.error('Error fetching quizzes:', err);
      setError('Failed to load quizzes for revision. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchQuizzes();
    setRefreshing(false);
  };

  const toggleQuizExpansion = (quizId) => {
    setExpandedQuiz(expandedQuiz === quizId ? null : quizId);
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  // Filter quizzes based on search and filter
  const filteredQuizzes = quizzes.filter(quiz => {
    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const matchesTopic = quiz.topic?.toLowerCase().includes(term);
      const matchesQuestion = quiz.questions?.some(q => 
        q.question_text?.toLowerCase().includes(term)
      );
      if (!matchesTopic && !matchesQuestion) return false;
    }
    return true;
  });

  // Get questions with correct/incorrect filter
  const getFilteredQuestions = (questions) => {
    if (filterCorrect === 'all') return questions;
    if (filterCorrect === 'correct') {
      return questions.filter(q => q.user_answer === q.correct_answer || q.is_correct);
    }
    return questions.filter(q => (q.user_answer !== q.correct_answer) && !q.is_correct);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-violet-950 to-slate-900 overflow-y-auto">
      {/* Animated Background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(120,119,198,0.15),transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,rgba(251,146,60,0.1),transparent_50%)]" />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto px-4 py-6 pb-24">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-6"
        >
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/quiz')}
              className="p-2 rounded-xl hover:bg-white/10 transition-colors"
            >
              <ArrowLeft className="w-6 h-6 text-white/60" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-white">Quiz Revision</h1>
              <p className="text-sm text-white/50">Review your completed quizzes</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <NetworkStatusBadge variant="minimal" size="sm" />
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="p-2 rounded-xl hover:bg-white/10 transition-colors"
            >
              <RefreshCw className={`w-5 h-5 text-white/60 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </motion.div>

        {/* Search and Filters */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-6 space-y-3"
        >
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
            <input
              type="text"
              placeholder="Search quizzes or questions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-violet-500/50"
            />
          </div>

          {/* Filter Buttons */}
          
        </motion.div>

        {/* Loading State */}
        {loading ? (
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8">
            <div className="flex flex-col items-center justify-center">
              <div className="w-12 h-12 border-4 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mb-4" />
              <p className="text-white/50">Loading your quizzes...</p>
            </div>
          </div>
        ) : error ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 flex items-center gap-3"
          >
            <XCircle className="w-5 h-5 text-red-400" />
            <p className="text-red-300">{error}</p>
          </motion.div>
        ) : filteredQuizzes.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 text-center"
          >
            <motion.div
              animate={{ y: [0, -5, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-5xl mb-4"
            >
              📝
            </motion.div>
            <h3 className="text-lg font-semibold text-white mb-2">No Completed Quizzes Yet</h3>
            <p className="text-sm text-white/50 mb-4">
              Complete some quizzes to review them here!
            </p>
            <Button
              variant="primary"
              onClick={() => navigate('/quiz')}
              icon={BookOpen}
            >
              Take a Quiz
            </Button>
          </motion.div>
        ) : (
          <div className="space-y-4">
            {filteredQuizzes.map((quiz, index) => {
              const quizId = quiz._id || quiz.id;
              const isExpanded = expandedQuiz === quizId;
              const filteredQuestions = getFilteredQuestions(quiz.questions || []);
              // Use correct_count from API or calculate from is_correct/user_answer
              const correctCount = quiz.correct_count || (quiz.questions || []).filter(
                q => q.is_correct || q.user_answer === q.correct_answer
              ).length;
              const totalQuestions = quiz.total_questions || (quiz.questions || []).length;

              return (
                <motion.div
                  key={quizId}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05 * index }}
                  className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden"
                >
                  {/* Quiz Header */}
                  <div
                    onClick={() => toggleQuizExpansion(quizId)}
                    className="p-4 cursor-pointer hover:bg-white/5 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                          quiz.score >= 70 
                            ? 'bg-gradient-to-br from-emerald-500 to-teal-600' 
                            : quiz.score >= 40
                            ? 'bg-gradient-to-br from-amber-500 to-orange-600'
                            : 'bg-gradient-to-br from-red-500 to-rose-600'
                        }`}>
                          <Star className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-white flex items-center gap-2">
                            {quiz.topic}
                            {quiz.is_backlog && (
                              <span className="px-2 py-0.5 text-xs bg-amber-500/20 text-amber-400 rounded-full">
                                Backlog
                              </span>
                            )}
                          </h3>
                          <div className="flex items-center gap-3 text-sm text-white/50">
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {formatDate(quiz.completed_at || quiz.quiz_date)}
                            </span>
                            <span className="flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" />
                              {correctCount}/{totalQuestions} correct
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <div className={`text-lg font-bold ${
                            quiz.score >= 70 
                              ? 'text-emerald-400' 
                              : quiz.score >= 40
                              ? 'text-amber-400'
                              : 'text-red-400'
                          }`}>
                            {quiz.score}%
                          </div>
                          <div className="text-xs text-white/50">Score</div>
                        </div>
                        {isExpanded ? (
                          <ChevronUp className="w-5 h-5 text-white/40" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-white/40" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Questions (Expanded) */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="border-t border-white/10"
                      >
                        {filteredQuestions.length === 0 ? (
                          <div className="p-4 text-center text-white/50">
                            No {filterCorrect === 'correct' ? 'correct' : 'incorrect'} answers in this quiz
                          </div>
                        ) : (
                          <div className="divide-y divide-white/5">
                            {filteredQuestions.map((question, qIndex) => {
                              const isCorrect = question.is_correct || question.user_answer === question.correct_answer;
                              const userAnswer = question.user_answer;
                              return (
                                <div key={qIndex} className="p-4">
                                  <div className="flex items-start gap-3 mb-3">
                                    <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                                      isCorrect ? 'bg-emerald-500' : 'bg-red-500'
                                    }`}>
                                      {isCorrect ? (
                                        <CheckCircle2 className="w-4 h-4 text-white" />
                                      ) : (
                                        <XCircle className="w-4 h-4 text-white" />
                                      )}
                                    </div>
                                    <p className="text-white font-medium">{question.question_text}</p>
                                  </div>

                                  {/* Options */}
                                  <div className="ml-9 space-y-2">
                                    {question.options?.map((option, oIndex) => {
                                      const optionLetter = String.fromCharCode(65 + oIndex); // A, B, C, D
                                      const isSelected = userAnswer === optionLetter || userAnswer === option;
                                      const isCorrectOption = question.correct_answer === option;

                                      return (
                                        <div
                                          key={oIndex}
                                          className={`p-3 rounded-lg text-sm flex items-center justify-between ${
                                            isCorrectOption
                                              ? 'bg-emerald-500/30 border-2 border-emerald-400 text-emerald-200'
                                              : isSelected && !isCorrect
                                              ? 'bg-red-500/20 border border-red-500/30 text-red-300'
                                              : 'bg-white/5 border border-white/10 text-white/60'
                                          }`}
                                        >
                                          <div>
                                            <span className="font-medium mr-2">{optionLetter}.</span>
                                            {option}
                                          </div>
                                          <div className="flex items-center gap-2">
                                            {isCorrectOption && (
                                              <span className="flex items-center gap-1 px-2 py-1 bg-emerald-500/40 text-emerald-300 text-xs font-semibold rounded-full">
                                                <CheckCircle2 className="w-3 h-3" />
                                                Correct Answer
                                              </span>
                                            )}
                                            {isSelected && !isCorrect && (
                                              <span className="flex items-center gap-1 px-2 py-1 bg-red-500/40 text-red-300 text-xs font-semibold rounded-full">
                                                <XCircle className="w-3 h-3" />
                                                Your answer
                                              </span>
                                            )}
                                            {isSelected && isCorrect && (
                                              <span className="flex items-center gap-1 px-2 py-1 bg-emerald-500/40 text-emerald-300 text-xs font-semibold rounded-full">
                                                <CheckCircle2 className="w-3 h-3" />
                                                You got it!
                                              </span>
                                            )}
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>

                                  {/* Explanation if available */}
                                  {question.explanation && (
                                    <div className="ml-9 mt-3 p-3 bg-violet-500/10 border border-violet-500/20 rounded-lg">
                                      <p className="text-sm text-violet-300">
                                        <span className="font-medium">Explanation:</span> {question.explanation}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </div>
        )}

        {/* Stats Summary */}
        {!loading && filteredQuizzes.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-8 bg-gradient-to-r from-violet-500/10 to-indigo-500/10 backdrop-blur-xl border border-violet-500/20 rounded-2xl p-6"
          >
            <h3 className="text-lg font-semibold text-white mb-4 text-center">Review Summary</h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-violet-400">{filteredQuizzes.length}</div>
                <div className="text-xs text-white/50">Quizzes Completed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-emerald-400">
                  {filteredQuizzes.reduce((acc, q) => acc + (q.correct_count || (q.questions || []).filter(
                    question => question.is_correct || question.user_answer === question.correct_answer
                  ).length), 0)}
                </div>
                <div className="text-xs text-white/50">Correct Answers</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-amber-400">
                  {Math.round(
                    filteredQuizzes.reduce((acc, q) => acc + (q.score || 0), 0) / filteredQuizzes.length
                  )}%
                </div>
                <div className="text-xs text-white/50">Average Score</div>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
