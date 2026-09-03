import { useEffect, useState } from "react";
import { type ExportOptions, getExportOptions, getJob, jobExportVideoUrl, startExport } from "../api";
import type { Job } from "../types";

const RESOLUTION_LABELS: Record<string, string> = {
  "1080p": "1080×1920 (HD)",
  "1440p": "1440×2560 (QHD)",
  "4k": "2160×3840 (4K)",
};

const CODEC_LABELS: Record<string, string> = {
  h264: "H.264",
  h265: "H.265 (HEVC)",
};

export default function ExportPanel({ job, onJobChange }: { job: Job; onJobChange: (j: Job) => void }) {
  const [options, setOptions] = useState<ExportOptions>({ resolutions: [], codecs: [] });
  const [resolution, setResolution] = useState("1080p");
  const [codec, setCodec] = useState("h264");

  useEffect(() => {
    getExportOptions().then(setOptions);
  }, []);

  useEffect(() => {
    if (job.export_status !== "pending" && job.export_status !== "rendering") return;
    const interval = window.setInterval(async () => {
      onJobChange(await getJob(job.id));
    }, 2000);
    return () => window.clearInterval(interval);
  }, [job.id, job.export_status]);

  async function runExport() {
    onJobChange(await startExport(job.id, resolution, codec));
  }

  const busy = job.export_status === "pending" || job.export_status === "rendering";

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
      <div style={{ fontWeight: 600 }}>Export</div>
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Resolution
          <select value={resolution} onChange={(e) => setResolution(e.target.value)} style={selectStyle}>
            {options.resolutions.map((r) => (
              <option key={r} value={r}>
                {RESOLUTION_LABELS[r] ?? r}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Codec
          <select value={codec} onChange={(e) => setCodec(e.target.value)} style={selectStyle}>
            {options.codecs.map((c) => (
              <option key={c} value={c}>
                {CODEC_LABELS[c] ?? c}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button
          onClick={runExport}
          disabled={
            !job.background ||
            job.background_status === "pending" ||
            job.background_status === "rendering" ||
            busy
          }
          style={{
            background: "#a855f7",
            color: "#0b0b0f",
            border: "none",
            borderRadius: 6,
            padding: "8px 18px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Export final video
        </button>
        {busy && <span>Encoding at export quality (slower than the preview render)…</span>}
        {job.export_status === "failed" && <span style={{ color: "#ff6b6b" }}>Export failed: {job.export_error}</span>}
      </div>

      {job.export_status === "done" && (
        <a
          href={jobExportVideoUrl(job.id)}
          download={`lyric-video-${job.id}.mp4`}
          style={{ color: "#a855f7", fontWeight: 600 }}
        >
          Download {RESOLUTION_LABELS[job.export_resolution ?? ""] ?? job.export_resolution} {job.export_codec?.toUpperCase()} export
        </a>
      )}
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  background: "#1c1c24",
  color: "#f2f2f5",
  border: "1px solid #3a3a48",
  borderRadius: 6,
  padding: "6px 10px",
};
