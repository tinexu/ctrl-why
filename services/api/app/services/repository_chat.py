from typing import Protocol

from openai import OpenAI
from pydantic import SecretStr

from app.domain.indexing import (
    ChatCitation,
    ChatMessage,
    RepositoryChatResponse,
)
from app.services.repository_indexing import RepositoryIndexingService


class ChatConfigurationError(RuntimeError):
    pass


class ChatProviderError(RuntimeError):
    pass


class ResponsesClient(Protocol):
    def create(self, **kwargs: object) -> object: ...


class RepositoryChatService:
    def __init__(
        self,
        indexing: RepositoryIndexingService,
        api_key: SecretStr | None,
        model: str,
        client: ResponsesClient | None = None,
    ) -> None:
        self._indexing = indexing
        self._api_key = api_key
        self._model = model
        self._client = client

    def ask(
        self,
        workspace_id: str,
        question: str,
        history: list[ChatMessage],
    ) -> RepositoryChatResponse:
        search = self._indexing.search(workspace_id, question, limit=6)
        if not search.results:
            return RepositoryChatResponse(
                workspace_id=workspace_id,
                answer="I could not find enough repository evidence to answer that question.",
                citations=[],
                sources=[],
            )

        evidence = "\n\n".join(
            f"[{number}] {result.path}:{result.start_line}-{result.end_line}"
            f"{f' ({result.symbol})' if result.symbol else ''}\n{result.excerpt}"
            for number, result in enumerate(search.results, start=1)
        )
        conversation = "\n".join(
            f"{message.role.upper()}: {message.content}" for message in history[-10:]
        )
        user_input = (
            f"Conversation so far:\n{conversation or '(none)'}\n\n"
            f"Current question:\n{question}\n\nRepository evidence:\n{evidence}"
        )

        try:
            response = self._responses().create(
                model=self._model,
                reasoning={"effort": "none"},
                text={"verbosity": "low"},
                instructions=(
                    "You are a codebase advisor. Answer only from the supplied repository evidence. "
                    "Write for a developer who is new to this codebase. Start with a direct plain-English "
                    "answer in one or two sentences, then add a short step-by-step explanation only when useful. "
                    "Define unfamiliar internal names instead of assuming the reader knows them. Use short "
                    "Markdown headings, bullets, and inline code to make the answer easy to scan. "
                    "Connect evidence across files when useful. "
                    "Cite every repository claim with bracketed evidence numbers such as [1]. "
                    "If the evidence is insufficient, say what cannot be established. Never invent files, "
                    "symbols, behavior, or line numbers."
                ),
                input=user_input,
            )
        except ChatConfigurationError:
            raise
        except Exception as error:
            raise ChatProviderError("The AI provider could not answer the question.") from error

        answer = getattr(response, "output_text", "").strip()
        if not answer:
            raise ChatProviderError("The AI provider returned an empty answer.")

        citations = [
            ChatCitation(
                reference=number,
                path=result.path,
                start_line=result.start_line,
                end_line=result.end_line,
                symbol=result.symbol,
            )
            for number, result in enumerate(search.results, start=1)
            if f"[{number}]" in answer
        ]
        return RepositoryChatResponse(
            workspace_id=workspace_id,
            answer=answer,
            citations=citations,
            sources=search.results,
        )

    def _responses(self) -> ResponsesClient:
        if self._client is not None:
            return self._client
        if self._api_key is None:
            raise ChatConfigurationError("OPENAI_API_KEY is not configured for the backend.")
        self._client = OpenAI(api_key=self._api_key.get_secret_value()).responses
        return self._client
