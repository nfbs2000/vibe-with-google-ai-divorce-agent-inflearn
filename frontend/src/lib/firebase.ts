/**
 * Firebase Remote Config
 *
 * Firebase는 Remote Config로만 사용 (variant 값 관리)
 * GTM + GA4로 실제 이벤트 추적
 *
 * Setup:
 * 1. Firebase 프로젝트 생성
 * 2. Remote Config 설정
 * 3. .env에 credentials 추가
 */

import { initializeApp, FirebaseApp } from 'firebase/app';
import {
  getRemoteConfig,
  RemoteConfig,
  fetchAndActivate,
  getValue,
  Value
} from 'firebase/remote-config';

// Firebase configuration
// TODO: Replace with your Firebase project config
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || 'PLACEHOLDER',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'PLACEHOLDER',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'vibe-with-bigquery-demo',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || 'PLACEHOLDER',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || 'PLACEHOLDER',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || 'PLACEHOLDER',
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || 'PLACEHOLDER'
};

// Initialize Firebase
let app: FirebaseApp | null = null;
let remoteConfig: RemoteConfig | null = null;

export const initializeFirebase = (): FirebaseApp => {
  if (!app) {
    app = initializeApp(firebaseConfig);

    // Initialize Remote Config (variant 관리용)
    if (typeof window !== 'undefined') {
      remoteConfig = getRemoteConfig(app);

      // Remote Config settings
      remoteConfig.settings = {
        minimumFetchIntervalMillis: 3600000, // 1 hour
        fetchTimeoutMillis: 60000, // 1 minute
      };

      // Default variants
      remoteConfig.defaultConfig = {
        page_variant: 'control',
        feature_enabled: false,
      };
    }
  }

  return app;
};

// Get Remote Config instance
export const getRemoteConfigInstance = (): RemoteConfig | null => {
  if (!remoteConfig && typeof window !== 'undefined') {
    initializeFirebase();
  }
  return remoteConfig;
};

/**
 * Fetch and activate Remote Config values
 * This should be called when the app loads
 */
export const activateRemoteConfig = async (): Promise<boolean> => {
  const config = getRemoteConfigInstance();
  if (!config) return false;

  try {
    const activated = await fetchAndActivate(config);
    console.log('Remote Config activated:', activated);
    return activated;
  } catch (error) {
    console.error('Error activating Remote Config:', error);
    return false;
  }
};

/**
 * Get a Remote Config value
 */
export const getRemoteConfigValue = (key: string): Value | null => {
  const config = getRemoteConfigInstance();
  if (!config) return null;

  return getValue(config, key);
};

/**
 * Get variant value from Remote Config
 * Returns the variant string for the given parameter name
 */
export const getExperimentVariant = (experimentName: string): string => {
  const config = getRemoteConfigInstance();
  if (!config) return 'control';

  const value = getValue(config, experimentName);
  return value.asString() || 'control';
};


/**
 * Check if Firebase is properly configured
 */
export const isFirebaseConfigured = (): boolean => {
  return firebaseConfig.apiKey !== 'PLACEHOLDER';
};

export default {
  initializeFirebase,
  getRemoteConfigInstance,
  activateRemoteConfig,
  getRemoteConfigValue,
  getExperimentVariant,
  isFirebaseConfigured
};
