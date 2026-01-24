import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import {
  LandingPage,
  LoginPage,
  RegisterPage,
  ProfileSelectionPage,
  CreateProfilePage,
  EditProfilePage,
  ChatPage,
  QuizListPage,
  QuizTakePage,
  GamificationDashboard,
  AdminDashboardPage,
  UploadDocumentPage,
  DocumentsListPage,
  VectorSearchPage,
  AudioPlayerDemo,
} from './pages';
import { AdminLayout } from './components/layouts';

// Auth guard component
const PrivateRoute = ({ children }) => {
  const token = localStorage.getItem('access_token');
  return token ? children : <Navigate to="/login" replace />;
};

// Public route guard (redirect to profiles if logged in)
const PublicRoute = ({ children }) => {
  const token = localStorage.getItem('access_token');
  return !token ? children : <Navigate to="/profiles" replace />;
};

function App() {
  return (
    <Router>
      <Routes>
        {/* Landing Page (Public - No Auth Guard) */}
        <Route path="/" element={<LandingPage />} />

        {/* Public Routes */}
        <Route
          path="/login"
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <RegisterPage />
            </PublicRoute>
          }
        />

        {/* Protected Routes */}
        <Route
          path="/profiles"
          element={
            <PrivateRoute>
              <ProfileSelectionPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/profiles/create"
          element={
            <PrivateRoute>
              <CreateProfilePage />
            </PrivateRoute>
          }
        />
        <Route
          path="/profiles/:profileId/edit"
          element={
            <PrivateRoute>
              <EditProfilePage />
            </PrivateRoute>
          }
        />

        {/* Admin Routes */}
        <Route
          path="/admin"
          element={
            <PrivateRoute>
              <AdminLayout />
            </PrivateRoute>
          }
        >
          <Route index element={<AdminDashboardPage />} />
          <Route path="upload" element={<UploadDocumentPage />} />
          <Route path="documents" element={<DocumentsListPage />} />
          <Route path="search" element={<VectorSearchPage />} />
        </Route>

        {/* Chat Route */}
        <Route
          path="/chat"
          element={
            <PrivateRoute>
              <ChatPage />
            </PrivateRoute>
          }
        />

        {/* Quiz Routes */}
        <Route
          path="/quiz"
          element={
            <PrivateRoute>
              <QuizListPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/quiz/:quizId"
          element={
            <PrivateRoute>
              <QuizTakePage />
            </PrivateRoute>
          }
        />
        <Route
          path="/progress"
          element={
            <PrivateRoute>
              <GamificationDashboard />
            </PrivateRoute>
          }
        />

        {/* Demo Routes (for development) */}
        <Route path="/demo/audio-player" element={<AudioPlayerDemo />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
