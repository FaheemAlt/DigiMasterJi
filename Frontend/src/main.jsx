import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './contexts/AuthContext'
import { ProfileProvider } from './contexts/ProfileContext'
import { NetworkStatusProvider } from './contexts/NetworkStatusContext'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <ProfileProvider>
        <NetworkStatusProvider>
          <App />
        </NetworkStatusProvider>
      </ProfileProvider>
    </AuthProvider>
  </StrictMode>,
)

// PWA Service Worker Registration - Only in production builds
// In development, use `npm run build && npm run preview` to test PWA offline functionality
if (import.meta.env.PROD) {
  import('virtual:pwa-register').then(({ registerSW }) => {
    const updateSW = registerSW({
      onNeedRefresh() {
        console.log('[PWA] New content available, refresh to update');
      },
      onOfflineReady() {
        console.log('[PWA] App ready for offline use');
      },
      onRegistered(registration) {
        console.log('[PWA] Service Worker registered:', registration);
      },
      onRegisterError(error) {
        console.error('[PWA] Service Worker registration failed:', error);
      }
    });
  });
} else {
  console.log('[Dev] PWA disabled in development. Run `npm run build && npm run preview` to test offline.');
}
