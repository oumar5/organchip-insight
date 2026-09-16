import type {
  AnalysisEngine,
  AnalysisResult,
  Experiment,
  ExperimentCreate,
  UploadSummary,
  UploadLimits,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = payload?.detail;
    const message = typeof detail === "string" ? detail : Array.isArray(detail)
      ? detail.map((item) => `${item.loc?.slice(1).join(".") ?? "Champ"} : ${item.msg ?? "Valeur invalide"}`).join(" ; ")
      : response.status === 413 ? "Fichier trop volumineux pour le serveur."
        : `La requête a échoué (HTTP ${response.status}).`;
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function listExperiments(): Promise<Experiment[]> {
  return request<Experiment[]>("/experiments");
}

export function listInferenceEngines(): Promise<AnalysisEngine[]> {
  return request<AnalysisEngine[]>("/inference/engines");
}

export function createExperiment(payload: ExperimentCreate): Promise<Experiment> {
  return request<Experiment>("/experiments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getUploadLimits(): Promise<UploadLimits> {
  return request<UploadLimits>("/inference/upload-limits");
}

export async function uploadImage(experimentId: string, file: File): Promise<UploadSummary> {
  const formData = new FormData();
  formData.append("files", file);
  return request<UploadSummary>(`/experiments/${experimentId}/images`, {
    method: "POST",
    body: formData,
  });
}

export function analyzeExperiment(
  experimentId: string,
  engineId: string,
): Promise<AnalysisResult> {
  const query = new URLSearchParams({ engine_id: engineId });
  return request<AnalysisResult>(`/experiments/${experimentId}/analyze?${query}`, {
    method: "POST",
  });
}

export function getExperimentResults(experimentId: string): Promise<AnalysisResult> {
  return request<AnalysisResult>(`/experiments/${experimentId}/results`);
}
