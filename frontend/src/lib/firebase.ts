import { type FirebaseError, initializeApp } from 'firebase/app'
import { getAnalytics, isSupported } from 'firebase/analytics'
import {
  type User,
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  sendPasswordResetEmail,
  sendEmailVerification,
} from 'firebase/auth'
import {
  collection,
  doc,
  getDocs,
  getFirestore,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
} from 'firebase/firestore'
import type { Agent } from '../types/agent'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
}

const hasConfig = Object.values(firebaseConfig).every(Boolean)

export const firebaseApp = hasConfig ? initializeApp(firebaseConfig) : null
export const firebaseAuth = firebaseApp ? getAuth(firebaseApp) : null

export async function initFirebaseAnalytics() {
  if (!firebaseApp || typeof window === 'undefined') {
    return
  }

  if (await isSupported()) {
    getAnalytics(firebaseApp)
  }
}

export function subscribeToFirebaseAuth(
  callback: (user: User | null) => void,
): () => void {
  if (!firebaseAuth) {
    callback(null)
    return () => {}
  }

  return onAuthStateChanged(firebaseAuth, callback)
}

export async function registerWithEmailPassword(
  email: string,
  password: string,
): Promise<User> {
  if (!firebaseAuth) {
    throw new Error('Firebase Auth is not configured.')
  }

  const credential = await createUserWithEmailAndPassword(
    firebaseAuth,
    email,
    password,
  )
  return credential.user
}

export async function loginWithEmailPassword(
  email: string,
  password: string,
): Promise<User> {
  if (!firebaseAuth) {
    throw new Error('Firebase Auth is not configured.')
  }

  const credential = await signInWithEmailAndPassword(firebaseAuth, email, password)
  return credential.user
}

export function getFirebaseAuthErrorMessage(error: unknown): string {
  if (!error || typeof error !== 'object') {
    return 'Authentication failed. Please try again.'
  }

  const firebaseError = error as FirebaseError
  const code = firebaseError.code ?? ''

  if (code === 'auth/configuration-not-found') {
    return 'Firebase Authentication is not enabled for this project. In Firebase Console: Authentication -> Get started -> Sign-in method -> enable Email/Password, then try again.'
  }

  if (code === 'auth/operation-not-allowed') {
    return 'Email/password sign-in is disabled. Enable Email/Password under Firebase Console -> Authentication -> Sign-in method.'
  }

  if (code === 'auth/invalid-credential' || code === 'auth/invalid-login-credentials') {
    return 'Invalid email or password.'
  }

  if (code === 'auth/user-not-found') {
    return 'No account found for this email. Create an account first.'
  }

  if (code === 'auth/wrong-password') {
    return 'Wrong password. Try again.'
  }

  if (code === 'auth/email-already-in-use') {
    return 'This email is already in use. Try logging in instead.'
  }

  if (code === 'auth/weak-password') {
    return 'Password is too weak. Use at least 6 characters.'
  }

  if (code === 'auth/invalid-api-key') {
    return 'Firebase API key is invalid. Check your .env Firebase values.'
  }

  if (code === 'auth/network-request-failed') {
    return 'Network error while contacting Firebase. Check your connection and try again.'
  }

  if (typeof firebaseError.message === 'string' && firebaseError.message) {
    return firebaseError.message
  }

  return 'Authentication failed. Please verify Firebase configuration.'
}

export function getFirebaseWriteErrorMessage(error: unknown): string {
  if (!error || typeof error !== 'object') {
    return 'Firebase write failed.'
  }

  const firebaseError = error as FirebaseError
  const code = firebaseError.code ?? ''

  if (code === 'permission-denied' || code === 'firestore/permission-denied') {
    return 'Firestore denied the write. Check Firestore rules for users/{uid}/agents and ensure the signed-in user matches the document path.'
  }

  if (code === 'unauthenticated' || code === 'firestore/unauthenticated') {
    return 'You are not authenticated with Firebase. Sign in again and retry token upload.'
  }

  if (code === 'not-found' || code === 'firestore/not-found') {
    return 'Firestore is not enabled in this Firebase project. Open Firebase Console and create Firestore database.'
  }

  if (code === 'unavailable' || code === 'firestore/unavailable') {
    return 'Firestore is temporarily unavailable. Try again in a moment.'
  }

  if (typeof firebaseError.message === 'string' && firebaseError.message) {
    return firebaseError.message
  }

  return 'Firebase write failed. Check Firestore setup and rules.'
}

export async function logoutFromFirebase(): Promise<void> {
  if (!firebaseAuth) {
    return
  }

  await signOut(firebaseAuth)
}

export async function saveAgentToFirebase(params: {
  userId: string
  userEmail: string
  agent: Agent
}): Promise<boolean> {
  if (!firebaseApp) {
    return false
  }

  const db = getFirestore(firebaseApp)
  const { userId, userEmail, agent } = params

  await setDoc(
    doc(db, 'users', userId, 'agents', agent.id),
    {
      id: agent.id,
      name: agent.name,
      role: agent.role,
      botId: agent.botId,
      botUsername: agent.botUsername,
      botToken: agent.botToken,
      deliveryStatus: agent.deliveryStatus,
      ownerEmail: userEmail,
      updatedAt: serverTimestamp(),
      createdAt: serverTimestamp(),
    },
    { merge: true },
  )

  return true
}

export async function loadAgentsFromFirebase(userId: string): Promise<Agent[]> {
  if (!firebaseApp || !userId) {
    return []
  }

  const db = getFirestore(firebaseApp)
  const snapshot = await getDocs(
    query(collection(db, 'users', userId, 'agents'), orderBy('createdAt', 'desc')),
  )

  return snapshot.docs
    .map((docItem) => docItem.data())
    .filter(
      (item): item is Agent =>
        typeof item?.id === 'string' &&
        typeof item?.name === 'string' &&
        typeof item?.role === 'string' &&
        typeof item?.botId === 'string' &&
        typeof item?.botUsername === 'string' &&
        typeof item?.botToken === 'string' &&
        (item?.deliveryStatus === 'sent' || item?.deliveryStatus === 'pending'),
    )
}

export async function sendPasswordReset(email: string): Promise<void> {
  if (!firebaseAuth) {
    throw new Error('Firebase Auth is not configured.')
  }

  try {
    await sendPasswordResetEmail(firebaseAuth, email)
  } catch (error) {
    const message = getFirebaseAuthErrorMessage(error)
    throw new Error(message)
  }
}

export async function sendVerificationEmail(user: User): Promise<void> {
  try {
    await sendEmailVerification(user)
  } catch (error) {
    const message = getFirebaseAuthErrorMessage(error)
    throw new Error(message)
  }
}
