interface Props {
  title: string;
}

export default function PlaceholderPage({ title }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-32 animate-fade-in">
      <h2 className="font-mono text-ws-muted text-lg mb-2">{title}</h2>
      <p className="text-ws-muted/50 text-sm">Coming Soon</p>
    </div>
  );
}
