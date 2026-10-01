import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import SyntaxHighlighter from "react-syntax-highlighter/dist/esm/prism-light";
import oneDark from "react-syntax-highlighter/dist/esm/styles/prism/one-dark";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import css from "react-syntax-highlighter/dist/esm/languages/prism/css";
import javascript from "react-syntax-highlighter/dist/esm/languages/prism/javascript";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";
import markdown from "react-syntax-highlighter/dist/esm/languages/prism/markdown";
import markup from "react-syntax-highlighter/dist/esm/languages/prism/markup";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import sql from "react-syntax-highlighter/dist/esm/languages/prism/sql";
import tsx from "react-syntax-highlighter/dist/esm/languages/prism/tsx";
import typescript from "react-syntax-highlighter/dist/esm/languages/prism/typescript";
import yaml from "react-syntax-highlighter/dist/esm/languages/prism/yaml";
import CopyButton from "./CopyButton";

// Only register the grammars worth shipping (PrismLight keeps the bundle small).
const LANGS: Record<string, unknown> = {
  bash,
  css,
  javascript,
  json,
  markdown,
  markup,
  python,
  sql,
  tsx,
  typescript,
  yaml,
};
for (const [name, def] of Object.entries(LANGS)) {
  SyntaxHighlighter.registerLanguage(name, def);
}

const ALIASES: Record<string, string> = {
  sh: "bash",
  shell: "bash",
  zsh: "bash",
  js: "javascript",
  jsx: "tsx",
  ts: "typescript",
  py: "python",
  yml: "yaml",
  md: "markdown",
  html: "markup",
  xml: "markup",
};

function resolveLang(lang?: string): string | undefined {
  if (!lang) return undefined;
  const key = ALIASES[lang.toLowerCase()] ?? lang.toLowerCase();
  return key in LANGS ? key : undefined;
}

function CodeBlock({ language, value }: { language?: string; value: string }) {
  const resolved = resolveLang(language);
  return (
    <div className="code-block">
      <div className="code-head">
        <span className="code-lang">{language || "text"}</span>
        <CopyButton text={value} label="Copy kode" />
      </div>
      {resolved ? (
        <SyntaxHighlighter
          language={resolved}
          style={oneDark}
          PreTag="div"
          customStyle={{ margin: 0, background: "transparent", fontSize: "12.5px" }}
          codeTagProps={{ style: { fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" } }}
        >
          {value}
        </SyntaxHighlighter>
      ) : (
        <pre className="code-plain">
          <code>{value}</code>
        </pre>
      )}
    </div>
  );
}

// Render agent replies as GitHub-flavored markdown; code blocks get highlight + copy.
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Block code is rendered by our own CodeBlock (with header + copy); drop the
          // default <pre> wrapper so its styles don't stack on top of ours.
          pre: ({ children }) => <>{children}</>,
          code(props) {
            const { className, children } = props;
            const text = String(children).replace(/\n$/, "");
            const match = /language-([\w-]+)/.exec(className || "");
            const isBlock = !!match || text.includes("\n");
            if (!isBlock) {
              return <code className={className}>{children}</code>;
            }
            return <CodeBlock language={match?.[1]} value={text} />;
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
