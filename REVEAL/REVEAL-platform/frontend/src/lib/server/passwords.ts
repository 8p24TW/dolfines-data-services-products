import { randomBytes, scrypt as nodeScrypt, timingSafeEqual } from "node:crypto";
import { promisify } from "node:util";

const scrypt = promisify(nodeScrypt);
const HASH_PREFIX = "scrypt";
const KEY_LENGTH = 64;

export async function hashPassword(password: string) {
  const salt = randomBytes(16).toString("hex");
  const derived = (await scrypt(password, salt, KEY_LENGTH)) as Buffer;
  return `${HASH_PREFIX}$${salt}$${derived.toString("hex")}`;
}

export async function verifyPassword(password: string, storedPassword: string) {
  if (!storedPassword.startsWith(`${HASH_PREFIX}$`)) {
    return storedPassword === password;
  }

  const [, salt, hashHex] = storedPassword.split("$");
  if (!salt || !hashHex) {
    return false;
  }

  const derived = (await scrypt(password, salt, KEY_LENGTH)) as Buffer;
  const storedHash = Buffer.from(hashHex, "hex");
  return storedHash.length === derived.length && timingSafeEqual(storedHash, derived);
}
