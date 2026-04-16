"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { BrandLockup } from "@/components/layout/BrandLockup";

export function ResetPasswordForm({ token }: { token: string }) {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setMessage(null);
    setError(null);

    if (!token) {
      setError("This reset link is missing its token.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });

      const payload = await response.json();
      if (!response.ok) {
        setError(payload.message ?? "Unable to reset password.");
        return;
      }

      setMessage(payload.message);
      setTimeout(() => router.push("/login"), 1200);
    } catch {
      setError("Unable to reset password right now.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-navy-dark px-4 py-10">
      <div className="absolute left-6 top-6">
        <BrandLockup href="/login" />
      </div>
      <div className="w-full max-w-md rounded-[28px] border border-white/12 bg-[rgba(3,20,31,0.82)] p-8 shadow-[0_32px_90px_rgba(0,0,0,0.35)] backdrop-blur-md">
        <h1 className="font-dolfines mt-4 text-3xl font-semibold tracking-[0.08em] text-white">
          Choose a New Password
        </h1>
        <p className="mt-3 text-sm text-slate-300/75">
          Set a new password for your registered REVEAL account.
        </p>

        <div className="mt-8 space-y-4">
          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-[0.22em] text-slate-200/78">
              New password
            </label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-xl border border-white/12 bg-white px-3 py-2.5 text-sm font-medium text-slate-950 placeholder:text-slate-500 focus:border-orange-DEFAULT focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-[0.22em] text-slate-200/78">
              Confirm password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              className="w-full rounded-xl border border-white/12 bg-white px-3 py-2.5 text-sm font-medium text-slate-950 placeholder:text-slate-500 focus:border-orange-DEFAULT focus:outline-none"
            />
          </div>

          {message ? <p className="text-sm font-semibold text-emerald-400">{message}</p> : null}
          {error ? <p className="text-sm font-semibold text-red-400">{error}</p> : null}

          <Button variant="primary" size="lg" className="w-full" loading={submitting} onClick={handleSubmit}>
            Update password
          </Button>

          <div className="text-center">
            <Link href="/login" className="text-sm font-medium text-slate-300 hover:text-white">
              Back to sign in
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
