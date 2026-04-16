import crypto from "node:crypto";
import { prisma } from "@/lib/prisma";
import { hashPassword, passwordMeetsPolicy, passwordPolicyMessage } from "@/lib/server/passwords";

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

  if (!passwordMeetsPolicy(trimmedPassword)) {
    return { ok: false as const, message: passwordPolicyMessage() };
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
  const logoUrl = `${appUrl}/brand/logo-white.png`;
  const fontStack = `Montserrat, "Open Sans", Aptos, Calibri, Arial, sans-serif`;

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
    subject: "Welcome to REVEAL",
    text: `Hello ${firstName},\n\nYour REVEAL account is now active.\n\nAccess REVEAL: ${appUrl}\n\nREVEAL supports solar PV and wind performance analysis, long-term normalization, electricity price forecasting, BESS retrofit screening and equipment intelligence.\n\nIf you have any questions, please contact us at consulting@8p2.fr.\n\nBest regards,\n8p2 Advisory\n\n8p2 Advisory, part of the Dolfines SA Group`,
    html: `
      <!DOCTYPE html>
      <html lang="en">
        <body style="margin:0;padding:0;background:#dfe7ef;font-family:${fontStack};">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dfe7ef;padding:28px 0;">
            <tr>
              <td align="center">
                <table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" style="width:640px;max-width:640px;background:#0b2233;overflow:hidden;box-shadow:0 18px 48px rgba(8,20,30,0.18);">
                  <tr>
                    <td style="background:#0a2030;padding:28px 34px 26px 34px;font-family:${fontStack};">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                          <td valign="top" align="left" style="padding-right:18px;">
                            <div style="font-size:18px;line-height:1.55;color:#e6edf3;max-width:360px;font-family:${fontStack};">Renewable Energy Valuation, Evaluation and Analytics Lab</div>
                          </td>
                          <td valign="top" align="right" style="width:180px;">
                            <img src="${logoUrl}" alt="8p2 Advisory" width="150" style="display:block;width:150px;height:auto;border:0;margin-left:auto;" />
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                  <tr>
                    <td style="background:#163247;padding:30px 54px 30px 54px;color:#f4f7fa;font-family:${fontStack};">
                      <div style="font-size:27px;line-height:1.25;font-weight:700;color:#ffffff;margin:0 0 22px 0;font-family:${fontStack};">Welcome to the REVEAL platform</div>
                      <div style="font-size:15px;line-height:1.8;color:#f0f5f8;margin:0 0 10px 0;font-family:${fontStack};">Hello ${firstName},</div>
                      <div style="font-size:15px;line-height:1.8;color:#f0f5f8;margin:0 0 14px 0;font-family:${fontStack};">Your REVEAL account is now active.</div>
                      <div style="font-size:15px;line-height:1.8;color:#d9e5ee;margin:0 0 24px 0;max-width:470px;font-family:${fontStack};">
                        REVEAL supports solar PV and wind performance analysis, long-term normalization, electricity price forecasting, BESS retrofit screening and equipment intelligence.
                      </div>
                      <div style="margin:6px 0 24px 0;text-align:center;">
                        <a href="${appUrl}" style="display:inline-block;color:#f39200;text-decoration:none;font-size:24px;line-height:1.2;font-weight:700;font-family:${fontStack};text-align:center;letter-spacing:0.02em;text-shadow:0 0 12px rgba(255,255,255,0.32), 0 0 24px rgba(255,255,255,0.16);">Access REVEAL</a>
                      </div>
                      <div style="font-size:15px;line-height:1.8;color:#d9e5ee;margin:0 0 18px 0;font-family:${fontStack};">
                        If you have any questions, please contact us at
                        <a href="mailto:consulting@8p2.fr" style="color:#f6ac45;text-decoration:none;font-weight:700;font-family:${fontStack};">consulting@8p2.fr</a>.
                      </div>
                      <div style="font-size:15px;line-height:1.8;color:#f0f5f8;font-family:${fontStack};">Best regards,<br />8p2 Advisory</div>
                    </td>
                  </tr>
                  <tr>
                    <td style="background:#0a2030;padding:16px 34px 18px 34px;font-size:12px;line-height:1.6;color:#a8bccb;font-family:${fontStack};">
                      8p2 Advisory, part of the Dolfines SA Group
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </body>
      </html>
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
