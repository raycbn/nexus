export class NexusClient {
  constructor(private readonly baseUrl: string, private readonly apiKey: string) {}

  private async get<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl.replace(/\/$/, '')}/api/public/v1${path}`, {
      headers: { 'X-API-Key': this.apiKey },
    });
    if (!response.ok) throw new Error(`NEXUS API error: ${response.status}`);
    return response.json() as Promise<T>;
  }

  resources() {
    return this.get<Array<Record<string, unknown>>>('/resources');
  }

  incidents() {
    return this.get<Array<Record<string, unknown>>>('/incidents');
  }
}
