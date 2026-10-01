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

  async ingestAlert(payload: Record<string, unknown>, idempotencyKey?: string) {
    const headers: Record<string, string> = {
      'X-API-Key': this.apiKey,
      'Content-Type': 'application/json',
    };
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
    const response = await fetch(`${this.baseUrl.replace(/\/$/, '')}/api/public/v1/alerts`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`NEXUS API error: ${response.status}`);
    return response.json() as Promise<Record<string, unknown>>;
  }
}
