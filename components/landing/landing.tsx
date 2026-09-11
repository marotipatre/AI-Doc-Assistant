import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  Boxes,
  Check,
  FileCode2,
  GitBranch,
  Layers3,
  ShieldCheck,
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { ProductPreview } from "./product-preview";
function Header() {
  return (
    <header className="marketing-header">
      <Link href="/" className="studio-brand">
        <Boxes size={22} />
        repolens.
      </Link>
      <nav aria-label="Main navigation">
        <Link href="/#workflow">Features</Link>
        <Link href="/guide">User guide</Link>
        <Link href="/workspace?demo=1">View example</Link>
      </nav>
      <div>
        <ThemeToggle />
        <Link className="button primary" href="/workspace/repository">
          Choose repository <ArrowUpRight size={15} />
        </Link>
      </div>
    </header>
  );
}
export function LandingPage() {
  const features = [
    {
      title: "Choose a repository",
      text: "Connect GitHub to choose from your repositories, or paste a public repository URL. You decide which repository to open.",
      label: "Choose repository",
      href: "/workspace/repository",
      icon: GitBranch,
    },
    {
      title: "Review the project files",
      text: "Read the setup documentation, project instructions, and test configuration used to prepare your document.",
      label: "View an example",
      href: "/workspace?demo=1",
      icon: Layers3,
    },
    {
      title: "Edit your instructions",
      text: "Write directly in the editor. Use the writing assistant to revise a passage or add a section, then review and apply the suggestion.",
      label: "Try the editor",
      href: "/workspace?demo=1",
      icon: FileCode2,
    },
    {
      title: "Download SKILL.md",
      text: "Download the edited Markdown file. It includes repository setup references, project rules, and checks for your next change.",
      label: "Read the user guide",
      href: "/guide",
      icon: ShieldCheck,
    },
  ];
  return (
    <div className="marketing-app">
      <Header />
      <main>
        <section className="marketing-hero">
          <div className="marketing-hero-copy">
            <span className="hero-eyebrow">REPOSITORY DOCUMENTATION</span>
            <h1>
              Create a useful
              <br />
              <em>SKILL.md</em>
              <br />
              for your project.
            </h1>
            <p>
              Keep setup steps, project rules, and verification checks in one
              editable file. Choose a GitHub repository, review its files, and
              download instructions tailored to your project.
            </p>
            <div className="hero-cta">
              <Link className="button primary" href="/workspace/repository">
                Choose a repository <ArrowUpRight size={17} />
              </Link>
              <Link className="button secondary" href="/workspace?demo=1">
                See an example <ArrowRight size={16} />
              </Link>
            </div>
            <div className="hero-trust">
              <span>
                <Check size={14} /> Edit before downloading
              </span>
              <span>
                <Check size={14} /> No changes to GitHub files
              </span>
            </div>
          </div>
          <ProductPreview />
        </section>
        <div className="marketing-ribbon">
          <span>WHAT GOES IN YOUR FILE</span>
          <span>
            <FileCode2 size={19} /> Setup instructions
          </span>
          <span>
            <Layers3 size={19} /> Project conventions
          </span>
          <span>
            <GitBranch size={19} /> Verification checks
          </span>
        </div>
        <section className="marketing-features" id="workflow">
          <div className="marketing-section-heading">
            <div>
              <span className="mini-label">HOW IT WORKS</span>
              <h2>Choose. Review. Edit. Download.</h2>
            </div>
            <p>
              SKILL.md is a Markdown instruction file for working in a
              repository. You control what goes into it.
            </p>
          </div>
          <div className="marketing-feature-grid">
            {features.map((feature, i) => (
              <Link
                className="marketing-feature"
                href={feature.href}
                key={feature.title}
              >
                <div className="feature-top">
                  <span>
                    <feature.icon size={24} />
                  </span>
                  <small>0{i + 1}</small>
                </div>
                <h3>{feature.title}</h3>
                <p>{feature.text}</p>
                <div className="feature-link">
                  {feature.label}
                  <ArrowUpRight size={18} />
                </div>
              </Link>
            ))}
          </div>
        </section>
        <section className="marketing-bottom-cta">
          <div>
            <h2>Start with your repository.</h2>
            <p>
              You can read public repositories without connecting a GitHub
              account.
            </p>
          </div>
          <Link className="button primary" href="/workspace/repository">
            Choose repository <ArrowUpRight size={17} />
          </Link>
        </section>
        <div className="marketing-limit">
          <p>
            Review setup commands and requirements against the repository before
            using the downloaded file.
          </p>
        </div>
      </main>
      <footer className="marketing-footer">
        <Link className="studio-brand" href="/">
          repolens.
        </Link>
        <span>Repository instructions you can edit.</span>
        <Link href="/guide">User guide</Link>
      </footer>
    </div>
  );
}
export function GuidePage() {
  return (
    <div className="marketing-app guide-app">
      <Header />
      <main className="handoff-main">
        <section className="handoff-hero">
          <span className="mini-label">USER GUIDE</span>
          <h1>Create your project’s SKILL.md.</h1>
          <p>
            SKILL.md is a Markdown file that describes how to work in a
            repository. Use RepoLens to prepare, edit, and download that file.
          </p>
        </section>
        {[
          [
            "1. Choose a repository",
            "Select Connect GitHub in the top navigation. After GitHub returns you to RepoLens, choose a repository from the list. For a public repository, you can paste its URL without connecting an account. Select Read repository to start. Signing in does not select or read a repository automatically.",
          ],
          [
            "2. Review the source files",
            "The editor lists documentation and configuration files used to prepare the instructions. Select View files on a card or open Repository files to read the source. If a file is not listed, check the repository before adding commands or requirements.",
          ],
          [
            "3. Edit SKILL.md",
            "Edit the document directly. To get help, select the passage you want changed and describe the change in Writing assistant. With no text selected, a suggestion adds a new section. Review the suggested text, then select Apply change or Discard. Your document is not changed automatically.",
          ],
          [
            "4. Download and use the file",
            "Select Download SKILL.md to save the current editor contents. If your coding tool supports skills, place the file in the folder shown below the editor. Otherwise, use it as project documentation. Check your tool’s instructions for the correct location.",
          ],
          [
            "Manage your GitHub connection",
            "The top navigation shows the connected GitHub account. Open that menu to choose a repository, switch accounts, or disconnect. Disconnect clears the selected repository and draft from the workspace and removes stored private repository data. It does not sign you out of github.com.",
          ],
          [
            "Return to a project",
            "Each new visit starts without a selected repository. Choose a previously read repository or read a new one. Use Sync repository to refresh its files before preparing a new document. Download your edited document before leaving or disconnecting; edits are kept only in the current workspace session.",
          ],
        ].map(([title, text]) => (
          <section className="handoff-connection" key={title}>
            <h2>{title}</h2>
            <p>{text}</p>
          </section>
        ))}
        <section className="handoff-connection">
          <h2>Ask questions about the repository</h2>
          <p>
            After choosing a repository, open Ask repository. Ask about setup,
            architecture, or a feature. Answers arrive as they are written and
            include references you can inspect. You can add a useful answer to
            SKILL.md for review in the editor.
          </p>
        </section>
        <Link className="button primary" href="/workspace/repository">
          Choose repository
        </Link>
      </main>
    </div>
  );
}
