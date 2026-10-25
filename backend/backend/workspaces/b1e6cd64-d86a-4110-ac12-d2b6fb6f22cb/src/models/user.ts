export interface User {
  id: string;
  email: string;
  passwordHash: string;
  failedLoginAttempts: number;
  lockUntil: number | null;
  createdAt: Date;
}

// In-memory user store for demonstration purposes (can be replaced with any ORM/DB)
class UserStore {
  private users: Map<string, User> = new Map();

  async findByEmail(email: string): Promise<User | undefined> {
    return this.users.get(email.toLowerCase());
  }

  async findById(id: string): Promise<User | undefined> {
    for (const user of this.users.values()) {
      if (user.id === id) return user;
    }
    return undefined;
  }

  async save(user: User): Promise<void> {
    this.users.set(user.email.toLowerCase(), user);
  }
}

export const userStore = new UserStore();
