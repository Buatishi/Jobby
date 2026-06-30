import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    job_analysis: {
      executor: "constant-vus",
      vus: 100,
      duration: "1m",
      exec: "jobAnalysis"
    },
    interview_kits: {
      executor: "constant-vus",
      vus: 20,
      duration: "1m",
      exec: "interviewKit"
    }
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<30000"]
  }
};

const API_URL = __ENV.API_URL || "http://localhost:8000";
const TOKEN = __ENV.AUTH_TOKEN || "";

const headers = {
  "Content-Type": "application/json",
  Authorization: `Bearer ${TOKEN}`
};

export function jobAnalysis() {
  const response = http.post(
    `${API_URL}/api/v1/jobs/analyze`,
    JSON.stringify({
      source: "text",
      raw_text: "Senior Python FastAPI role with PostgreSQL and Redis."
    }),
    { headers, timeout: "35s" }
  );
  check(response, {
    "job analysis accepted or rate limited": (res) =>
      [202, 403, 429].includes(res.status)
  });
  sleep(1);
}

export function interviewKit() {
  const response = http.post(
    `${API_URL}/api/v1/interview-kits`,
    JSON.stringify({
      job_id: __ENV.JOB_ID || "00000000-0000-0000-0000-000000000000",
      company_linkedin_url: "https://www.linkedin.com/company/acme",
      interviewer_linkedin_url: "https://www.linkedin.com/in/jane-doe"
    }),
    { headers, timeout: "35s" }
  );
  check(response, {
    "kit accepted gated or rate limited": (res) =>
      [202, 403, 404, 429].includes(res.status)
  });
  sleep(1);
}
