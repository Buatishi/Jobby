class AIGatewayError(Exception):
    pass


class ProviderUnavailableError(AIGatewayError):
    def __init__(self, provider: str, message: str | None = None) -> None:
        self.provider = provider
        super().__init__(message or f"{provider} is unavailable.")


class ProviderQuotaExceededError(ProviderUnavailableError):
    """La cuenta del proveedor no tiene saldo: otro intento falla igual."""


class PremiumRequiredError(AIGatewayError):
    def __init__(self, task_type: str) -> None:
        self.task_type = task_type
        super().__init__(f"{task_type} requires a premium subscription.")
