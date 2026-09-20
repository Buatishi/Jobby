import http from "k6/http";
import { check, sleep } from "k6";

const FRONTEND_URL = __ENV.FRONTEND_URL || "http://localhost:3000";
const API_URL = __ENV.API_URL || "http://localhost:8000";
const AUTH_TOKEN = __ENV.AUTH_TOKEN;

export const options = {
  scenarios: {
    authenticated_reads: {
      executor: "ramping-vus",
      stages: [
        { duration: "30s", target: 1 },
        { duration: "30s", target: 5 },
        { duration: "30s", target: 10 },
        { duration: "30s", target: 15 },
        { duration: "30s", target: 0 }
      ]
    }
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000", "p(99)<4000"]
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
  if (!AUTH_TOKEN) {
    throw new Error("AUTH_TOKEN is required for medium.js");
  }

  const dashboardPage = http.get(`${FRONTEND_URL}/dashboard`);
  check(dashboardPage, {
    "dashboard page responds": (response) =>
      response.status === 200 || response.status === 307
  });

  const summary = http.get(`${API_URL}/api/v1/dashboard/summary`, authHeaders());
  check(summary, {
    "dashboard summary succeeds": (response) => response.status === 200
  });

  const profile = http.get(`${API_URL}/api/v1/profiles/me`, authHeaders());
  check(profile, {
    "profile succeeds": (response) => response.status === 200
  });

  const jobs = http.get(`${API_URL}/api/v1/jobs`, authHeaders());
  check(jobs, {
    "jobs succeeds": (response) => response.status === 200
  });

  sleep(1);
}

