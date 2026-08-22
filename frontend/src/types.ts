export interface Word {
  text: string;
  start: number;
  end: number;
  score?: number | null;
}

export interface Segment {
  text: string;
  start: number;
  end: number;
  words: Word[];
}

export interface TranscriptionResult {
  language: string;
  duration: number;
  segments: Segment[];
}

export type JobStatus =
  | "pending"
  | "extracting_audio"
  | "transcribing"
  | "aligning"
  | "done"
  | "failed";

export type RenderStatus = "pending" | "rendering" | "done" | "failed";

export interface Job {
  id: string;
  status: JobStatus;
  filename: string;
  error?: string | null;
  result?: TranscriptionResult | null;
  background?: string | null;
  render_status?: RenderStatus | null;
  render_error?: string | null;
}
