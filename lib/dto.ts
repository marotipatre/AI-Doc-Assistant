/** Browser transport types mirrored by the FastAPI OpenAPI models. */
export type ApiMode = "demo" | "live";
export type RepositoryStatus = "connected" | "indexing" | "ready" | "failed";
export interface Repository {
  id: string;
  owner: string;
  name: string;
  full_name: string;
  html_url: string;
  description: string;
  default_branch: string;
  stars: number;
  language: string;
  commit_sha: string;
  status: RepositoryStatus;
  file_count: number;
  chunk_count: number;
  indexed_at: string | null;
  is_demo: boolean;
  private: boolean;
}
export interface Source {
  id: string;
  path: string;
  heading: string;
  start_line: number;
  end_line: number;
  excerpt: string;
  commit_sha: string;
  github_url: string;
  language: string;
}
export interface Skill {
  id: string;
  name: string;
  category: string;
  confidence: number;
  evidence: Source[];
}
export interface DocumentationReference {
  name: string;
  category: string;
  kind: string;
  url: string;
  evidence: Source[];
}
export interface Overview {
  documentation?: DocumentationReference[];
  repository: Repository;
  skills: Skill[];
  architecture: { name: string; description: string; path?: string }[];
  languages: { name: string; percentage: number; color?: string }[];
  suggested_questions: string[];
  sources: Source[];
  warnings: string[];
}
export interface Message {
  cached?: boolean;
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Source[];
  created_at: string;
}
export interface Conversation {
  id: string;
  repository_id: string;
  title: string;
  messages: Message[];
  created_at: string;
}
export type JobStage =
  | "queued"
  | "fetching"
  | "discovering"
  | "parsing"
  | "embedding"
  | "saving"
  | "ready"
  | "failed"
  | "cancelled";
export interface Job {
  id: string;
  repository_id: string;
  status: string;
  stage: JobStage;
  progress: number;
  files_processed: number;
  total_files: number;
  warnings: string[];
  error: string | null;
}
export type StreamEvent =
  | { type: "token"; text: string }
  | { type: "citations"; sources: Source[] }
  | { type: "done"; message: Message }
  | { type: "error"; message: string };

export interface RepoLensApi {
  listRepositories(): Promise<Repository[]>;
  connectRepository(url: string, branch?: string): Promise<Repository>;
  indexRepository(id: string): Promise<Job>;
  syncRepository(id: string): Promise<Job>;
  getJob(id: string): Promise<Job>;
  cancelJob(id: string): Promise<Job>;
  deleteRepository(id: string): Promise<void>;
  getOverview(id: string): Promise<Overview>;
  getSkills(id: string): Promise<Skill[]>;
  listSources(id: string): Promise<Source[]>;
  getSource(repoId: string, id: string): Promise<Source>;
  listConversations(repoId: string): Promise<Conversation[]>;
  getConversation(id: string): Promise<Conversation>;
  createConversation(repoId: string): Promise<Conversation>;
  deleteConversation(id: string): Promise<void>;
  streamMessage(
    id: string,
    content: string,
    onEvent: (event: StreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void>;
  exportContext(repoId: string): Promise<string>;
}
