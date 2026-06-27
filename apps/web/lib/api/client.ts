import { createSupabaseBrowserClient } from "@/lib/supabase/client";

type ApiClientOptions = Omit<RequestInit, "headers"> & {
  headers?: HeadersInit;
};

export async function apiClient<TResponse>(
  path: string,
  options: ApiClientOptions = {}
): Promise<TResponse> {
  const { headers, ...requestOptions } = options;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const supabase = createSupabaseBrowserClient();
  const {
    data: { session }
  } = await supabase.auth.getSession();

  const response = await fetch(`${apiUrl}${path}`, {
    ...requestOptions,
    headers: {
      "Content-Type": "application/json",
      ...(session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {}),
      ...headers
    }
  });

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}.`);
  }

  return response.json() as Promise<TResponse>;
}
