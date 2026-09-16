import type { AnalysisResult, Experiment, ExperimentCreate } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function listExperiments(): Promise<Experiment[]> {
  return request<Experiment[]>("/experiments");
}

export function createExperiment(payload: ExperimentCreate): Promise<Experiment> {
  return request<Experiment>("/experiments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function uploadImages(experimentId: string, files: FileList): Promise<void> {
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append("files", file));
  await request(`/experiments/${experimentId}/images`, {
    method: "POST",
    body: formData,
  });
}

export function analyzeExperiment(experimentId: string): Promise<AnalysisResult> {
  return request<AnalysisResult>(`/experiments/${experimentId}/analyze`, {
    method: "POST",
  });
}

