export default function RoyalDivider({ className = "" }) {
  return (
    <div className={`relative mx-auto my-6 h-px w-28 bg-gold ${className}`}>
      <span className="absolute left-1/2 top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rotate-45 border-2 border-ivory bg-gold" />
    </div>
  );
}
