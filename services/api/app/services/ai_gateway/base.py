from typing import Protocol


class AIProvider(Protocol):
    name: str

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        ...
