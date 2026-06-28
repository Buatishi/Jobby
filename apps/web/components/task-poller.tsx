"use client";

import { useEffect } from "react";

import { apiStream } from "@/lib/api/client";

type TaskStatus = "pending" | "processing" | "done" | "failed";

type TaskResponse = {
  task_id: string;
  status: TaskStatus;
  result: unknown;
  error: string | null;
};

type TaskPollerProps = {
  taskId: string | null;
  onComplete: () => void;
  onFail: (message: string) => void;
};

export function TaskPoller({ taskId, onComplete, onFail }: TaskPollerProps) {
  useEffect(() => {
    if (!taskId) {
      return;
    }

    let cancelled = false;

    void apiStream(`/api/v1/tasks/${taskId}/stream`, (message) => {
      if (cancelled) {
        return;
      }

      const task = JSON.parse(message) as TaskResponse;
      if (task.status === "done") {
        onComplete();
      }
      if (task.status === "failed") {
        onFail(task.error ?? "No se pudo completar el análisis.");
      }
    }).catch((error: unknown) => {
      if (!cancelled) {
        onFail(error instanceof Error ? error.message : "No se pudo leer el task.");
      }
    });

    return () => {
      cancelled = true;
    };
  }, [onComplete, onFail, taskId]);

  return null;
}
