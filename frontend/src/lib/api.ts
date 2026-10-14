export type CapabilityStatus = 'implemented' | 'planned' | 'mocked';

export interface Capability {
  id: string;
  title: string;
  phase: number;
  status: CapabilityStatus;
  description: string;
}

export interface CapabilitiesResponse {
  project: string;
  current_phase: number;
  capabilities: Capability[];
}

export interface ArchitectureLayer {
  name: string;
  modules: string[];
  status: CapabilityStatus;
}

export interface ArchitectureResponse {
  version: string;
  architecture: string;
  layers: ArchitectureLayer[];
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal, headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`API unavailable (HTTP ${response.status})`);
  return response.json() as Promise<T>;
}

export const api = {
  health: (signal?: AbortSignal) => getJson<{ service: string; status: string; version: string }>('/api/v1/health', signal),
  capabilities: (signal?: AbortSignal) => getJson<CapabilitiesResponse>('/api/v1/capabilities', signal),
  architecture: (signal?: AbortSignal) => getJson<ArchitectureResponse>('/api/v1/architecture', signal),
};
