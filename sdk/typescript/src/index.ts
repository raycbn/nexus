export type NexusResource = {
  id: string;
  name: string;
  resource_type: string;
  environment: string;
  enabled: boolean;
};

export type NexusIncident = {
  id: string;
  title: string;
  status: string;
  severity: string;
};

export class NexusClient {
  constructor(
    private readonly baseUrl: string,
    private readonly apiKey: string,
  ) {}

  private async request<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl.replace(/\/$/, "")}/${path.replace(/^\//, "")}`, {
      headers: { Accept: "application/json", "X-API-Key": this.apiKey },
    });
    if (!response.ok) throw new Error(`NEXUS API error ${response.status}`);
    return response.json() as Promise<T>;
  }

  listResources(): Promise<NexusResource[]> {
    return this.request("public/v1/resources");
  }

  listIncidents(): Promise<NexusIncident[]> {
    return this.request("public/v1/incidents");
  }
}
