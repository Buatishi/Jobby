from collections.abc import Sequence

from app.services.ai_gateway.base import AIProvider
from app.services.ai_gateway.errors import ProviderUnavailableError
from app.services.ai_gateway.openai_embeddings import OpenAIEmbeddingsProvider


async def verify_ai_providers_available(
    providers: Sequence[AIProvider],
    embeddings_provider: OpenAIEmbeddingsProvider,
) -> None:
    for provider in providers:
        try:
            await provider.generate(
                prompt="Return ok.",
                system="Health check. Return only the word ok.",
                json_mode=False,
            )
        except Exception as exc:
            raise ProviderUnavailableError(provider.name) from exc

    try:
        await embeddings_provider.embed("health check")
    except Exception as exc:
        raise ProviderUnavailableError(embeddings_provider.name) from exc
