"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { signIn } from "next-auth/react";
import { Button } from "@/components/ui/Button";
import { BrandLockup } from "@/components/layout/BrandLockup";
import { useTranslation } from "@/lib/i18n";

const googleEnabled = process.env.NEXT_PUBLIC_GOOGLE_LOGIN_ENABLED === "true";
const PASSWORD_HELP =
  "At least 10 characters, including uppercase, lowercase, and a number.";

const LOGIN_COPY = {
  en: {
    title: "REVEAL",
    subtitle:
      "Solar PV and wind performance analysis, long-term normalization, electricity price forecasting, BESS retrofit screening and equipment intelligence.",
    email: "Email",
    password: "Password",
    name: "Full name",
    signIn: "Sign in",
    createAccount: "Create account",
    createMode: "Need access for the first time?",
    existingMode: "Already have an account?",
    forgot: "Forgot password?",
    google: "Continue with Google",
    helper:
      "Use any email address to create an account. Gmail, Outlook, Hotmail and corporate addresses are all supported.",
    passwordHelp: PASSWORD_HELP,
    confirmPassword: "Confirm password",
    mismatch: "Passwords do not match.",
    powered: "Powered by 8p2 Advisory",
    invalid: "Incorrect email or password.",
    registerSuccess: "Account created. Signing you in now...",
    registerError: "Unable to create your account right now.",
  },
  fr: {
    title: "REVEAL",
    subtitle:
      "Analyse de performance solaire PV et éolienne, normalisation long terme, prévision des prix de l'électricité, dimensionnement de retrofit BESS et intelligence équipement.",
    email: "E-mail",
    password: "Mot de passe",
    name: "Nom complet",
    signIn: "Se connecter",
    createAccount: "Créer un compte",
    createMode: "Premier accès ?",
    existingMode: "Vous avez déjà un compte ?",
    forgot: "Mot de passe oublié ?",
    google: "Continuer avec Google",
    helper:
      "Utilisez n'importe quelle adresse e-mail pour créer un compte. Gmail, Outlook, Hotmail et les adresses professionnelles sont pris en charge.",
    passwordHelp: PASSWORD_HELP,
    confirmPassword: "Confirmer le mot de passe",
    mismatch: "Les mots de passe ne correspondent pas.",
    powered: "Powered by 8p2 Advisory",
    invalid: "E-mail ou mot de passe incorrect.",
    registerSuccess: "Compte créé. Connexion en cours...",
    registerError: "Impossible de créer votre compte pour le moment.",
  },
  de: {
    title: "REVEAL",
    subtitle:
      "Solar- und Windleistungsanalyse, Langfristnormalisierung, Strompreisvorhersage, BESS-Retrofit-Screening und Anlagenintelligenz.",
    email: "E-Mail",
    password: "Passwort",
    name: "Vollständiger Name",
    signIn: "Anmelden",
    createAccount: "Konto erstellen",
    createMode: "Zum ersten Mal hier?",
    existingMode: "Sie haben bereits ein Konto?",
    forgot: "Passwort vergessen?",
    google: "Mit Google fortfahren",
    helper:
      "Sie können mit jeder E-Mail-Adresse ein Konto erstellen. Gmail, Outlook, Hotmail und Unternehmensadressen werden unterstützt.",
    passwordHelp: PASSWORD_HELP,
    confirmPassword: "Passwort bestätigen",
    mismatch: "Die Passwörter stimmen nicht überein.",
    powered: "Powered by 8p2 Advisory",
    invalid: "Falsche E-Mail oder falsches Passwort.",
    registerSuccess: "Konto erstellt. Anmeldung läuft...",
    registerError: "Ihr Konto konnte gerade nicht erstellt werden.",
  },
} as const;

export default function LoginPage() {
  const { lang, setLang } = useTranslation();
  const [displayLang, setDisplayLang] = useState(lang);
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDisplayLang(lang);
  }, [lang]);

  const copy = LOGIN_COPY[displayLang] ?? LOGIN_COPY.en;

  async function handleCredentialsSignIn() {
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const result = await signIn("credentials", {
        email,
        password,
        callbackUrl: "/dashboard",
        redirect: false,
      });

      if (result?.error) {
        setError(copy.invalid);
        return;
      }

      window.location.href = result?.url ?? "/dashboard";
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRegister() {
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      if (password !== confirmPassword) {
        setError(copy.mismatch);
        return;
      }

      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        setError(payload?.message ?? copy.registerError);
        return;
      }

      setMessage(copy.registerSuccess);
      const result = await signIn("credentials", {
        email,
        password,
        callbackUrl: "/dashboard",
        redirect: false,
      });

      if (result?.error) {
        setMode("signin");
        setError(copy.invalid);
        return;
      }

      window.location.href = result?.url ?? "/dashboard";
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogleSignIn() {
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const result = await signIn("google", {
        callbackUrl: "/dashboard",
        redirect: false,
      });

      if (result?.error || !result?.url) {
        setError("Google sign-in is not available yet.");
        return;
      }

      window.location.href = result.url;
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <Image
        src="/brand/login-hero.jpg"
        alt="Wind farm background"
        fill
        priority
        className="object-cover"
      />
      <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(2,18,28,0.9),rgba(5,30,45,0.66),rgba(240,120,32,0.18))]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.12),transparent_42%)]" />
      <div className="absolute left-8 top-7 z-10 flex items-center gap-3 whitespace-nowrap">
        <BrandLockup href="/login" />
        <span className="text-sm font-medium text-white/75 drop-shadow">
          Renewable Energy Valuation, Evaluation and Analytics Lab
        </span>
      </div>
      <div className="absolute right-6 top-6 z-20 flex items-center gap-2 rounded-full border border-white/20 bg-[rgba(3,20,31,0.78)] px-2.5 py-1.5 shadow-[0_10px_30px_rgba(0,0,0,0.22)] backdrop-blur-md">
        <span className="text-[10px] font-semibold uppercase tracking-[0.26em] text-white/70">
          Language
        </span>
        <div className="flex items-center gap-1">
          {(["en", "fr", "de"] as const).map((option) => {
            const active = displayLang === option;
            return (
              <button
                key={option}
                type="button"
                onClick={() => {
                  setDisplayLang(option);
                  setLang(option);
                }}
                className={`min-w-[34px] rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
                  active
                    ? "bg-orange-DEFAULT text-white shadow-[0_8px_24px_rgba(240,120,32,0.28)]"
                    : "bg-white/6 text-white/78 hover:bg-white/12 hover:text-white"
                }`}
              >
                {option.toUpperCase()}
              </button>
            );
          })}
        </div>
      </div>

      <div
        key={displayLang}
        className="relative w-full max-w-md rounded-[28px] border border-orange-DEFAULT/25 bg-orange-DEFAULT/10 p-8 shadow-[0_32px_90px_rgba(0,0,0,0.4)] backdrop-blur-md transition-colors hover:bg-orange-DEFAULT/15"
      >
        <div className="mb-8 text-center">
          <h1 className="font-dolfines text-5xl font-semibold tracking-[0.08em] text-white">
            {copy.title}
          </h1>
          <p className="mt-4 text-sm text-slate-200/78">{copy.subtitle}</p>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-white/14 bg-white/7 px-4 py-4 text-sm text-slate-100/88 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
            {copy.helper}
          </div>

          {mode === "register" ? (
            <div>
              <label className="mb-1 block text-xs font-bold uppercase tracking-[0.22em] text-slate-200/78">
                {copy.name}
              </label>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="w-full rounded-xl border border-white/12 bg-white px-3 py-2.5 text-sm font-medium text-slate-950 placeholder:text-slate-500 focus:border-orange-DEFAULT focus:outline-none"
              />
            </div>
          ) : null}

          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-[0.22em] text-slate-200/78">
              {copy.email}
            </label>
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-xl border border-white/12 bg-white px-3 py-2.5 text-sm font-medium text-slate-950 placeholder:text-slate-500 focus:border-orange-DEFAULT focus:outline-none"
            />
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between gap-3">
              <label className="block text-xs font-bold uppercase tracking-[0.22em] text-slate-200/78">
                {copy.password}
              </label>
              {mode === "signin" ? (
                <Link href="/forgot-password" className="text-xs font-semibold text-orange-DEFAULT hover:text-orange-accent">
                  {copy.forgot}
                </Link>
              ) : null}
            </div>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-xl border border-white/12 bg-white px-3 py-2.5 text-sm font-medium text-slate-950 placeholder:text-slate-500 focus:border-orange-DEFAULT focus:outline-none"
            />
            {mode === "register" ? (
              <p className="mt-2 text-xs text-slate-300/70">{copy.passwordHelp}</p>
            ) : null}
          </div>

          {mode === "register" ? (
            <div>
              <label className="mb-1 block text-xs font-bold uppercase tracking-[0.22em] text-slate-200/78">
                {copy.confirmPassword}
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="w-full rounded-xl border border-white/12 bg-white px-3 py-2.5 text-sm font-medium text-slate-950 placeholder:text-slate-500 focus:border-orange-DEFAULT focus:outline-none"
              />
            </div>
          ) : null}

          {message ? <p className="text-sm font-semibold text-emerald-300">{message}</p> : null}
          {error ? <p className="text-sm font-semibold text-red-400">{error}</p> : null}

          <Button
            variant="primary"
            size="lg"
            className="w-full !bg-[#F39200] hover:!bg-[#D97F00]"
            loading={submitting}
            onClick={mode === "signin" ? handleCredentialsSignIn : handleRegister}
          >
            {mode === "signin" ? copy.signIn : copy.createAccount}
          </Button>

          {googleEnabled ? (
            <Button
              variant="ghost"
              size="lg"
              className="w-full border border-white/18 bg-white/8 text-white hover:bg-white/12"
              onClick={handleGoogleSignIn}
            >
              {copy.google}
            </Button>
          ) : null}

          <button
            type="button"
            onClick={() => {
              setMode(mode === "signin" ? "register" : "signin");
              setError(null);
              setMessage(null);
              setConfirmPassword("");
            }}
            className="w-full text-center text-sm font-medium text-slate-200/80 hover:text-white"
          >
            {mode === "signin" ? copy.createMode : copy.existingMode}
          </button>
        </div>

        <p className="mt-6 text-center text-xs font-bold uppercase tracking-[0.18em] text-slate-300/55">
          {copy.powered}
        </p>
      </div>
    </main>
  );
}
