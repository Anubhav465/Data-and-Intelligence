import { useState } from 'react';
import { motion } from 'framer-motion';
import { Table2, Columns, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { useDataset } from '../../context/DatasetContext';
import './DatasetPreview.css';

const TYPE_COLOR = {
  BIGINT: 'type--int',
  INTEGER: 'type--int',
  'DOUBLE PRECISION': 'type--float',
  REAL: 'type--float',
  BOOLEAN: 'type--bool',
  TIMESTAMP: 'type--date',
  DATE: 'type--date',
  TEXT: 'type--text',
};

const TypeBadge = ({ pgType }) => {
  const short = pgType === 'DOUBLE PRECISION' ? 'FLOAT' : pgType;
  return <span className={`type-badge ${TYPE_COLOR[pgType] || 'type--text'}`}>{short}</span>;
};

const DatasetPreview = () => {
  const { activeDataset } = useDataset();
  const [showRows, setShowRows] = useState(true);
  const [showColumns, setShowColumns] = useState(true);

  if (!activeDataset) return null;

  const { table_name, columns = [], row_count = 0, preview_rows = [], cleaning } = activeDataset;
  const previewSlice = preview_rows.slice(0, 10);
  const colKeys = previewSlice.length > 0 ? Object.keys(previewSlice[0]) : columns.map((c) => c.name);

  const shortName = table_name.replace('user_table_', '');

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="dp"
    >
      {/* Header */}
      <div className="dp__header">
        <div className="dp__title-row">
          <Table2 size={14} color="#22d3ee" />
          <span className="dp__name" title={table_name}>{shortName}</span>
        </div>
        <span className="dp__rows">{row_count.toLocaleString()} rows</span>
      </div>

      {/* Cleaning report */}
      {cleaning && (
        <div className="dp__cleaning">
          <Sparkles size={11} color="#a855f7" />
          <span>
            {cleaning.null_strings_replaced > 0 && `${cleaning.null_strings_replaced} nulls normalised · `}
            {cleaning.rows_dropped_duplicates > 0 && `${cleaning.rows_dropped_duplicates} dupes removed · `}
            {cleaning.total_rows_after?.toLocaleString()} rows after cleaning
          </span>
        </div>
      )}

      {/* Columns section */}
      <div className="dp__section">
        <button className="dp__section-toggle" onClick={() => setShowColumns((p) => !p)}>
          <Columns size={12} />
          <span>Columns ({columns.length})</span>
          {showColumns ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>
        {showColumns && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="dp__columns-list"
          >
            {columns.map((col) => (
              <div key={col.name} className="dp__col-row">
                <span className="dp__col-name" title={col.original_name !== col.name ? col.original_name : undefined}>
                  {col.name}
                </span>
                <TypeBadge pgType={col.pg_type} />
              </div>
            ))}
          </motion.div>
        )}
      </div>

      {/* Preview rows section */}
      {previewSlice.length > 0 && (
        <div className="dp__section">
          <button className="dp__section-toggle" onClick={() => setShowRows((p) => !p)}>
            <Table2 size={12} />
            <span>Preview ({Math.min(10, previewSlice.length)} rows)</span>
            {showRows ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {showRows && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              className="dp__table-wrap scrollbar-neural"
            >
              <table className="dp__table">
                <thead>
                  <tr>
                    {colKeys.map((k) => (
                      <th key={k} className="dp__th">{k}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {previewSlice.map((row, i) => (
                    <tr key={i} className="dp__tr">
                      {colKeys.map((k) => (
                        <td key={k} className="dp__td">
                          {row[k] === null || row[k] === undefined
                            ? <span className="dp__null">null</span>
                            : String(row[k])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </motion.div>
          )}
        </div>
      )}
    </motion.div>
  );
};

export default DatasetPreview;
