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
  const f = `Montserrat,Aptos,Calibri,Arial,sans-serif`;

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
    text: [
      `Hello ${firstName},`,
      ``,
      `Your REVEAL account is now active.`,
      ``,
      `Access REVEAL: ${appUrl}`,
      ``,
      `REVEAL supports solar PV and wind performance analysis, long-term normalization, electricity price forecasting, BESS retrofit screening and equipment intelligence.`,
      ``,
      `Questions? Contact us at consulting@8p2.fr`,
      ``,
      `Best regards,`,
      `8p2 Advisory — part of the Dolfines SA Group`,
    ].join("\n"),
    html: `<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>Welcome to REVEAL</title>
<style>@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&display=swap');</style>
</head>
<body style="margin:0;padding:0;background-color:#020C15;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#020C15" style="background-color:#020C15;">
<tr><td align="center" style="padding:36px 12px;">

  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;">

    <!-- Orange top bar -->
    <tr><td bgcolor="#F39200" height="4" style="height:4px;font-size:0;line-height:0;background-color:#F39200;">&nbsp;</td></tr>

    <!-- Header -->
    <tr>
      <td bgcolor="#051825" style="padding:26px 36px 22px 36px;background-color:#051825;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td valign="middle">
              <div style="font-family:${f};font-size:30px;font-weight:800;letter-spacing:0.14em;color:#FFFFFF;line-height:1;margin:0 0 5px 0;">REVEAL</div>
              <div style="font-family:${f};font-size:9px;font-weight:600;letter-spacing:0.22em;text-transform:uppercase;color:#7A9BB0;margin:0;">Renewable Energy Valuation, Evaluation and Analytics Lab</div>
            </td>
            <td valign="middle" align="right" style="padding-left:20px;">
              <img src="${logoUrl}" alt="8p2 Advisory" width="150" style="display:block;width:150px;height:auto;border:0;" />
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Separator -->
    <tr><td bgcolor="#0B2A3D" height="1" style="height:1px;font-size:0;line-height:0;background-color:#0B2A3D;">&nbsp;</td></tr>

    <!-- Hero -->
    <tr>
      <td bgcolor="#0B2A3D" style="padding:40px 36px 36px 36px;background-color:#0B2A3D;">
        <div style="font-family:${f};font-size:10px;font-weight:700;letter-spacing:0.28em;text-transform:uppercase;color:#F39200;margin:0 0 16px 0;">Account activated</div>
        <div style="font-family:${f};font-size:24px;font-weight:700;line-height:1.35;color:#FFFFFF;margin:0 0 16px 0;">Welcome to the platform, ${firstName}.</div>
        <div style="font-family:${f};font-size:15px;line-height:1.8;color:#8DAFC4;margin:0 0 32px 0;">You now have full access to REVEAL — the professional platform for renewable energy analysis, price intelligence and technology screening.</div>
        <!-- CTA -->
        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td bgcolor="#F39200" style="border-radius:8px;background-color:#F39200;">
              <a href="${appUrl}" style="display:inline-block;padding:14px 34px;background-color:#F39200;color:#FFFFFF;text-decoration:none;font-family:${f};font-size:14px;font-weight:700;letter-spacing:0.07em;border-radius:8px;line-height:1;text-align:center;">Open REVEAL &#8594;</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Features label -->
    <tr>
      <td bgcolor="#071E2C" style="padding:28px 36px 0 36px;background-color:#071E2C;">
        <div style="font-family:${f};font-size:9px;font-weight:700;letter-spacing:0.3em;text-transform:uppercase;color:#4A6A7E;border-top:1px solid #132C3E;padding-top:22px;margin:0 0 20px 0;">What REVEAL does</div>
      </td>
    </tr>

    <!-- Features grid -->
    <tr>
      <td bgcolor="#071E2C" style="padding:0 36px 32px 36px;background-color:#071E2C;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <!-- Left column -->
            <td width="50%" valign="top" style="padding-right:14px;">
              <!-- Feature 1 -->
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:18px;">
                <tr>
                  <td width="24" valign="top" style="padding-top:1px;">
                    <div style="width:6px;height:6px;background-color:#F39200;border-radius:50%;margin-top:6px;">&nbsp;</div>
                  </td>
                  <td style="padding-left:10px;">
                    <div style="font-family:${f};font-size:13px;font-weight:700;color:#FFFFFF;margin:0 0 3px 0;">Solar PV &amp; Wind Analysis</div>
                    <div style="font-family:${f};font-size:12px;line-height:1.6;color:#4A6A7E;">Performance analysis and long-term normalization</div>
                  </td>
                </tr>
              </table>
              <!-- Feature 2 -->
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td width="24" valign="top" style="padding-top:1px;">
                    <div style="width:6px;height:6px;background-color:#F39200;border-radius:50%;margin-top:6px;">&nbsp;</div>
                  </td>
                  <td style="padding-left:10px;">
                    <div style="font-family:${f};font-size:13px;font-weight:700;color:#FFFFFF;margin:0 0 3px 0;">BESS Retrofit Screening</div>
                    <div style="font-family:${f};font-size:12px;line-height:1.6;color:#4A6A7E;">Battery sizing and economic assessment</div>
                  </td>
                </tr>
              </table>
            </td>
            <!-- Right column -->
            <td width="50%" valign="top" style="padding-left:14px;">
              <!-- Feature 3 -->
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:18px;">
                <tr>
                  <td width="24" valign="top" style="padding-top:1px;">
                    <div style="width:6px;height:6px;background-color:#F39200;border-radius:50%;margin-top:6px;">&nbsp;</div>
                  </td>
                  <td style="padding-left:10px;">
                    <div style="font-family:${f};font-size:13px;font-weight:700;color:#FFFFFF;margin:0 0 3px 0;">Electricity Price Forecasting</div>
                    <div style="font-family:${f};font-size:12px;line-height:1.6;color:#4A6A7E;">Long-term scenarios with capture rates</div>
                  </td>
                </tr>
              </table>
              <!-- Feature 4 -->
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td width="24" valign="top" style="padding-top:1px;">
                    <div style="width:6px;height:6px;background-color:#F39200;border-radius:50%;margin-top:6px;">&nbsp;</div>
                  </td>
                  <td style="padding-left:10px;">
                    <div style="font-family:${f};font-size:13px;font-weight:700;color:#FFFFFF;margin:0 0 3px 0;">Equipment Intelligence</div>
                    <div style="font-family:${f};font-size:12px;line-height:1.6;color:#4A6A7E;">Technology knowledge base and benchmarking</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Contact -->
    <tr>
      <td bgcolor="#0B2A3D" style="padding:22px 36px;background-color:#0B2A3D;border-top:1px solid #132C3E;">
        <div style="font-family:${f};font-size:13px;line-height:1.7;color:#4A6A7E;">Questions? Reach us at <a href="mailto:consulting@8p2.fr" style="color:#F39200;text-decoration:none;font-weight:600;">consulting@8p2.fr</a></div>
      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td bgcolor="#020C15" style="padding:18px 36px;background-color:#020C15;">
        <div style="font-family:${f};font-size:10px;font-weight:600;letter-spacing:0.16em;text-transform:uppercase;color:#2A4A5E;">8p2 Advisory &bull; Part of the Dolfines SA Group</div>
      </td>
    </tr>

    <!-- Orange bottom bar -->
    <tr><td bgcolor="#F39200" height="3" style="height:3px;font-size:0;line-height:0;background-color:#F39200;">&nbsp;</td></tr>

  </table>

</td></tr>
</table>
</body>
</html>`,
  });

  return true;
}

async function sendPasswordResetEmail(email: string, resetUrl: string) {
  if (!smtpConfigured()) {
    return false;
  }

  const appUrl = process.env.NEXTAUTH_URL?.replace(/\/$/, "") || "https://dolfines-data-services-products.vercel.app";
  const logoUrl = `${appUrl}/brand/logo-white.png`;
  const f = `Montserrat,Aptos,Calibri,Arial,sans-serif`;

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
    text: [
      `A password reset was requested for your REVEAL account.`,
      ``,
      `Use this link to reset your password (valid for 1 hour):`,
      resetUrl,
      ``,
      `If you did not request this, you can safely ignore this email.`,
      ``,
      `8p2 Advisory — part of the Dolfines SA Group`,
    ].join("\n"),
    html: `<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>Reset your REVEAL password</title>
<style>@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&display=swap');</style>
</head>
<body style="margin:0;padding:0;background-color:#020C15;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#020C15" style="background-color:#020C15;">
<tr><td align="center" style="padding:36px 12px;">

  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;">

    <!-- Orange top bar -->
    <tr><td bgcolor="#F39200" height="4" style="height:4px;font-size:0;line-height:0;background-color:#F39200;">&nbsp;</td></tr>

    <!-- Header -->
    <tr>
      <td bgcolor="#051825" style="padding:26px 36px 22px 36px;background-color:#051825;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td valign="middle">
              <div style="font-family:${f};font-size:30px;font-weight:800;letter-spacing:0.14em;color:#FFFFFF;line-height:1;margin:0 0 5px 0;">REVEAL</div>
              <div style="font-family:${f};font-size:9px;font-weight:600;letter-spacing:0.22em;text-transform:uppercase;color:#7A9BB0;margin:0;">Renewable Energy Valuation, Evaluation and Analytics Lab</div>
            </td>
            <td valign="middle" align="right" style="padding-left:20px;">
              <img src="${logoUrl}" alt="8p2 Advisory" width="150" style="display:block;width:150px;height:auto;border:0;" />
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Separator -->
    <tr><td bgcolor="#0B2A3D" height="1" style="height:1px;font-size:0;line-height:0;background-color:#0B2A3D;">&nbsp;</td></tr>

    <!-- Body -->
    <tr>
      <td bgcolor="#0B2A3D" style="padding:40px 36px 36px 36px;background-color:#0B2A3D;">
        <div style="font-family:${f};font-size:10px;font-weight:700;letter-spacing:0.28em;text-transform:uppercase;color:#F39200;margin:0 0 16px 0;">Password reset</div>
        <div style="font-family:${f};font-size:22px;font-weight:700;line-height:1.35;color:#FFFFFF;margin:0 0 16px 0;">Reset your password</div>
        <div style="font-family:${f};font-size:15px;line-height:1.8;color:#8DAFC4;margin:0 0 12px 0;">A password reset was requested for your REVEAL account.</div>
        <div style="font-family:${f};font-size:15px;line-height:1.8;color:#8DAFC4;margin:0 0 32px 0;">Click the button below to choose a new password. This link is valid for <strong style="color:#FFFFFF;">1 hour</strong>.</div>
        <!-- CTA -->
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:32px;">
          <tr>
            <td bgcolor="#F39200" style="border-radius:8px;background-color:#F39200;">
              <a href="${resetUrl}" style="display:inline-block;padding:14px 34px;background-color:#F39200;color:#FFFFFF;text-decoration:none;font-family:${f};font-size:14px;font-weight:700;letter-spacing:0.07em;border-radius:8px;line-height:1;text-align:center;">Reset password &#8594;</a>
            </td>
          </tr>
        </table>
        <div style="font-family:${f};font-size:13px;line-height:1.7;color:#4A6A7E;">If you did not request a password reset, you can safely ignore this email. Your account remains secure.</div>
      </td>
    </tr>

    <!-- Contact -->
    <tr>
      <td bgcolor="#0B2A3D" style="padding:22px 36px;background-color:#0B2A3D;border-top:1px solid #132C3E;">
        <div style="font-family:${f};font-size:13px;line-height:1.7;color:#4A6A7E;">Questions? Reach us at <a href="mailto:consulting@8p2.fr" style="color:#F39200;text-decoration:none;font-weight:600;">consulting@8p2.fr</a></div>
      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td bgcolor="#020C15" style="padding:18px 36px;background-color:#020C15;">
        <div style="font-family:${f};font-size:10px;font-weight:600;letter-spacing:0.16em;text-transform:uppercase;color:#2A4A5E;">8p2 Advisory &bull; Part of the Dolfines SA Group</div>
      </td>
    </tr>

    <!-- Orange bottom bar -->
    <tr><td bgcolor="#F39200" height="3" style="height:3px;font-size:0;line-height:0;background-color:#F39200;">&nbsp;</td></tr>

  </table>

</td></tr>
</table>
</body>
</html>`,
  });

  return true;
}
