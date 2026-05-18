import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Table2, ChevronDown, ChevronRight } from 'lucide-react';
import './DataTable.css';

const DataTable = ({ data }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!data || !data.rows || data.rows.length === 0) return null;

  return (
    <div className="datatable">
      <button
        onClick={() => setIsOpen(v => !v)}
        className="datatable__toggle"
      >
        <span className="datatable__toggle-icon">
          <Table2 size={11} color="#22d3ee" />
        </span>
        <span>
          {isOpen ? 'Hide' : 'Show'} Results
          <span className="datatable__count">
            {data.row_count ?? data.rows.length}
          </span>
        </span>
        {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            <div className="datatable__wrap scrollbar-neural">
              <table className="datatable__table">
                <thead>
                  <tr>
                    <th className="datatable__th datatable__th--num">#</th>
                    {data.columns.map((col, i) => (
                      <th key={i} className="datatable__th">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((row, i) => (
                    <tr key={i} className={`datatable__tr ${i % 2 === 0 ? 'datatable__tr--even' : ''}`}>
                      <td className="datatable__td datatable__td--num">{i + 1}</td>
                      {data.columns.map((col, j) => {
                        const val = row[col];
                        const isNum = typeof val === 'number';
                        return (
                          <td
                            key={j}
                            className={`datatable__td ${isNum ? 'datatable__td--numeric' : ''}`}
                          >
                            {val !== null && val !== undefined
                              ? isNum
                                ? typeof val === 'number' && !Number.isInteger(val)
                                  ? val.toFixed(2)
                                  : val.toLocaleString()
                                : String(val)
                              : <span className="datatable__null">—</span>}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default DataTable;
