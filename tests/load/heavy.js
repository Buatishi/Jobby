import http from "k6/http";
import { check, sleep } from "k6";

const API_URL = __ENV.API_URL || "http://localhost:8000";
const AUTH_TOKEN = __ENV.AUTH_TOKEN;
const ENABLE_HEAVY = __ENV.ENABLE_HEAVY === "true";

export const options = {
  scenarios: {
    ai_job_analysis: {
      executor: "ramping-vus",
      stages: [
        { duration: "20s", target: 1 },
        { duration: "40s", target: 3 },
        { duration: "40s", target: 5 },
        { duration: "20s", target: 0 }
      ]
    }
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<5000", "p(99)<10000"]
  }
};

function authHeaders() {
  return {
    headers: {
      Authorization: `Bearer ${AUTH_TOKEN}`,
      "Content-Type": "application/json"
    }
  };
}

export default function () {
  if (!ENABLE_HEAVY) {
    throw new Error("Set ENABLE_HEAVY=true to run AI-costing scenarios.");
  }
  if (!AUTH_TOKEN) {
    throw new Error("AUTH_TOKEN is required for heavy.js");
  }

  const payload = JSON.stringify({
    source: "text",
    raw_text:
      "Backend Engineer role requiring Python, FastAPI, PostgreSQL, Redis, APIs and async systems."
  });

  const analyze = http.post(
    `${API_URL}/api/v1/jobs/analyze`,
    payload,
    authHeaders()
  );
  check(analyze, {
    "job analysis accepted or gated clearly": (response) =>
      [202, 403, 429].includes(response.status)
  });

  sleep(2);
}

