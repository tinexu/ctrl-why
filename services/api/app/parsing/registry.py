from tree_sitter import Language, Parser
import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript

from app.domain.parsing import SourceLanguage


class ParserRegistry:
    """Creates language parsers for the supported source types."""

    def __init__(self) -> None:
        self._languages = {
            SourceLanguage.python: Language(tree_sitter_python.language()),
            SourceLanguage.javascript: Language(tree_sitter_javascript.language()),
            SourceLanguage.typescript: Language(tree_sitter_typescript.language_typescript()),
            SourceLanguage.tsx: Language(tree_sitter_typescript.language_tsx()),
        }

    def create(self, language: SourceLanguage) -> Parser:
        return Parser(self._languages[language])
