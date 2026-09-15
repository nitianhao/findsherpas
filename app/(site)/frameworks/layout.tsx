export default function FrameworkLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className="fs-legacy">{children}</div>;
}
