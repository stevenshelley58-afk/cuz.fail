const DEFAULT_API_BASE_URL = "/api/v1";

export type ProbeName = "health" | "ready";

export type ApiProbeResult = {
  name: ProbeName;
  endpoint: "/health" | "/ready";
  url: string;
  ok: boolean;
  status: number | null;
  statusText: string;
  latencyMs: number;
  checkedAt: string;
  body: unknown;
  error: string | null;
};

export type ParserAccuracyReport = {
  demo_fixture_status: "passed" | "failed";
  beta_status: "not_beta_ready" | string;
  reason: string;
  expected_fact_count: number;
  extracted_fact_count: number;
  matched_fact_count: number;
  recall: number;
  precision: number;
  matched: string[];
  missing: string[];
  mismatched: unknown[];
  blocked_for_beta: string[];
};

type ProbeDefinition = {
  name: ProbeName;
  endpoint: ApiProbeResult["endpoint"];
};

const probes: Record<ProbeName, ProbeDefinition> = {
  health: { name: "health", endpoint: "/health" },
  ready: { name: "ready", endpoint: "/ready" },
};

function normalizeApiBaseUrl(rawBaseUrl: string | undefined): string {
  const trimmed = rawBaseUrl?.trim();
  return (trimmed && trimmed.length > 0 ? trimmed : DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const text = await response.text();

  if (!text) {
    return null;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return JSON.parse(text);
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.name === "AbortError" ? "Probe cancelled." : error.message;
  }

  return "Unable to reach the DraftCheck API.";
}

export class DraftCheckApiClient {
  readonly baseUrl: string;

  constructor(baseUrl = import.meta.env.VITE_API_BASE_URL) {
    this.baseUrl = normalizeApiBaseUrl(baseUrl);
  }

  health(signal?: AbortSignal): Promise<ApiProbeResult> {
    return this.probe(probes.health, signal);
  }

  ready(signal?: AbortSignal): Promise<ApiProbeResult> {
    return this.probe(probes.ready, signal);
  }

  async parserAccuracy(signal?: AbortSignal): Promise<ParserAccuracyReport> {
    const response = await fetch(`${this.baseUrl}/documents/parsers/accuracy`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal,
    });
    const body = await parseResponseBody(response);
    if (!response.ok) {
      throw new Error(`Parser accuracy check failed: HTTP ${response.status}`);
    }
    return body as ParserAccuracyReport;
  }

  private async probe(definition: ProbeDefinition, signal?: AbortSignal): Promise<ApiProbeResult> {
    const startedAt = performance.now();
    const url = `${this.baseUrl}${definition.endpoint}`;

    try {
      const response = await fetch(url, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
        signal,
      });
      const latencyMs = Math.round(performance.now() - startedAt);
      const body = await parseResponseBody(response);
      const statusText = response.statusText || (response.ok ? "OK" : "HTTP error");

      return {
        name: definition.name,
        endpoint: definition.endpoint,
        url,
        ok: response.ok,
        status: response.status,
        statusText,
        latencyMs,
        checkedAt: new Date().toISOString(),
        body,
        error: response.ok ? null : `HTTP ${response.status} ${statusText}`,
      };
    } catch (error) {
      return {
        name: definition.name,
        endpoint: definition.endpoint,
        url,
        ok: false,
        status: null,
        statusText: "Network error",
        latencyMs: Math.round(performance.now() - startedAt),
        checkedAt: new Date().toISOString(),
        body: null,
        error: errorMessage(error),
      };
    }
  }
}

export const apiClient = new DraftCheckApiClient();
