export type RepositoryWorkspace = {
  id: string;
  name: string;
  source_type: "github" | "upload";
  source_reference: string;
  created_at: string;
  expires_at: string;
  file_count: number;
  total_bytes: number;
};

export type SourceFile = {
  id: string;
  path: string;
  language: "python" | "javascript" | "typescript" | "tsx";
  size_bytes: number;
  line_count: number;
  syntax_error_count: number;
};

export type SourceSymbol = {
  id: string;
  file_id: string;
  name: string;
  qualified_name: string;
  kind: "function" | "method" | "class" | "interface" | "type_alias";
  start_line: number;
  start_column: number;
  end_line: number;
  end_column: number;
  signature: string;
};

export type GraphNode = {
  id: string;
  type: "file" | "symbol" | "external_module";
  label: string;
  path: string | null;
  entity_id: string | null;
  metadata: Record<string, string>;
};

export type GraphEdge = {
  id: string;
  source_id: string;
  target_id: string;
  type: "contains" | "imports" | "calls";
  line: number | null;
  label: string;
  confidence: number;
};

export type CodeChunkMetadata = {
  id: string;
  file_id: string;
  symbol_id: string | null;
  path: string;
  start_line: number;
  end_line: number;
  content_hash: string;
  token_estimate: number;
};

export type RepositoryIndex = {
  workspace_id: string;
  indexed_at: string;
  files: SourceFile[];
  symbols: SourceSymbol[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  chunks: CodeChunkMetadata[];
  stats: {
    file_count: number;
    symbol_count: number;
    edge_count: number;
    chunk_count: number;
    embedded_chunk_count: number;
    languages: Record<string, number>;
  };
};

export type RepositorySearchResult = {
  chunk_id: string;
  path: string;
  symbol: string | null;
  symbol_kind: string | null;
  start_line: number;
  end_line: number;
  excerpt: string;
  score: number;
  reason: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type ChatCitation = {
  reference: number;
  path: string;
  start_line: number;
  end_line: number;
  symbol: string | null;
};

export type RepositoryChatResponse = {
  workspace_id: string;
  answer: string;
  citations: ChatCitation[];
  sources: RepositorySearchResult[];
};
