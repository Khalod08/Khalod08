import { useEffect, useState } from "react";
import {
  type BackgroundPreset,
  chooseBackgroundPreset,
  getBackgroundPresets,
  getJob,
  jobRenderVideoUrl,
  startRender,
  uploadBackground,
} from "../api";
import type { Job } from "../types";

export default function BackgroundAndRender({ job, onJobChange }: { job: Job; onJobChange: (j: Job) => void }) {
  const [presets, setPresets] = useState<BackgroundPreset[]>([]);
  const [busy, setBusy] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [pickedCount, setPickedCount] = useState(0);

  useEffect(() => {
    getBackgroundPresets().then(setPresets);
  }, []);

  useEffect(() => {
    const buildingBackground = job.background_status === "pending" || job.background_status === "rendering";
    const rendering = job.render_status === "pending" || job.render_status === "rendering";
    if (!buildingBackground && !rendering) return;
    const interval = window.setInterval(async () => {
      const updated = await getJob(job.id);
      onJobChange(updated);
    }, 1500);
    return () => window.clearInterval(interval);
  }, [job.id, job.background_status, job.render_status]);

  async function pickPreset(id: string) {
    setBusy(true);
    try {
      onJobChange(await chooseBackgroundPreset(job.id, id));
      setPickedCount(0);
    } finally {
      setBusy(false);
    }
  }

  async function pickUpload(files: File[]) {
    setBusy(true);
    setUploadError(null);
    try {
      onJobChange(await uploadBackground(job.id, files));
      setPickedCount(files.length);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function render() {
    onJobChange(await startRender(job.id));
  }

  const currentPreset = job.background?.startsWith("preset:") ? job.background.slice(7) : null;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 14,
        background: "#111116",
        border: "1px solid #26262e",
        borderRadius: 8,
        padding: 16,
      }}
    >
      <div style={{ fontWeight: 600 }}>Background</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {presets.map((p) => (
          <button
            key={p.id}
            onClick={() => pickPreset(p.id)}
            disabled={busy}
            style={{
              padding: "6px 14px",
              borderRadius: 6,
              border: currentPreset === p.id ? "2px solid #3b82f6" : "1px solid #3a3a48",
              background: "#1c1c24",
              color: "#f2f2f5",
              cursor: "pointer",
            }}
          >
            {p.label}
          </button>
        ))}
        <label
          style={{
            padding: "6px 14px",
            borderRadius: 6,
            border: job.background === "upload" ? "2px solid #3b82f6" : "1px solid #3a3a48",
            background: "#1c1c24",
            cursor: "pointer",
          }}
        >
          {pickedCount > 1 ? `${pickedCount}-image slideshow` : "Upload image(s) or a video…"}
          <input
            type="file"
            accept="image/*,video/*"
            multiple
            style={{ display: "none" }}
            onChange={(e) => {
              const files = Array.from(e.target.files ?? []);
              if (files.length > 0) pickUpload(files);
            }}
          />
        </label>
      </div>
      {uploadError && <span style={{ color: "#ff6b6b" }}>{uploadError}</span>}
      {(job.background_status === "pending" || job.background_status === "rendering") && (
        <span style={{ opacity: 0.7, fontSize: 13 }}>
          Building your {pickedCount}-image slideshow (crossfaded across the full track — this can take a
          minute or two)…
        </span>
      )}
      {job.background_status === "failed" && (
        <span style={{ color: "#ff6b6b" }}>Slideshow build failed: {job.background_error}</span>
      )}
      {job.background === "upload" && job.background_status === "done" && pickedCount > 1 && (
        <span style={{ opacity: 0.7, fontSize: 13 }}>
          Captions will play over a crossfaded slideshow of your {pickedCount} images, timed to the full track.
        </span>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button
          onClick={render}
          disabled={
            !job.background ||
            job.background_status === "pending" ||
            job.background_status === "rendering" ||
            job.render_status === "rendering" ||
            job.render_status === "pending"
          }
          style={{
            background: "#22c55e",
            color: "#0b0b0f",
            border: "none",
            borderRadius: 6,
            padding: "8px 18px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Render preview
        </button>
        {(job.render_status === "pending" || job.render_status === "rendering") && <span>Rendering…</span>}
        {job.render_status === "failed" && <span style={{ color: "#ff6b6b" }}>Render failed: {job.render_error}</span>}
      </div>

      {job.render_status === "done" && (
        <video controls style={{ maxWidth: 320, borderRadius: 8 }} src={jobRenderVideoUrl(job.id)} />
      )}
    </div>
  );
}
