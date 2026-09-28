# NEXUS TypeScript SDK

Minimal client for the NEXUS Public API v1.

```ts
import { NexusClient } from "@nexus-ops/sdk";

const client = new NexusClient("https://nexus.example.com/api", "<api-key>");
const resources = await client.listResources();
const incidents = await client.listIncidents();
```

The client works in modern browser and Node.js runtimes that provide `fetch`.
