export default function StepHeader({
  stage,
  title,
  dek,
}: {
  stage: string;
  title: string;
  dek?: string;
}) {
  return (
    <header className="mb-8">
      <div className="kicker">{stage}</div>
      <h2 className="display mt-3 text-4xl md:text-[2.75rem]">{title}</h2>
      {dek && <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-soft">{dek}</p>}
    </header>
  );
}
