export interface APIError {
  error: string;
  code: string;
  details: Record<string, unknown>;
}
