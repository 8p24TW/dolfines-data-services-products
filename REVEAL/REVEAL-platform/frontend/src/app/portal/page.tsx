"use client";

import Link from "next/link";
import { useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { useDropzone } from "react-dropzone";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { BrandLockup } from "@/components/layout/BrandLockup";

interface PortalFormData {
  contactName: string;
  contactEmail: string;
  company: string;
  contractRef: string;
  notes: string;
  numSites: number;
  dataYear: number;
}

const YEARS = Array.from({ length: 8 }, (_, i) => 2019 + i);
const STEPS = ["Setup", "Contact", "Site Data", "Review & Submit"];

export default function PortalPage() {
  const [step, setStep] = useState(0);
  const [siteFiles, setSiteFiles] = useState<Record<number, { inverter: File[]; irradiance: File[]; other: File[] }>>({});
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const { register, handleSubmit, watch, formState: { errors } } = useForm<PortalFormData>({
    defaultValues: { numSites: 1, dataYear: new Date().getFullYear() - 1 },
  });
  const numSites = watch("numSites");

  function addFile(siteIdx: number, role: "inverter" | "irradiance" | "other", file: File) {
    setSiteFiles((prev) => ({
      ...prev,
      [siteIdx]: {
        ...(prev[siteIdx] ?? {}),
        inverter: prev[siteIdx]?.inverter ?? [],
        irradiance: prev[siteIdx]?.irradiance ?? [],
        other: prev[siteIdx]?.other ?? [],
        [role]: [...((prev[siteIdx]?.[role]) ?? []), file],
      },
    }));
  }

  async function onSubmit(data: PortalFormData) {
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("metadata", JSON.stringify(data));
      for (const [siteIdx, files] of Object.entries(siteFiles)) {
        const si = parseInt(siteIdx);
        files.inverter.forEach((f) => form.append(`site_${si}_inverter`, f));
        files.irradiance.forEach((f) => form.append(`site_${si}_irradiance`, f));
        files.other.forEach((f) => form.append(`site_${si}_other`, f));
      }
      await api.portal.submit(form);
      setSuccess(true);
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-navy-dark px-4">
        <div className="max-w-md text-center">
          <div className="text-4xl mb-4">✅</div>
          <h1 className="text-xl font-bold text-white mb-2">Submission Received</h1>
          <p className="text-sm text-slate-400">
            Your data package has been uploaded. The 8p2 team will be in touch.
          </p>
          <div className="mt-6">
            <Link href="/dashboard" className="text-sm font-medium text-orange-DEFAULT hover:text-orange-accent">
              Back to dashboard
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-navy-dark py-10 px-4">
      <div className="max-w-2xl mx-auto space-y-8">
        {/* Header */}
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-4 border-b border-navy-light/70 pb-4">
            <BrandLockup compact />
            <Link href="/dashboard" className="text-sm font-medium text-orange-DEFAULT transition-colors hover:text-orange-accent">
              Back to dashboard
            </Link>
          </div>
          <h1 className="text-2xl font-bold text-orange-DEFAULT">REVEAL · Data Submission Portal</h1>
          <p className="text-sm text-slate-400 mt-1">Submit your SCADA data for professional analysis</p>
        </div>

        {/* Step indicator */}
        <div className="flex gap-2">
          {STEPS.map((s, i) => (
            <div key={s} className={`flex-1 rounded-full h-1.5 ${i <= step ? "bg-orange-DEFAULT" : "bg-navy-light"}`} />
          ))}
        </div>
        <p className="text-xs text-slate-400">Step {step + 1} of {STEPS.length}: {STEPS[step]}</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Step 0: Setup */}
          {step === 0 && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Number of sites (1–5)</label>
                <input type="number" min={1} max={5} {...register("numSites", { min: 1, max: 5 })}
                  className="rounded bg-navy-DEFAULT border border-navy-light text-white text-sm px-3 py-1.5 w-24 focus:outline-none focus:border-orange-DEFAULT" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Data year</label>
                <select {...register("dataYear")}
                  className="rounded bg-navy-DEFAULT border border-navy-light text-white text-sm px-3 py-1.5 focus:outline-none focus:border-orange-DEFAULT">
                  {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
                </select>
              </div>
              <Button type="button" variant="primary" onClick={() => setStep(1)}>Next</Button>
            </div>
          )}

          {/* Step 1: Contact */}
          {step === 1 && (
            <div className="space-y-4">
              {[
                { label: "Contact name", field: "contactName" as const, required: true },
                { label: "Email", field: "contactEmail" as const, required: true },
                { label: "Company", field: "company" as const, required: true },
                { label: "Contract / PO reference", field: "contractRef" as const, required: false },
              ].map(({ label, field, required }) => (
                <div key={field}>
                  <label className="block text-xs text-slate-400 mb-1">{label}</label>
                  <input {...register(field, { required })}
                    className="w-full rounded bg-navy-DEFAULT border border-navy-light text-white text-sm px-3 py-1.5 focus:outline-none focus:border-orange-DEFAULT" />
                  {errors[field] && <p className="text-xs text-danger mt-0.5">Required</p>}
                </div>
              ))}
              <div>
                <label className="block text-xs text-slate-400 mb-1">Notes for analysis team</label>
                <textarea {...register("notes")} rows={3}
                  className="w-full rounded bg-navy-DEFAULT border border-navy-light text-white text-sm px-3 py-1.5 focus:outline-none focus:border-orange-DEFAULT" />
              </div>
              <div className="flex gap-2">
                <Button type="button" variant="ghost" onClick={() => setStep(0)}>Back</Button>
                <Button type="button" variant="primary" onClick={() => setStep(2)}>Next</Button>
              </div>
            </div>
          )}

          {/* Step 2: Site files */}
          {step === 2 && (
            <div className="space-y-6">
              {Array.from({ length: numSites }, (_, i) => (
                <SiteUploadSection key={i} index={i} onAdd={addFile} siteFiles={siteFiles[i] ?? { inverter: [], irradiance: [], other: [] }} />
              ))}
              <div className="flex gap-2">
                <Button type="button" variant="ghost" onClick={() => setStep(1)}>Back</Button>
                <Button type="button" variant="primary" onClick={() => setStep(3)}>Review</Button>
              </div>
            </div>
          )}

          {/* Step 3: Submit */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="rounded-lg border border-navy-light bg-navy-dark/40 p-4 text-sm text-slate-300 space-y-1">
                <p><span className="text-slate-400">Sites:</span> {numSites}</p>
                <p><span className="text-slate-400">Files per site:</span>{" "}
                  {Array.from({ length: numSites }, (_, i) =>
                    `Site ${i + 1}: ${(siteFiles[i]?.inverter.length ?? 0) + (siteFiles[i]?.irradiance.length ?? 0) + (siteFiles[i]?.other.length ?? 0)} file(s)`
                  ).join(", ")}
                </p>
              </div>
              <div className="flex gap-2">
                <Button type="button" variant="ghost" onClick={() => setStep(2)}>Back</Button>
                <Button type="submit" variant="primary" loading={submitting}>Submit package</Button>
              </div>
            </div>
          )}
        </form>
      </div>
    </main>
  );
}

function SiteUploadSection({
  index,
  onAdd,
  siteFiles,
}: {
  index: number;
  onAdd: (idx: number, role: "inverter" | "irradiance" | "other", file: File) => void;
  siteFiles: { inverter: File[]; irradiance: File[]; other: File[] };
}) {
  return (
    <div className="rounded-xl border border-navy-light bg-navy-DEFAULT/60 p-4 space-y-4">
      <h3 className="text-sm font-semibold text-white">Site {index + 1}</h3>
      {(["inverter", "irradiance", "other"] as const).map((role) => (
        <FileZone key={role} role={role} files={siteFiles[role]} onAdd={(f) => onAdd(index, role, f)} />
      ))}
    </div>
  );
}

function FileZone({
  role,
  files,
  onAdd,
}: {
  role: string;
  files: File[];
  onAdd: (f: File) => void;
}) {
  const onDrop = useCallback((accepted: File[]) => accepted.forEach(onAdd), [onAdd]);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, multiple: true });

  const labels: Record<string, string> = {
    inverter: "Inverter power CSVs",
    irradiance: "Irradiance CSV",
    other: "Other files (faults, grid, maintenance…)",
  };

  return (
    <div>
      <p className="text-xs text-slate-400 mb-1">{labels[role]}</p>
      <div
        {...getRootProps()}
        className={`rounded border-dashed border p-3 text-center cursor-pointer text-xs transition-colors ${isDragActive ? "border-orange-DEFAULT text-orange-DEFAULT" : "border-navy-light text-slate-500 hover:border-orange-DEFAULT/40"}`}
      >
        <input {...getInputProps()} />
        {files.length > 0
          ? files.map((f) => f.name).join(", ")
          : "Drop or click to add"}
      </div>
    </div>
  );
}
