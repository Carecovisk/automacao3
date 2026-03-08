"""Exceptions specific to Gemini API interactions."""


class MissingGeminiApiKeyError(Exception):
    """Raised when the Gemini API key is not configured or is missing."""

    def __init__(self):
        message = (
            "Chave da API do Gemini não configurada. "
            "Por favor, defina a chave da API na página de configuração"
            "ou desabilite as funcionalidades de IA."
        )
        super().__init__(message)
