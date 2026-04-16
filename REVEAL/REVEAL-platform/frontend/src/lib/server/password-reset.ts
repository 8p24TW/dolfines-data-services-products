import crypto from "node:crypto";
import { prisma } from "@/lib/prisma";
import { hashPassword } from "@/lib/server/passwords";

const RESET_TOKEN_TTL_MS = 1000 * 60 * 60;

function hashToken(token: string) {
  return crypto.createHash("sha256").update(token).digest("hex");
}

function smtpConfigured() {
  return Boolean(
    process.env.SMTP_HOST &&
    process.env.SMTP_PORT &&
    process.env.SMTP_USER &&
    process.env.SMTP_PASSWORD &&
    process.env.SMTP_FROM
  );
}

export async function createPasswordReset(email: string, baseUrl: string) {
  const normalizedEmail = email.trim().toLowerCase();
  const user = await prisma.user.findUnique({
    where: { email: normalizedEmail },
  });

  if (!user) {
    return { ok: true as const };
  }

  await prisma.passwordResetToken.deleteMany({
    where: { userId: user.id },
  });

  const token = crypto.randomBytes(32).toString("hex");
  const tokenHash = hashToken(token);
  const expiresAt = new Date(Date.now() + RESET_TOKEN_TTL_MS);
  const resetUrl = `${baseUrl.replace(/\/$/, "")}/reset-password?token=${token}`;

  await prisma.passwordResetToken.create({
    data: {
      userId: user.id,
      tokenHash,
      expiresAt,
    },
  });

  const mailed = await sendPasswordResetEmail(user.email, resetUrl);
  return {
    ok: true as const,
    mailed,
    devResetUrl: mailed || process.env.NODE_ENV === "production" ? undefined : resetUrl,
  };
}

export async function resetPassword(token: string, password: string) {
  const normalizedToken = token.trim();
  const trimmedPassword = password.trim();

  if (!normalizedToken) {
    return { ok: false as const, message: "Missing reset token." };
  }

  if (trimmedPassword.length < 8) {
    return { ok: false as const, message: "Password must be at least 8 characters." };
  }

  const tokenHash = hashToken(normalizedToken);
  const resetRecord = await prisma.passwordResetToken.findUnique({
    where: { tokenHash },
    include: { user: true },
  });

  if (
    !resetRecord ||
    resetRecord.consumedAt ||
    resetRecord.expiresAt.getTime() < Date.now()
  ) {
    return { ok: false as const, message: "This reset link is invalid or has expired." };
  }

  const hashedPassword = await hashPassword(trimmedPassword);

  await prisma.$transaction([
    prisma.user.update({
      where: { id: resetRecord.userId },
      data: { password: hashedPassword },
    }),
    prisma.passwordResetToken.update({
      where: { id: resetRecord.id },
      data: { consumedAt: new Date() },
    }),
    prisma.passwordResetToken.deleteMany({
      where: {
        userId: resetRecord.userId,
        id: { not: resetRecord.id },
      },
    }),
  ]);

  return { ok: true as const };
}

export async function sendWelcomeEmail(email: string, name: string) {
  if (!smtpConfigured()) {
    return false;
  }

  const appUrl = process.env.NEXTAUTH_URL?.replace(/\/$/, "") || "https://dolfines-data-services-products.vercel.app";
  const firstName = name.trim().split(/\s+/)[0] || "there";

  const nodemailer = await import("nodemailer");
  const transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT ?? 587),
    secure: process.env.SMTP_SECURE === "true",
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASSWORD,
    },
  });

  await transporter.sendMail({
    from: process.env.SMTP_FROM,
    to: email,
    subject: "Welcome to the REVEAL platform",
    text: `Welcome to REVEAL, ${firstName}.\n\nYour account is now active.\n\nYou can sign in here: ${appUrl}\n\nREVEAL supports solar PV and wind performance analysis, long-term normalization, electricity price forecasting, BESS retrofit screening and equipment intelligence.\n\nBest regards,\n8p2 Advisory`,
    html: `
      <div style="font-family:Arial,sans-serif;line-height:1.6;color:#0b2a3d">
        <h2 style="margin:0 0 16px;color:#0b2a3d">Welcome to the REVEAL platform</h2>
        <p>Hello ${firstName},</p>
        <p>Your REVEAL account is now active.</p>
        <p>
          <a href="${appUrl}" style="display:inline-block;padding:12px 18px;background:#f39200;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600">
            Open REVEAL
          </a>
        </p>
        <p>REVEAL supports solar PV and wind performance analysis, long-term normalization, electricity price forecasting, BESS retrofit screening and equipment intelligence.</p>
        <p>Best regards,<br />8p2 Advisory</p>
      </div>
    `,
  });

  return true;
}

async function sendPasswordResetEmail(email: string, resetUrl: string) {
  if (!smtpConfigured()) {
    return false;
  }

  const nodemailer = await import("nodemailer");
  const transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT ?? 587),
    secure: process.env.SMTP_SECURE === "true",
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASSWORD,
    },
  });

  await transporter.sendMail({
    from: process.env.SMTP_FROM,
    to: email,
    subject: "Reset your REVEAL password",
    text: `Use this link to reset your REVEAL password: ${resetUrl}`,
    html: `
      <div style="font-family:Arial,sans-serif;line-height:1.6;color:#0b2a3d">
        <h2 style="margin:0 0 16px;color:#0b2a3d">REVEAL Renewable Energy Valuation, Evaluation and Analytics Lab</h2>
        <p>A password reset was requested for your account.</p>
        <p>
          <a href="${resetUrl}" style="display:inline-block;padding:12px 18px;background:#f39200;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600">
            Reset password
          </a>
        </p>
        <p>If you did not request this, you can ignore this email.</p>
      </div>
    `,
  });

  return true;
}
