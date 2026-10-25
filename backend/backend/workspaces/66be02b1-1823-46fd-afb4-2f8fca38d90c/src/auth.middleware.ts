import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { redis } from "./redis";

const JWT_SECRET = process.env.JWT_SECRET || "super-secret-access-key";

export interface AuthenticatedRequest extends Request {
  user?: {
    userId: string;
    email: string;
  };
}

export async function authenticateToken(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> {
  const authHeader = req.headers["authorization"];
  const token = authHeader && authHeader.split(" ")[1];

  if (!token) {
    res.status(401).json({ error: "Access token missing" });
    return;
  }

  try {
    const payload = jwt.verify(token, JWT_SECRET) as { userId: string; email: string };
    
    // Check if token family/session is globally revoked
    const isRevoked = await redis.get(`blacklisted_access:${token}`);
    if (isRevoked) {
      res.status(403).json({ error: "Token has been revoked" });
      return;
    }

    req.user = payload;
    next();
  } catch (err) {
    res.status(403).json({ error: "Invalid or expired access token" });
  }
}

export async function rateLimiter(req: Request, res: Response, next: NextFunction): Promise<void> {
  const ip = req.ip || req.socket.remoteAddress || "unknown";
  const key = `rate_limit:${ip}`;
  const windowSecs = 60;
  const maxRequests = 10;

  try {
    const requests = await redis.incr(key);
    if (requests === 1) {
      await redis.expire(key, windowSecs);
    }

    if (requests > maxRequests) {
      res.status(429).json({ error: "Too many requests, please try again later." });
      return;
    }

    next();
  } catch (err) {
    console.error("Rate limiter error:", err);
    // Fail open if Redis is down, or fail closed depending on strictness. Here we pass.
    next();
  }
}
