import { createSupabaseBrowserClient } from "@/lib/supabase/client";

type ApiClientOptions = Omit<RequestInit, "headers"> & {
  headers?: HeadersInit;
};

export class ApiAuthenticationError extends Error {
  constructor(message = "Tu sesión expiró. Volvé a iniciar sesión.") {
    super(message);
    this.name = "ApiAuthenticationError";
  }
}

async function getSessionAccessToken(forceRefresh = false) {
  const supabase = createSupabaseBrowserClient();

  if (forceRefresh) {
    const {
      data: { session }
    } = await supabase.auth.refreshSession();

    return session?.access_token;
  }

  const {
    data: { session }
  } = await supabase.auth.getSession();

  return session?.access_token;
}

async function getAuthHeaders(headers?: HeadersInit, forceRefresh = false) {
  const accessToken = await getSessionAccessToken(forceRefresh);

  return {
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    ...headers
  };
}

function getApiUrl() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  if (apiUrl) {
    return apiUrl;
  }

  if (process.env.NODE_ENV === "production") {
    throw new Error("Missing NEXT_PUBLIC_API_URL.");
  }

  return "http://localhost:8000";
}

async function redirectToLoginAfterAuthFailure() {
  const supabase = createSupabaseBrowserClient();
  await supabase.auth.signOut();

  if (typeof window !== "undefined") {
    const nextPath = `${window.location.pathname}${window.location.search}`;
    const loginUrl = new URL("/login", window.location.origin);
    loginUrl.searchParams.set("next", nextPath);
    loginUrl.searchParams.set("error", "session-expired");
    window.location.assign(loginUrl.toString());
  }
}

async function parseApiError(response: Response) {
  const errorPayload = (await response.json().catch(() => null)) as {
    error?: string;
    detail?: { error?: string };
  } | null;

  return (
    errorPayload?.error ??
    errorPayload?.detail?.error ??
    `API request failed with status ${response.status}.`
  );
}

export async function apiClient<TResponse>(
  path: string,
  options: ApiClientOptions = {}
): Promise<TResponse> {
  const { headers, ...requestOptions } = options;
  const apiUrl = getApiUrl();

  async function sendRequest(forceRefresh = false) {
    const authHeaders = await getAuthHeaders(headers, forceRefresh);

    return fetch(`${apiUrl}${path}`, {
      ...requestOptions,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders
      }
    });
  }

  let response = await sendRequest();

  if (response.status === 401) {
    response = await sendRequest(true);
    if (response.status === 401) {
      await redirectToLoginAfterAuthFailure();
      throw new ApiAuthenticationError();
    }
  }

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  return response.json() as Promise<TResponse>;
}

export async function apiStream(
  path: string,
  onMessage: (message: string) => void
) {
  const apiUrl = getApiUrl();
  async function openStream(forceRefresh = false) {
    return fetch(`${apiUrl}${path}`, {
      headers: await getAuthHeaders({ Accept: "text/event-stream" }, forceRefresh)
    });
  }

  let response = await openStream();

  if (response.status === 401) {
    response = await openStream(true);
    if (response.status === 401) {
      await redirectToLoginAfterAuthFailure();
      throw new ApiAuthenticationError();
    }
  }

  if (!response.ok || !response.body) {
    throw new Error(`API stream failed with status ${response.status}.`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const event of events) {
      const dataLine = event
        .split("\n")
        .find((line) => line.startsWith("data: "));
      if (dataLine) {
        onMessage(dataLine.slice(6));
      }
    }
  }
}
