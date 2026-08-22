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
