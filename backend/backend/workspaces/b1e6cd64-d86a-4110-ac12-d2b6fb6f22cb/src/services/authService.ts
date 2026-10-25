import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import { userStore, User } from '../models/user';

const SALT_ROUNDS = 12;
const JWT_SECRET = process.env.JWT_SECRET || 'super-secret-jwt-key-change-in-prod';
const MAX_FAILED_ATTEMPTS = 5;
const LOCK_TIME_MS = 15 * 60 * 1000; // 15 minutes lock

export interface AuthResult {
  token?: string;
  message: string;
}

export class AuthService {
  async register(email: string, password: string):Promise<{ success: boolean; error?: string }> {
    if (!email || !email.includes('@')) {
      return { success: false, error: 'Invalid email address.' };
    }

    if (!password || password.length < 8) {
      return { success: false, error: 'Password must be at least 8 characters long.' };
    }

    const existingUser = await userStore.findByEmail(email);
    if (existingUser) {
      return { success: false, error: 'Email is already registered.' };
    }

    const passwordHash = await bcrypt.hash(password, SALT_ROUNDS);

    const newUser: User = {
      id: Math.random().toString(36).substring(2, 15),
      email,
      passwordHash,
      failedLoginAttempts: 0,
      lockUntil: null,
      createdAt: new Date(),
    };

    await userStore.save(newUser);
    return { success: true };
  }

  async login(email: string, password: string): Promise<{ success: boolean; token?: string; error?: string }> {
    const user = await userStore.findByEmail(email);
    if (!user) {
      return { success: false, error: 'Invalid email or password.' };
    }

    const now = Date.now();
    if (user.lockUntil && user.lockUntil > now) {
      const minutesRemaining = Math.ceil((user.lockUntil - now) / 60000);
      return {
        success: false,
        error: `Account is temporarily locked due to multiple failed login attempts. Try again in ${minutesRemaining} minute(s).`,
      };
    }

    // If lock expired, reset lock state
    if (user.lockUntil && user.lockUntil <= now) {
      user.lockUntil = null;
      user.failedLoginAttempts = 0;
    }

    const isPasswordValid = await bcrypt.compare(password, user.passwordHash);
    if (!isPasswordValid) {
      user.failedLoginAttempts += 1;
      if (user.failedLoginAttempts >= MAX_FAILED_ATTEMPTS) {
        user.lockUntil = now + LOCK_TIME_MS;
        await userStore.save(user);
        return {
          success: false,
          error: 'Account locked due to 5 consecutive failed login attempts. Please try again later.',
        };
      }
      await userStore.save(user);
      return { success: false, error: 'Invalid email or password.' };
    }

    // Successful login: reset failure metrics
    user.failedLoginAttempts = 0;
    user.lockUntil = null;
    await userStore.save(user);

    const token = jwt.sign({ userId: user.id, email: user.email }, JWT_SECRET, { expiresIn: '1h' });
    return { success: true, token };
  }
}

export const authService = new AuthService();
