import { createSupabaseBrowserClient } from "@/lib/supabase/client";

type ApiClientOptions = Omit<RequestInit, "headers"> & {
  headers?: HeadersInit;
};

async function getAuthHeaders(headers?: HeadersInit) {
  const supabase = createSupabaseBrowserClient();
  const {
    data: { session }
  } = await supabase.auth.getSession();

  return {
    ...(session?.access_token
      ? { Authorization: `Bearer ${session.access_token}` }
      : {}),
    ...headers
  };
}

export async function apiClient<TResponse>(
  path: string,
  options: ApiClientOptions = {}
): Promise<TResponse> {
  const { headers, ...requestOptions } = options;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const authHeaders = await getAuthHeaders(headers);

  const response = await fetch(`${apiUrl}${path}`, {
    ...requestOptions,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders
    }
  });

  if (!response.ok) {
    const errorPayload = (await response.json().catch(() => null)) as {
      error?: string;
      detail?: { error?: string };
    } | null;
    throw new Error(
      errorPayload?.error ??
        errorPayload?.detail?.error ??
        `API request failed with status ${response.status}.`
    );
  }

  return response.json() as Promise<TResponse>;
}

export async function apiStream(
  path: string,
  onMessage: (message: string) => void
) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const response = await fetch(`${apiUrl}${path}`, {
    headers: await getAuthHeaders({ Accept: "text/event-stream" })
  });

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
