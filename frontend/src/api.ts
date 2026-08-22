import type { Job, TranscriptionResult } from "./types";

export async function uploadForTranscription(file: File): Promise<Job> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/transcribe", { method: "POST", body: form });
  if (!res.ok) throw new Error(`upload failed: ${res.status}`);
  return res.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`/api/jobs/${jobId}`);
  if (!res.ok) throw new Error(`get job failed: ${res.status}`);
  return res.json();
}

export async function saveTranscript(jobId: string, transcript: TranscriptionResult): Promise<Job> {
  const res = await fetch(`/api/jobs/${jobId}/transcript`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(transcript),
  });
  if (!res.ok) throw new Error(`save transcript failed: ${res.status}`);
  return res.json();
}

export function jobAudioUrl(jobId: string): string {
  return `/api/jobs/${jobId}/audio`;
}

export function jobRenderVideoUrl(jobId: string): string {
  return `/api/jobs/${jobId}/render/video`;
}

export interface BackgroundPreset {
  id: string;
  label: string;
}

export async function getBackgroundPresets(): Promise<BackgroundPreset[]> {
  const res = await fetch("/api/backgrounds/presets");
  if (!res.ok) throw new Error(`get presets failed: ${res.status}`);
  return res.json();
}

export async function chooseBackgroundPreset(jobId: string, preset: string): Promise<Job> {
  const res = await fetch(`/api/jobs/${jobId}/background/preset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preset }),
  });
  if (!res.ok) throw new Error(`choose preset failed: ${res.status}`);
  return res.json();
}

export async function uploadBackground(jobId: string, file: File): Promise<Job> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`/api/jobs/${jobId}/background/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`upload background failed: ${res.status}`);
  return res.json();
}

export async function startRender(jobId: string): Promise<Job> {
  const res = await fetch(`/api/jobs/${jobId}/render`, { method: "POST" });
  if (!res.ok) throw new Error(`start render failed: ${res.status}`);
  return res.json();
}
