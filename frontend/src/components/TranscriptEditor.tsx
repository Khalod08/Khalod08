import { useEffect, useMemo, useRef, useState } from "react";
import type { Segment, TranscriptionResult, Word } from "../types";

const MIN_WORD_DURATION = 0.05;
const PX_PER_SECOND = 140;

interface WordRef {
  segIndex: number;
  wordIndex: number;
  word: Word;
}

function flatten(segments: Segment[]): WordRef[] {
  const out: WordRef[] = [];
  segments.forEach((seg, segIndex) => {
    seg.words.forEach((word, wordIndex) => out.push({ segIndex, wordIndex, word }));
  });
  return out;
}

type DragMode = "move" | "resize-start" | "resize-end";

interface DragState {
  mode: DragMode;
  flatIndex: number;
  pointerStartX: number;
  wordStart: number;
  wordEnd: number;
  lowerBound: number;
  upperBound: number;
}

export default function TranscriptEditor({
  transcript,
  audioUrl,
  onChange,
  onSave,
  saving,
}: {
  transcript: TranscriptionResult;
  audioUrl: string;
  onChange: (t: TranscriptionResult) => void;
  onSave: () => void;
  saving: boolean;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<DragState | null>(null);

  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");

  const flat = useMemo(() => flatten(transcript.segments), [transcript.segments]);
  const totalWidth = Math.max(600, transcript.duration * PX_PER_SECOND + 200);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onTime = () => setCurrentTime(audio.currentTime);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    audio.addEventListener("timeupdate", onTime);
    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onPause);
    return () => {
      audio.removeEventListener("timeupdate", onTime);
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onPause);
    };
  }, []);

  function updateWord(flatIndex: number, patch: Partial<Word>) {
    const ref = flat[flatIndex];
    const nextSegments = transcript.segments.map((seg, si) => {
      if (si !== ref.segIndex) return seg;
      return {
        ...seg,
        words: seg.words.map((w, wi) => (wi === ref.wordIndex ? { ...w, ...patch } : w)),
      };
    });
    onChange({ ...transcript, segments: nextSegments });
  }

  function beginDrag(mode: DragMode, flatIndex: number, e: React.PointerEvent) {
    e.stopPropagation();
    const ref = flat[flatIndex];
    const prevEnd = flatIndex > 0 ? flat[flatIndex - 1].word.end : 0;
    const nextStart = flatIndex < flat.length - 1 ? flat[flatIndex + 1].word.start : transcript.duration;
    dragRef.current = {
      mode,
      flatIndex,
      pointerStartX: e.clientX,
      wordStart: ref.word.start,
      wordEnd: ref.word.end,
      lowerBound: prevEnd,
      upperBound: nextStart,
    };
    window.addEventListener("pointermove", onDragMove);
    window.addEventListener("pointerup", onDragEnd);
  }

  function onDragMove(e: PointerEvent) {
    const drag = dragRef.current;
    if (!drag) return;
    const dx = (e.clientX - drag.pointerStartX) / PX_PER_SECOND;
    const duration = drag.wordEnd - drag.wordStart;

    if (drag.mode === "move") {
      let newStart = drag.wordStart + dx;
      newStart = Math.max(drag.lowerBound, Math.min(newStart, drag.upperBound - duration));
      updateWord(drag.flatIndex, { start: round3(newStart), end: round3(newStart + duration) });
    } else if (drag.mode === "resize-start") {
      let newStart = drag.wordStart + dx;
      newStart = Math.max(drag.lowerBound, Math.min(newStart, drag.wordEnd - MIN_WORD_DURATION));
      updateWord(drag.flatIndex, { start: round3(newStart) });
    } else {
      let newEnd = drag.wordEnd + dx;
      newEnd = Math.min(drag.upperBound, Math.max(newEnd, drag.wordStart + MIN_WORD_DURATION));
      updateWord(drag.flatIndex, { end: round3(newEnd) });
    }
  }

  function onDragEnd() {
    dragRef.current = null;
    window.removeEventListener("pointermove", onDragMove);
    window.removeEventListener("pointerup", onDragEnd);
  }

  function round3(n: number) {
    return Math.round(n * 1000) / 1000;
  }

  function seekTo(seconds: number) {
    if (audioRef.current) audioRef.current.currentTime = seconds;
    setCurrentTime(seconds);
  }

  function togglePlay() {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) audio.play();
    else audio.pause();
  }

  function startEdit(flatIndex: number) {
    const ref = flat[flatIndex];
    setEditingKey(`${ref.segIndex}-${ref.wordIndex}`);
    setEditingText(ref.word.text);
  }

  function commitEdit(flatIndex: number) {
    updateWord(flatIndex, { text: editingText });
    setEditingKey(null);
  }

  const activeFlatIndex = flat.findIndex((r) => currentTime >= r.word.start && currentTime < r.word.end);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <audio ref={audioRef} src={audioUrl} preload="metadata" />

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button onClick={togglePlay} style={btnStyle}>
          {isPlaying ? "Pause" : "Play"}
        </button>
        <span style={{ fontVariantNumeric: "tabular-nums", opacity: 0.8 }}>
          {currentTime.toFixed(2)}s / {transcript.duration.toFixed(2)}s
        </span>
        <div style={{ flex: 1 }} />
        <button onClick={onSave} disabled={saving} style={{ ...btnStyle, background: "#3b82f6" }}>
          {saving ? "Saving…" : "Save corrections"}
        </button>
      </div>

      {/* Live caption-style preview so edits are easy to sanity check */}
      <div
        style={{
          background: "#0b0b0f",
          border: "1px solid #26262e",
          borderRadius: 12,
          padding: "28px 16px",
          textAlign: "center",
          fontSize: 28,
          fontWeight: 700,
          minHeight: 40,
        }}
      >
        {activeFlatIndex >= 0 ? (
          <span style={{ color: "#ffce33" }}>{flat[activeFlatIndex].word.text}</span>
        ) : (
          <span style={{ opacity: 0.3 }}>—</span>
        )}
      </div>

      {/* Timeline: drag body to retime, drag edges to trim */}
      <div
        ref={timelineRef}
        onPointerDown={(e) => {
          const rect = timelineRef.current!.getBoundingClientRect();
          const x = e.clientX - rect.left + timelineRef.current!.scrollLeft;
          seekTo(Math.max(0, x / PX_PER_SECOND));
        }}
        style={{
          position: "relative",
          overflowX: "auto",
          background: "#111116",
          border: "1px solid #26262e",
          borderRadius: 8,
          height: 90,
        }}
      >
        <div style={{ position: "relative", width: totalWidth, height: "100%" }}>
          {flat.map((ref, i) => {
            const key = `${ref.segIndex}-${ref.wordIndex}`;
            const left = ref.word.start * PX_PER_SECOND;
            const width = Math.max(6, (ref.word.end - ref.word.start) * PX_PER_SECOND);
            const active = i === activeFlatIndex;
            return (
              <div
                key={key}
                onPointerDown={(e) => beginDrag("move", i, e)}
                title={ref.word.text}
                style={{
                  position: "absolute",
                  left,
                  width,
                  top: 12,
                  height: 66,
                  background: active ? "#ffce33" : "#2b2b38",
                  border: "1px solid #3a3a48",
                  borderRadius: 6,
                  cursor: "grab",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  overflow: "hidden",
                  fontSize: 12,
                  color: active ? "#111" : "#e5e5ea",
                  userSelect: "none",
                }}
              >
                <div
                  onPointerDown={(e) => beginDrag("resize-start", i, e)}
                  style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 6, cursor: "ew-resize" }}
                />
                <span style={{ padding: "0 4px", whiteSpace: "nowrap" }}>{ref.word.text}</span>
                <div
                  onPointerDown={(e) => beginDrag("resize-end", i, e)}
                  style={{ position: "absolute", right: 0, top: 0, bottom: 0, width: 6, cursor: "ew-resize" }}
                />
              </div>
            );
          })}
          <div
            style={{
              position: "absolute",
              left: currentTime * PX_PER_SECOND,
              top: 0,
              bottom: 0,
              width: 2,
              background: "#ff4d6d",
              pointerEvents: "none",
            }}
          />
        </div>
      </div>

      {/* Flowing transcript text: click a word to fix a typo */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "0.35em",
          lineHeight: 1.8,
          fontSize: 18,
          background: "#111116",
          border: "1px solid #26262e",
          borderRadius: 8,
          padding: 16,
        }}
      >
        {flat.map((ref, i) => {
          const key = `${ref.segIndex}-${ref.wordIndex}`;
          const active = i === activeFlatIndex;
          if (editingKey === key) {
            return (
              <input
                key={key}
                autoFocus
                value={editingText}
                onChange={(e) => setEditingText(e.target.value)}
                onBlur={() => commitEdit(i)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitEdit(i);
                  if (e.key === "Escape") setEditingKey(null);
                }}
                style={{
                  width: `${Math.max(2, editingText.length)}ch`,
                  background: "#1c1c24",
                  border: "1px solid #3b82f6",
                  borderRadius: 4,
                  color: "#fff",
                  padding: "1px 4px",
                  font: "inherit",
                }}
              />
            );
          }
          return (
            <span
              key={key}
              onClick={() => startEdit(i)}
              onDoubleClick={() => seekTo(ref.word.start)}
              title="Click to edit text, double-click to seek"
              style={{
                cursor: "text",
                padding: "1px 3px",
                borderRadius: 4,
                background: active ? "#ffce33" : "transparent",
                color: active ? "#111" : "#e5e5ea",
              }}
            >
              {ref.word.text}
            </span>
          );
        })}
      </div>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  background: "#26262e",
  color: "#f2f2f5",
  border: "none",
  borderRadius: 6,
  padding: "8px 16px",
  cursor: "pointer",
  fontSize: 14,
};
