"""Identificadores de tareas atados al usuario que las encoló.

El id tiene la forma ``<owner_id>.<prefijo>-<aleatorio>``. Solo el dueño puede consultar
el estado de su tarea y la parte aleatoria (128 bits) vuelve inviable adivinar un id.
"""

import uuid


def new_task_id(owner_id: str, prefix: str = "task") -> str:
    return f"{owner_id}.{prefix}-{uuid.uuid4().hex}"


def task_belongs_to(task_id: str, owner_id: str) -> bool:
    return bool(owner_id) and task_id.startswith(f"{owner_id}.")
