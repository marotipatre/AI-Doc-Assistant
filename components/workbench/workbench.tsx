"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ArrowUpRight,
  BookOpen,
  Boxes,
  ChevronRight,
  FileCode2,
  FolderGit2,
  GitBranch,
  GitFork as Github,
  ShieldCheck,
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { RepositoryQuestions } from "./repository-questions";
import { readinessPack } from "@/lib/readiness-pack";
import { ReadinessPack } from "./readiness-pack";
import {
  authApi,
  getApi,
  type AuthSession,
  type GithubRepository,
} from "@/lib/api-client";
import { demoOverview } from "@/lib/demo-data";
import type { Job, Overview, Repository } from "@/lib/dto";

function useWorkspaceController() {
  const router = useRouter();
  const [initialized, setInitialized] = useState(false);
  const [task, setTask] = useState("");
  const [editedDocument, setEditedDocument] = useState<string | null>(null);
  const [demo, setDemo] = useState(false);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [auth, setAuth] = useState<AuthSession | null>(null);
  const [githubRepos, setGithubRepos] = useState<GithubRepository[]>([]);
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [search, setSearch] = useState("");
  const live = useRef<Overview | null>(null);
  const mounted = useRef(true);
  const errorText = (e: unknown) =>
    e instanceof Error ? e.message : "Something went wrong. Please retry.";
  useEffect(() => {
    mounted.current = true;
    const initialization = requestAnimationFrame(() => {
      const params = new URLSearchParams(location.search);

      if (params.has("connect") || params.has("github"))
        router.replace("/workspace/repository");
      const forcedDemo = params.get("demo") === "1";
      setDemo(forcedDemo);
      setOverview(forcedDemo ? demoOverview : null);
      setInitialized(true);
      // A new visit always asks the user to choose a repository.
      void Promise.all([authApi.session(), getApi("live").listRepositories()])
        .then(async ([session, list]) => {
          if (!mounted.current) return;
          setAuth(session);
          setRepos(list.filter((repo) => !repo.is_demo));
          if (session.authenticated) {
            const available = await authApi.repositories();
            if (mounted.current) setGithubRepos(available);
          }
        })
        .catch((e) => {
          if (mounted.current && !forcedDemo) setError(errorText(e));
        });
    });
    return () => {
      cancelAnimationFrame(initialization);
      mounted.current = false;
    };
  }, [router]);
  function remember(next: Overview | null) {
    const params = new URLSearchParams(location.search);
    params.delete("demo");
    params.delete("view");
    history.replaceState(
      null,
      "",
      `${location.pathname}${params.size ? `?${params}` : ""}`,
    );
    try {
      localStorage.setItem(
        "repolens:workspace",
        JSON.stringify({ mode: "live", id: next?.repository.id }),
      );
    } catch {}
  }
  async function toggleDemo() {
    setTask("");
    setEditedDocument(null);
    setError("");
    setJob(null);
    if (!demo) {
      live.current = overview;
      setDemo(true);
      history.replaceState(null, "", `${location.pathname}?demo=1`);
      setOverview(demoOverview);
      return;
    }
    setDemo(false);
    setOverview(live.current);
    setBusy(true);
    try {
      const list = (await getApi("live").listRepositories()).filter(
        (repo) => !repo.is_demo,
      );
      setRepos(list);
      const selected = list.find(
        (repo) => repo.id === live.current?.repository.id,
      );
      const next = selected
        ? await getApi("live").getOverview(selected.id)
        : null;
      live.current = next;
      setOverview(next);
      remember(next);

      if (!next) router.push("/workspace/repository");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function selectRepo(id: string) {
    setBusy(true);
    setError("");
    setJob(null);
    try {
      const next = await getApi("live").getOverview(id);
      setOverview(next);
      setDemo(false);
      setTask("");
      setEditedDocument(null);
      live.current = next;
      remember(next);
      router.push("/workspace");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function index(sync = false) {
    setBusy(true);
    setError("");
    setJob(null);
    try {
      const api = getApi("live");
      const repo =
        sync && overview
          ? overview.repository
          : await api.connectRepository(url.trim(), branch.trim() || undefined);
      let current = sync
        ? await api.syncRepository(repo.id)
        : await api.indexRepository(repo.id);
      setJob(current);
      const deadline = Date.now() + 180_000;
      while (!["ready", "failed", "cancelled"].includes(current.stage)) {
        if (Date.now() > deadline)
          throw new Error(
            "Indexing is still running. Wait a moment, then select the repository or sync again to refresh its status.",
          );
        await new Promise((resolve) => setTimeout(resolve, 900));
        if (!mounted.current) return;
        current = await api.getJob(current.id);
        setJob(current);
      }
      if (current.stage !== "ready")
        throw new Error(
          current.error || "Indexing did not finish. Retry when ready.",
        );
      const next = await api.getOverview(repo.id);
      live.current = next;
      setOverview(next);
      setTask("");
      setEditedDocument(null);
      setDemo(false);
      remember(next);
      setRepos((await api.listRepositories()).filter((repo) => !repo.is_demo));

      router.push("/workspace");
    } catch (e) {
      setError(errorText(e));
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  async function signIn(privateAccess = false) {
    setBusy(true);
    setError("");
    try {
      const session = await authApi.session();
      setAuth(session);
      if (!session.github_configured)
        throw new Error(
          "GitHub sign-in is not configured. You can still paste a public repository URL.",
        );
      window.location.assign(
        new URL(
          `/api/backend/v1/auth/github${privateAccess ? "?private=true" : ""}`,
          window.location.origin,
        ).href,
      );
    } catch (e) {
      setError(errorText(e));
      setBusy(false);
    }
  }
  async function browse() {
    setBusy(true);
    setError("");
    try {
      setGithubRepos(await authApi.repositories());
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function disconnect() {
    setBusy(true);
    setError("");
    try {
      await authApi.logout();
      setAuth(null);
      setGithubRepos([]);
      setRepos([]);
      live.current = null;
      setOverview(null);
      setDemo(false);
      setJob(null);
      remember(null);
      setUrl("");
      setBranch("");
      setTask("");
      setEditedDocument(null);
      setSearch("");
      try {
        localStorage.removeItem("repolens:workspace");
      } catch {}
      router.push("/workspace/repository");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  const evidence =
    overview?.sources.filter((source) =>
      `${source.path} ${source.excerpt}`
        .toLowerCase()
        .includes(search.toLowerCase()),
    ) || [];
  return {
    initialized,
    demo,
    overview,
    repos,
    auth,
    githubRepos,
    url,
    setUrl,
    branch,
    setBranch,
    busy,
    error,
    setError,
    job,
    search,
    setSearch,
    toggleDemo,
    selectRepo,
    index,
    signIn,
    browse,
    disconnect,
    evidence,
    task,
    setTask,
    editedDocument,
    setEditedDocument,
  };
}

const WorkspaceContext = createContext<ReturnType<
  typeof useWorkspaceController
> | null>(null);
function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("Workspace provider missing");
  return value;
}

export function Workbench({ children }: { children: ReactNode }) {
  const workspace = useWorkspaceController();
  const {
    demo,
    busy,
    overview,
    toggleDemo,
    error,
    setError,
    job,
    auth,
    signIn,
    disconnect,
  } = workspace;
  const [accountOpen, setAccountOpen] = useState(false);
  const pathname = usePathname();
  const navigation = [
    {
      href: "/workspace/questions",
      label: "Ask repository",
      icon: BookOpen,
      step: "",
    },
    {
      href: "/workspace",
      label: "SKILL.md editor",
      icon: ShieldCheck,
      step: "01",
    },
    {
      href: "/workspace/evidence",
      label: "Repository files",
      icon: FileCode2,
      step: "02",
    },
    {
      href: "/workspace/repository",
      label: "Choose repository",
      icon: FolderGit2,
      step: "03",
    },
  ];
  return (
    <WorkspaceContext value={workspace}>
      <div className="studio-app">
        <aside className="studio-sidebar">
          <Link className="studio-brand" href="/">
            <span className="brand-glyph">
              <Boxes size={21} />
            </span>
            repolens<span className="brand-period">.</span>
          </Link>
          <div className="studio-space">
            <span className="space-avatar">{demo ? "S" : "W"}</span>
            <div>
              <strong>{demo ? "Example workspace" : "Your workspace"}</strong>
              <small>Repository instructions</small>
            </div>
          </div>
          <span className="studio-nav-label">WORKSPACE</span>
          <nav aria-label="Workspace pages">
            {navigation.map(({ href, label, icon: Icon, step }) => (
              <Link
                key={href}
                href={href}
                aria-current={pathname === href ? "page" : undefined}
              >
                <Icon size={18} />
                <span>{label}</span>
                <small>{step}</small>
              </Link>
            ))}
          </nav>
          <div className="studio-sidebar-note">
            <FileCode2 size={21} />
            <strong>What is SKILL.md?</strong>
            <p>
              A Markdown file containing setup steps, project rules, and checks
              for this repository.
            </p>
            <Link href="/guide">
              How to use the file <ArrowUpRight size={14} />
            </Link>
          </div>
          <Link className="studio-guide" href="/guide">
            <BookOpen size={17} /> How it works <ArrowUpRight size={14} />
          </Link>
          <div className="studio-sidebar-foot">
            <span className="status-dot" /> Changes stay in this workspace
          </div>
        </aside>
        <div className="studio-body">
          <header className="studio-topbar">
            <div>
              <span>Workspace</span>
              <ChevronRight size={14} />
              <strong>
                {navigation.find((item) => item.href === pathname)?.label}
              </strong>
            </div>
            <div>
              <div className="account-control">
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() =>
                    auth?.authenticated
                      ? setAccountOpen(!accountOpen)
                      : signIn()
                  }
                  aria-expanded={auth?.authenticated ? accountOpen : undefined}
                >
                  <Github size={16} />
                  {auth?.authenticated
                    ? `GitHub: ${auth.user?.login}`
                    : "Connect GitHub"}
                </button>
                {accountOpen && auth?.authenticated && (
                  <div className="account-menu">
                    <p>
                      Connected to GitHub as <strong>{auth.user?.login}</strong>
                    </p>
                    <Link
                      href="/workspace/repository"
                      onClick={() => setAccountOpen(false)}
                    >
                      Choose a repository
                    </Link>
                    <button
                      disabled={busy}
                      onClick={() => {
                        setAccountOpen(false);
                        void signIn();
                      }}
                    >
                      Switch GitHub account
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => {
                        setAccountOpen(false);
                        void disconnect();
                      }}
                    >
                      Disconnect GitHub
                    </button>
                  </div>
                )}
              </div>
              <button
                className="studio-demo"
                role="switch"
                aria-label="Demo mode"
                aria-checked={demo}
                disabled={busy}
                onClick={toggleDemo}
              >
                <span className="switch-track">
                  <i />
                </span>{" "}
                Demo {demo ? "on" : "off"}
              </button>
              <ThemeToggle />
            </div>
          </header>
          <div className="studio-repo-strip">
            <span>
              <Github size={16} />
              {overview?.repository.full_name || "No repository connected"}
            </span>
            <span>
              <GitBranch size={14} />
              {overview?.repository.default_branch || "Choose a branch"}
              {!demo && overview && (
                <button
                  className="studio-sync"
                  disabled={busy}
                  onClick={() => workspace.index(true)}
                >
                  Sync repository
                </button>
              )}
              <i className="studio-chip">
                {demo ? "EXAMPLE" : overview ? "SELECTED" : "NOT SELECTED"}
              </i>
            </span>
          </div>
          <main id="main-content" className="studio-content">
            {error && (
              <div className="error-banner" role="alert">
                {error}
                <button onClick={() => setError("")}>Dismiss</button>
              </div>
            )}
            {busy && (
              <div className="studio-progress" role="status">
                <span className="status-dot" />
                {job
                  ? `Indexing: ${job.stage} · ${job.progress}%`
                  : "Loading repository…"}
              </div>
            )}
            {job?.warnings.map((warning) => (
              <p key={warning} role="status">
                {warning}
              </p>
            ))}
            {workspace.initialized ? (
              children
            ) : (
              <p role="status">Opening workspace…</p>
            )}
          </main>
          <footer className="studio-footer">
            <span>REPOLENS</span>
            <span>Review and download repository instructions.</span>
          </footer>
        </div>
      </div>
    </WorkspaceContext>
  );
}
export function PackPage() {
  const { overview, task, setTask, editedDocument, setEditedDocument } =
    useWorkspace();
  return overview ? (
    <ReadinessPack
      key={overview.repository.id}
      overview={overview}
      task={task}
      onTaskChange={setTask}
      editedDocument={editedDocument}
      onDocumentChange={setEditedDocument}
    />
  ) : (
    <div className="studio-empty">
      <FolderGit2 size={40} />
      <h1>Create instructions for your repository.</h1>
      <p>
        Choose a GitHub repository or paste its URL. We’ll read its files and
        prepare a SKILL.md you can edit and download.
      </p>
      <Link className="button primary" href="/workspace/repository">
        Connect repository <ArrowUpRight size={16} />
      </Link>
    </div>
  );
}
export function RepositoryPage() {
  const {
    overview,
    demo,
    busy,
    repos,
    selectRepo,
    index,
    url,
    setUrl,
    branch,
    setBranch,
    auth,
    browse,
    signIn,
    githubRepos,
  } = useWorkspace();
  return (
    <>
      <div className="studio-page-heading">
        <span className="mini-label">STEP 1</span>
        <h1>Choose a repository</h1>
        <p>
          Select a repository below, or paste a public GitHub URL. Nothing is
          imported until you select Read repository.
        </p>
      </div>{" "}
      <section
        className="handoff-connection"
        aria-label="Repository connection"
      >
        <div>
          <span className="mini-label">01 / REPOSITORY</span>
          <h1>{overview?.repository.full_name || "No repository selected"}</h1>
          <p>
            {demo
              ? "Example repository — this is not connected to your GitHub account."
              : "The selected repository is read-only. Editing SKILL.md here does not change files on GitHub."}
          </p>
        </div>
        <div className="pack-actions">
          {!demo && overview && (
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => index(true)}
            >
              Sync repository
            </button>
          )}
        </div>
        {!demo && repos.length > 0 && (
          <label>
            Saved repository
            <select
              value={overview?.repository.id || ""}
              disabled={busy}
              onChange={(e) => selectRepo(e.target.value)}
            >
              {!overview && <option value="">Choose repository</option>}
              {repos.map((repo) => (
                <option key={repo.id} value={repo.id}>
                  {repo.full_name}
                </option>
              ))}
            </select>
          </label>
        )}
        {auth?.authenticated && (
          <section className="repository-picker">
            <div>
              <h2>Your GitHub repositories</h2>
              <button
                className="button secondary"
                disabled={busy}
                onClick={browse}
              >
                Refresh list
              </button>
            </div>
            <p>
              Select a repository to fill in its URL and default branch, then
              select Read repository.
            </p>
            {githubRepos.length ? (
              <select
                aria-label="Select GitHub repository"
                value={
                  githubRepos.some((repo) => repo.html_url === url) ? url : ""
                }
                disabled={busy}
                onChange={(e) => {
                  const chosen = githubRepos.find(
                    (repo) => repo.html_url === e.target.value,
                  );
                  setUrl(e.target.value);
                  setBranch(chosen?.default_branch || "");
                }}
              >
                <option value="">Choose a repository…</option>
                {githubRepos.map((repo) => (
                  <option key={repo.full_name} value={repo.html_url}>
                    {repo.full_name}
                    {repo.private ? " (private)" : ""}
                  </option>
                ))}
              </select>
            ) : (
              <p>
                No repositories are available yet. Refresh the list, or
                authorize private repository access below.
              </p>
            )}
          </section>
        )}
        <div className="handoff-connect">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void index();
            }}
          >
            <label htmlFor="repo-url">GitHub repository URL</label>
            <input
              id="repo-url"
              type="url"
              required
              placeholder="https://github.com/owner/repository"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={busy}
            />
            <label htmlFor="repo-branch">Branch or ref (optional)</label>
            <input
              id="repo-branch"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              disabled={busy}
            />
            <button className="button primary" disabled={busy}>
              {busy ? "Working…" : "Read repository"}
            </button>
            <p>
              Public repositories need no sign-in. Private repositories require
              explicit GitHub access.
            </p>
          </form>
          <div>
            <h3>Private repository access</h3>
            <p>
              Connect GitHub from the top navigation to list your repositories.
              If a private repository is missing, authorize access below, then
              refresh the list.
            </p>
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => signIn(true)}
            >
              Authorize private repositories
            </button>
            <p>
              To use another account or disconnect, open the GitHub menu in the
              top navigation.
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
export function EvidencePage() {
  const { overview, evidence, search, setSearch } = useWorkspace();
  return (
    <>
      <div className="studio-page-heading">
        <span className="mini-label">REFERENCE FILES</span>
        <h1>Repository files</h1>
        <p>
          Search the files used to prepare your SKILL.md. Expand a result to
          read it.
        </p>
      </div>
      {overview ? (
        <section className="handoff-evidence">
          <details open>
            <summary>
              Read repository files ({overview.sources.length} excerpts)
            </summary>
            <p>
              Check the source before following generated guidance. Search runs
              locally.
            </p>
            <label htmlFor="evidence-search">Search files</label>
            <input
              id="evidence-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="File path or keyword"
            />
            {evidence.length === 0 && <p>No files match your search.</p>}
            {evidence.slice(0, 60).map((source) => (
              <details key={source.id}>
                <summary>
                  {source.path}:{source.start_line}–{source.end_line}
                </summary>
                <pre>{source.excerpt}</pre>
                <a href={source.github_url} target="_blank" rel="noreferrer">
                  View source at indexed commit
                </a>
              </details>
            ))}
            {evidence.length > 60 && (
              <p>Showing 60 excerpts. Narrow your search to find more.</p>
            )}
          </details>
        </section>
      ) : (
        <div className="studio-empty">
          <p>Choose a repository to browse its files.</p>
          <Link className="button primary" href="/workspace/repository">
            Connect repository
          </Link>
        </div>
      )}
    </>
  );
}

export function QuestionsPage() {
  const { overview, editedDocument, task, setEditedDocument } = useWorkspace();
  return overview ? (
    <RepositoryQuestions
      key={overview.repository.id}
      overview={overview}
      onAddToDocument={(text) =>
        setEditedDocument(
          (editedDocument ?? readinessPack(overview, task).markdown) + text,
        )
      }
    />
  ) : (
    <div className="studio-empty">
      <h1>Choose a repository to ask questions.</h1>
      <p>
        We need to read the repository files before answering questions about
        them.
      </p>
      <Link className="button primary" href="/workspace/repository">
        Choose repository
      </Link>
    </div>
  );
}
