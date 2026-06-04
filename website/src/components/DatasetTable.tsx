import type { CsvRow } from "../lib/dataLoader";

type DatasetTableProps = {
  rows: CsvRow[];
  columns: string[];
  limit?: number;
};

export default function DatasetTable({ rows, columns, limit = 20 }: DatasetTableProps) {
  const previewRows = rows.slice(0, limit);

  if (!columns.length) {
    return <p className="muted">No columns available for this dataset.</p>;
  }

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {previewRows.map((row, index) => (
            <tr key={`${row.date || row.river || "row"}-${index}`}>
              {columns.map((column) => (
                <td key={column}>{row[column]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
