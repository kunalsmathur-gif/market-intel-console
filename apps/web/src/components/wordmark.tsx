// The wordmark's [1] is the same citation marker used on every claim.
export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-semibold tracking-tight ${className}`}>
      citebell<sup className="ml-0.5 font-mono text-[0.6em] text-brass">[1]</sup>
    </span>
  );
}
