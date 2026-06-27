export type TaskStatus = "pending" | "processing" | "done" | "failed";

export interface TaskResponse<TData = unknown> {
  taskId: string;
  status: TaskStatus;
  data: TData | null;
  error: string | null;
}
