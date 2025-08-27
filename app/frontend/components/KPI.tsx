export interface KPIProps {
  label: string;
  value: string | number;
}

export default function KPI({ label, value }: KPIProps) {
  return (
    <div>
      <strong>{label}:</strong> {value}
    </div>
  );
}
