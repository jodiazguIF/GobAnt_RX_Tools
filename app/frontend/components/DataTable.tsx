export interface DataTableProps {
  rows: any[];
}

export default function DataTable({ rows }: DataTableProps) {
  if (!rows || rows.length === 0) return null;
  const headers = Object.keys(rows[0]);
  return (
    <table>
      <thead>
        <tr>
          {headers.map((h) => (
            <th key={h}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {headers.map((h) => (
              <td key={h}>{r[h]}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
