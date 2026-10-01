import type { Media } from "../lib/api";

const VIDEO_EXTS = [".mp4", ".webm", ".mov", ".m4v"];

function isVideo(m: Media): boolean {
  if (m.kind) return m.kind === "video";
  return VIDEO_EXTS.some((ext) => m.filename.toLowerCase().endsWith(ext));
}

// Render a media item as a thumbnail: <video> for video files, <img> otherwise.
export default function MediaThumb({ media }: { media: Media }) {
  if (isVideo(media)) {
    return (
      <video
        src={media.url}
        controls
        preload="metadata"
        className="h-24 w-24 rounded-md border border-line bg-bg object-cover"
      />
    );
  }
  return (
    <img
      src={media.url}
      alt={media.filename}
      className="h-24 w-24 rounded-md border border-line object-cover"
    />
  );
}
