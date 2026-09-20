import http from "k6/http";
import { check, sleep } from "k6";

const FRONTEND_URL = __ENV.FRONTEND_URL || "http://localhost:3000";
const API_URL = __ENV.API_URL || "http://localhost:8000";

export const options = {
  scenarios: {
    light_navigation: {
      executor: "ramping-vus",
      stages: [
        { duration: "30s", target: 1 },
        { duration: "30s", target: 5 },
        { duration: "30s", target: 10 },
        { duration: "30s", target: 20 },
        { duration: "30s", target: 0 }
      ]
    }
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1500", "p(99)<3000"]
  }
};

export default function () {
  const landing = http.get(`${FRONTEND_URL}/`);
  check(landing, {
    "landing is available": (response) => response.status === 200
  });

  const pricing = http.get(`${FRONTEND_URL}/pricing`);
  check(pricing, {
    "pricing is available": (response) =>
      response.status === 200 || response.status === 307
  });

  const health = http.get(`${API_URL}/health`);
  check(health, {
    "backend health is ok": (response) =>
      response.status === 200 && response.body.includes("ok")
  });

  sleep(1);
}

