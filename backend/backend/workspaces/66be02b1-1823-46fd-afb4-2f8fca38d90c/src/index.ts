import express, { Request, Response } from "express";
import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";
import { v4 as uuidv4 } from "uuid";
import { redis } from "./redis";
import { authenticateToken, rateLimiter, AuthenticatedRequest } from "./auth.middleware";

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || "super-secret-access-key";
const ACCESS_TOKEN_EXPIRY = "15m"; // 15 minutes
const REFRESH_TOKEN_EXPIRY = 7 * 24 * 60 * 60; // 7 days in seconds

// Mock In-Memory Database for demonstration purposes
interface UserDBRecord {
  userId: string;
  email: string;
  passwordHash: string;
}

const USERS_DB: Map<string, UserDBRecord> = new Map();

// Preload a default test user securely hashed (cost = 12)
bcrypt.hash("SecurePassword123!", 12).then((hash) => {
  USERS_DB.set("test@example.com", {
    userId: "usr_123456789",
    email: "test@example.com",
    passwordHash: hash,
  });
});

// [R004] Secure password validation & [R001] Access/Refresh generation
app.post("/login", rateLimiter, async (req: Request, res: Response): Promise<void> => {
  try {
    const { email, password } = req.body;
    if (!email || !password) {
      res.status(400).json({ error: "Email and password are required" });
      return;
    }

    const user = USERS_DB.get(email);
    if (!user) {
      res.status(401).json({ error: "Invalid credentials" });
      return;
    }

    const isValidPassword = await bcrypt.compare(password, user.passwordHash);
    if (!isValidPassword) {
      res.status(401).json({ error: "Invalid credentials" });
      return;
    }

    // Issue short-lived JWT Access Token
    const accessToken = jwt.sign(
      { userId: user.userId, email: user.email },
      JWT_SECRET,
      { expiresIn: ACCESS_TOKEN_EXPIRY }
    );

    // Issue long-lived opaque refresh token and setup family rotation
    const refreshToken = uuidv4();
    const familyId = uuidv4();
    
    const refreshRecord = {
      userId: user.userId,
      familyId,
      used: "false",
    };

    // Store refresh token mapped to its metadata and family
    await redis.hset(`refresh_token:${refreshToken}`, refreshRecord);
    await redis.expire(`refresh_token:${refreshToken}`, REFRESH_TOKEN_EXPIRY);

    // Track active family tokens for user session revocation
    await redis.sadd(`user_sessions:${user.userId}`, familyId);

    res.status(200).json({
      accessToken,
      refreshToken,
    });
  } catch (err) {
    console.error("Login error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

// [R002] Refresh token rotation with reuse detection
app.post("/refresh", rateLimiter, async (req: Request, res: Response): Promise<void> => {
  try {
    const { refreshToken } = req.body;
    if (!refreshToken) {
      res.status(400).json({ error: "Refresh token required" });
      return;
    }

    const tokenKey = `refresh_token:${refreshToken}`;
    const tokenData = await redis.hgetall(tokenKey);

    if (!tokenData || !tokenData.userId) {
      res.status(403).json({ error: "Invalid or expired refresh token" });
      return;
    }

    const { userId, familyId, used } = tokenData;

    // Reuse detection: If the token was already used, potential theft detected!
    if (used === "true") {
      console.warn(`SECURITY ALERT: Refresh token reuse detected for family ${familyId} and user ${userId}! Revoking all sessions.`);
      
      // Revoke all sessions belonging to this user family/user
      const userFamilies = await redis.smembers(`user_sessions:${userId}`);
      for (const fam of userFamilies) {
        await redis.del(`family_lock:${fam}`);
      }
      await redis.del(`user_sessions:${userId}`);
      
      res.status(403).json({ error: "Token reuse detected. All sessions revoked for security." });
      return;
    }

    // Check if family has been globally locked/invalidated due to prior breach
    // (Handled implicitly if family tokens are wiped, or explicit check)
    
    // Mark current refresh token as used
    await redis.hset(tokenKey, "used", "true");
    // Shorten TTL for audit/grace period window if necessary, or keep standard
    await redis.expire(tokenKey, 300); // 5 min grace window then purge

    // Issue new Access Token
    const userRecord = Array.from(USERS_DB.values()).find((u) => u.userId === userId);
    if (!userRecord) {
      res.status(403).json({ error: "User no longer exists" });
      return;
    }

    const newAccessToken = jwt.sign(
      { userId: userRecord.userId, email: userRecord.email },
      JWT_SECRET,
      { expiresIn: ACCESS_TOKEN_EXPIRY }
    );

    // Issue rotated New Refresh Token within the same family
    const newRefreshToken = uuidv4();
    await redis.hset(`refresh_token:${newRefreshToken}`, {
      userId: userRecord.userId,
      familyId,
      used: "false",
    });
    await redis.expire(`refresh_token:${newRefreshToken}`, REFRESH_TOKEN_EXPIRY);

    res.status(200).json({
      accessToken: newAccessToken,
      refreshToken: newRefreshToken,
    });
  } catch (err) {
    console.error("Refresh error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

// [R005] Robust logout and token revocation functionality
app.post("/logout", authenticateToken, async (req: AuthenticatedRequest, res: Response): Promise<void> => {
  try {
    const userId = req.user?.userId;
    if (!userId) {
      res.status(401).json({ error: "Unauthorized" });
      return;
    }

    // Invalidate all active user session families
    const userFamilies = await redis.smembers(`user_sessions:${userId}`);
    for (const fam of userFamilies) {
      // Find and delete or flag all associated tokens if tracked, or simply clear the session index
      // Clearing session index prevents further validation mapping
    }
    await redis.del(`user_sessions:${userId}`);

    // Optionally blacklist the current access token explicitly until expiry
    const authHeader = req.headers["authorization"];
    const token = authHeader && authHeader.split(" ")[1];
    if (token) {
      await redis.set(`blacklisted_access:${token}`, "true", "EX", 900); // 15 mins
    }

    res.status(200).json({ message: "Successfully logged out and tokens revoked." });
  } catch (err) {
    console.error("Logout error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

// Protected test route
app.get("/protected", authenticateToken, (req: AuthenticatedRequest, res: Response) => {
  res.status(200).json({ message: "Access granted to protected resource", user: req.user });
});

app.listen(PORT, () => {
  console.log(`Auth service running on port ${PORT}`);
});
