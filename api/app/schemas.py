from typing import Literal

from pydantic import BaseModel, Field


class Repository(BaseModel):
    id: str
    owner: str
    name: str
    full_name: str
    description: str = ""
    default_branch: str = "main"
    commit_sha: str = ""
    stars: int = 0
    language: str = ""
    status: str = "connected"
    file_count: int = 0
    chunk_count: int = 0
    indexed_at: str | None = None
    html_url: str = ""
    is_demo: bool = False
    private: bool = False


class Source(BaseModel):
    id: str
    path: str
    heading: str = ""
    start_line: int
    end_line: int
    excerpt: str
    commit_sha: str
    github_url: str
    language: str = "text"


class Skill(BaseModel):
    id: str
    name: str
    category: str
    confidence: float
    evidence: list[Source] = Field(default_factory=list)


class DocumentationReference(BaseModel):
    name: str
    category: str
    kind: str
    url: str
    evidence: list[Source] = Field(default_factory=list)


class Overview(BaseModel):
    documentation: list[DocumentationReference] = Field(default_factory=list)
    repository: Repository
    skills: list[Skill]
    sources: list[Source]
    suggested_questions: list[str]
    architecture: list[dict[str, str]]
    languages: list[dict[str, str | int | float]]
    warnings: list[str]


class Message(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    citations: list[Source] = Field(default_factory=list)
    created_at: str
    cached: bool = False


class Conversation(BaseModel):
    id: str
    title: str
    created_at: str
    messages: list[Message] = Field(default_factory=list)
    repository_id: str


class Job(BaseModel):
    id: str
    repository_id: str
    status: str = "queued"
    stage: str = "queued"
    progress: int = 0
    files_processed: int = 0
    total_files: int = 0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class ConnectRequest(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    branch: str | None = Field(default=None, max_length=200)


class QuestionRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ConversationRequest(BaseModel):
    title: str = Field(default="New conversation", max_length=100)


class SkillEditRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=2000)
    selection: str = Field(default="", max_length=6000)
    context: str = Field(default="", max_length=4000)
