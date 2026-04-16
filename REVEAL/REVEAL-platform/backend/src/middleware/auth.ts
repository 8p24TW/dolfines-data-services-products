import type { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import jwksClient from "jwks-rsa";

const TENANT_ID = process.env.AZURE_TENANT_ID!;
const AUDIENCE = process.env.JWT_AUDIENCE ?? process.env.AZURE_CLIENT_ID!;

const client = jwksClient({
  jwksUri: `https://login.microsoftonline.com/${TENANT_ID}/discovery/v2.0/keys`,
  cache: true,
  cacheMaxEntries: 5,
  cacheMaxAge: 600_000, // 10 min
});

function getKey(header: jwt.JwtHeader, callback: jwt.SigningKeyCallback) {
  client.getSigningKey(header.kid!, (err, key) => {
    if (err) return callback(err);
    callback(null, key?.getPublicKey());
  });
}

export interface AuthRequest extends Request {
  user?: { oid: string; email: string; name: string };
}

export function requireAuth(req: AuthRequest, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith("Bearer ")) {
    return res.status(401).json({ error: "Missing Bearer token" });
  }
  const token = authHeader.slice(7);

  jwt.verify(token, getKey, { audience: AUDIENCE }, (err, decoded) => {
    if (err) return res.status(401).json({ error: "Invalid token", detail: err.message });
    const payload = decoded as jwt.JwtPayload;
    req.user = {
      oid: payload.oid ?? payload.sub ?? "",
      email: payload.preferred_username ?? payload.email ?? "",
      name: payload.name ?? "",
    };
    next();
  });
}
