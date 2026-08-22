import { useEffect, useRef, useState } from "react";
import TranscriptEditor from "./components/TranscriptEditor";
import BackgroundAndRender from "./components/BackgroundAndRender";
import { getJob, jobAudioUrl, saveTranscript, uploadForTranscription } from "./api";
import type { Job, TranscriptionResult } from "./types";

const POLL_MS = 1500;

export default function App() {
  const [job, setJob] = useState<Job | null>(null);
  const [transcript, setTranscript] = useState<TranscriptionResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    const existingJobId = new URLSearchParams(window.location.search).get("job");
    if (existingJobId) {
      getJob(existingJobId).then((j) => {
        setJob(j);
        if (j.result) setTranscript(j.result);
      });
    }
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  async function handleFile(file: File) {
    setUploadError(null);
    setTranscript(null);
    try {
      const created = await uploadForTranscription(file);
      setJob(created);
      pollRef.current = window.setInterval(async () => {
        const updated = await getJob(created.id);
        setJob(updated);
        if (updated.result) {
          setTranscript(updated.result);
        }
        if (updated.status === "done" || updated.status === "failed") {
          if (pollRef.current) window.clearInterval(pollRef.current);
        }
      }, POLL_MS);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleSave() {
    if (!job || !transcript) return;
    setSaving(true);
    try {
      await saveTranscript(job.id, transcript);
    } finally {
      setSaving(false);
    }
  }

  const busy = job && !transcript && job.status !== "failed";

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2.5rem", maxWidth: 960, margin: "0 auto" }}>
      <h1 style={{ marginBottom: 4 }}>Lyric Video Generator</h1>
      <p style={{ opacity: 0.7, marginTop: 0 }}>Upload audio or video, review the detected lyrics, then fix anything before rendering.</p>

      <div style={{ margin: "1.5rem 0" }}>
        <input
          type="file"
          accept="audio/*,video/*"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
      </div>

      {uploadError && <p style={{ color: "#ff6b6b" }}>{uploadError}</p>}

      {busy && (
        <p style={{ opacity: 0.7 }}>
          {job!.status.replace("_", " ")}… (Whisper transcription is CPU-bound and can take a while on longer files)
        </p>
      )}

      {job?.status === "failed" && !transcript && (
        <p style={{ color: "#ff6b6b" }}>Pipeline failed: {job.error}</p>
      )}

      {job && transcript && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <TranscriptEditor
            transcript={transcript}
            audioUrl={jobAudioUrl(job.id)}
            onChange={setTranscript}
            onSave={handleSave}
            saving={saving}
          />
          <BackgroundAndRender job={job} onJobChange={setJob} />
        </div>
      )}
    </main>
  );
}
