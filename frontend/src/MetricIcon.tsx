const paths: Record<string, string> = {
  fleet: "M3 13l2-6h14l2 6v6h-3v-3H6v3H3v-6Zm0 0h18M7 10h10M6 14h1m10 0h1",
  check: "M20 6 9 17l-5-5",
  clock: "M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  active: "M4 12h15m-5-5 5 5-5 5M4 5v14",
  alert: "M12 8v5m0 4h.01M12 3 2 21h20L12 3Z",
  value: "M7 4h10M7 8h10M9 4c8 0 8 8 0 8H7l9 8",
  calendar: "M5 5h14v16H5V5Zm3-3v6m8-6v6M5 10h14",
};
export function MetricIcon({ label }: { label: string }) {
  const kind = /value/i.test(label) ? "value" : /overdue/i.test(label) ? "alert"
    : /pending/i.test(label) ? "clock" : /active/i.test(label) ? "active"
    : /upcoming/i.test(label) ? "calendar" : /published|completed/i.test(label) ? "check" : "fleet";
  return <span className={`metric-icon metric-icon--${kind}`} aria-hidden="true">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={paths[kind]} /></svg>
  </span>;
}
