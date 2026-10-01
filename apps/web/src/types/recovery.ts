export interface RecoveryStatusDTO {
  ready: boolean;
  redis_pending: number;
  redis_dlq: number;
  queue_stream: string;
  queue_group: string;
  postgres_container: string;
  redis_container: string;
  backup_format: string;
}
