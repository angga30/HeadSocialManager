import { useEffect } from "react";
import { ArrowClockwise, CheckCircle, PaperPlaneTilt, X } from "@phosphor-icons/react";
import type { Post } from "../lib/api";
import Button from "./ui/Button";
import Markdown from "./Markdown";
import MediaThumb from "./MediaThumb";

const DOT: Record<string, string> = {
  draft: "bg-mute",
  scheduled: "bg-accent",
  published: "bg-ok",
  failed: "bg-danger",
};

const fmt = (iso: string | null) =>
  iso ? iso.slice(0, 16).replace("T", " ") : "—";

// Right-side drawer with full post detail. Closes on Escape / backdrop / X.
export default function PostDetail({
  post,
  onClose,
  onApprove,
  onPublish,
}: {
  post: Post;
  onClose: () => void;
  onApprove: (id: number) => void;
  onPublish: (id: number) => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40" role="dialog" aria-modal="true" aria-label={`Detail post #${post.id}`}>
      <button
        type="button"
        aria-label="Tutup"
        onClick={onClose}
        className="absolute inset-0 bg-black/50"
      />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col gap-4 overflow-auto border-l border-line bg-panel p-5 shadow-2xl shadow-black/50">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${DOT[post.status] ?? "bg-mute"}`} />
            <span className={`badge badge-${post.status}`}>{post.status}</span>
            <span className="text-[13px] text-mute">#{post.id}</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup detail"
            className="btn btn-icon"
          >
            <X size={14} weight="bold" />
          </button>
        </div>

        <h3 className="text-base font-semibold leading-snug">{post.headline || "(tanpa headline)"}</h3>

        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-[13px]">
          <dt className="text-mute">Channel</dt>
          <dd>
            {post.channel ?? "—"}
            {post.handle ? ` · ${post.handle}` : ""}
          </dd>
          <dt className="text-mute">Pillar</dt>
          <dd>{post.pillar ?? "—"}</dd>
          <dt className="text-mute">Format</dt>
          <dd>{post.depth_hint ?? "—"}</dd>
          <dt className="text-mute">Jadwal</dt>
          <dd className="tabular-nums">{fmt(post.scheduled_at)}</dd>
          {post.published_at && (
            <>
              <dt className="text-mute">Terbit</dt>
              <dd className="tabular-nums">{fmt(post.published_at)}</dd>
            </>
          )}
        </dl>

        {post.body && (
          <div className="rounded-lg border border-line bg-panel2 p-3">
            <div className="text-xs uppercase tracking-wide text-mute">Caption</div>
            <div className="mt-1.5 text-sm">
              <Markdown>{post.body}</Markdown>
            </div>
          </div>
        )}

        {post.media.length > 0 && (
          <div>
            <div className="mb-1.5 text-xs uppercase tracking-wide text-mute">Media</div>
            <div className="flex flex-wrap gap-2">
              {post.media.map((m) => (
                <MediaThumb key={m.filename} media={m} />
              ))}
            </div>
          </div>
        )}

        <div className="mt-auto flex gap-2 pt-2">
          {post.status === "draft" && (
            <Button variant="ghost" onClick={() => onApprove(post.id)}>
              <CheckCircle size={15} /> Approve
            </Button>
          )}
          {post.status !== "published" && (
            <Button onClick={() => onPublish(post.id)}>
              <PaperPlaneTilt size={15} /> Publish
            </Button>
          )}
          {post.status === "published" && (
            <Button variant="ghost" disabled>
              <ArrowClockwise size={15} /> Sudah terbit
            </Button>
          )}
        </div>
      </aside>
    </div>
  );
}
