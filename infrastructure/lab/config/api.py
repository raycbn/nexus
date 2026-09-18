import json
import os
import sys
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

try:
    import psycopg2

    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

try:
    import redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


class LabHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _health(self) -> None:
        self._send_json(200, {"status": "healthy", "service": "linux-lab-api"})

    def _status(self) -> None:
        self._send_json(
            200,
            {
                "status": "running",
                "timestamp": datetime.now(UTC).isoformat(),
                "uptime_seconds": self.server.start_time,
                "version": "0.1.0",
            },
        )

    def _slow(self) -> None:
        params = parse_qs(urlparse(self.path).query)
        delay = float(params.get("seconds", ["2"])[0])
        delay = min(delay, 30.0)
        time.sleep(delay)
        self._send_json(
            200,
            {
                "status": "completed",
                "delay_seconds": delay,
                "message": f"Slept for {delay}s",
            },
        )

    def _error(self) -> None:
        self._send_json(
            500,
            {
                "error": "Intentional error for testing",
                "code": "LAB_ERROR_001",
                "message": "This endpoint always returns HTTP 500",
            },
        )

    def _db(self) -> None:
        if not HAS_POSTGRES:
            self._send_json(503, {"error": "psycopg2 not installed"})
            return

        host = os.environ.get("POSTGRES_HOST", "postgres")
        port = int(os.environ.get("POSTGRES_PORT", "5432"))
        user = os.environ.get("POSTGRES_USER", "labuser")
        password = os.environ.get("POSTGRES_PASSWORD", "labpassword")
        dbname = os.environ.get("POSTGRES_DB", "labdb")

        try:
            conn = psycopg2.connect(
                host=host, port=port, user=user, password=password, dbname=dbname, connect_timeout=5
            )
            cur = conn.cursor()
            cur.execute("SELECT 1 as ok, current_timestamp as now")
            row = cur.fetchone()
            cur.close()
            conn.close()
            self._send_json(
                200,
                {
                    "connected": True,
                    "postgres": "ok",
                    "host": f"{host}:{port}",
                    "database": dbname,
                    "checksum": row[0] if row else None,
                },
            )
        except Exception as e:
            self._send_json(
                503,
                {
                    "connected": False,
                    "postgres": "error",
                    "error": str(e),
                },
            )

    def _redis(self) -> None:
        if not HAS_REDIS:
            self._send_json(503, {"error": "redis not installed"})
            return

        host = os.environ.get("REDIS_HOST", "redis")
        port = int(os.environ.get("REDIS_PORT", "6379"))

        try:
            r = redis.Redis(host=host, port=port, socket_connect_timeout=5, socket_timeout=5)
            pong = r.ping()
            r.close()
            self._send_json(
                200,
                {
                    "connected": True,
                    "redis": "ok",
                    "host": f"{host}:{port}",
                    "ping": pong,
                },
            )
        except Exception as e:
            self._send_json(
                503,
                {
                    "connected": False,
                    "redis": "error",
                    "error": str(e),
                },
            )

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/health":
            self._health()
        elif path == "/api/status":
            self._status()
        elif path == "/api/slow":
            self._slow()
        elif path == "/api/error":
            self._error()
        elif path == "/api/db":
            self._db()
        elif path == "/api/redis":
            self._redis()
        else:
            self._send_json(404, {"error": "not found", "path": path})

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")


class LabServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()


def main() -> None:
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "5000"))
    server = LabServer((host, port), LabHandler)
    print(f"[api] Starting on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
