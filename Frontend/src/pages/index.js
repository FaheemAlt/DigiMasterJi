// Landing Page
export { default as LandingPage } from './LandingPage';

// Auth Pages
export { LoginPage, RegisterPage } from './auth';

// Profile Pages
export { ProfileSelectionPage, CreateProfilePage, EditProfilePage } from './profiles';

// Chat Pages
export { ChatPage } from './chat';

// Quiz & Gamification Pages
export { QuizListPage, QuizTakePage, GamificationDashboard } from './quiz';

// Admin Pages
export { 
  AdminDashboardPage, 
  UploadDocumentPage, 
  DocumentsListPage, 
  VectorSearchPage 
} from './admin';

// Demo Pages (for development/testing)
export { default as AudioPlayerDemo } from './demo/AudioPlayerDemo';
