import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Code2, ChevronDown, ChevronRight, Copy, Check, Clock, Database } from 'lucide-react';
import './SqlViewer.css';

const SqlViewer = ({ sql, meta }) => {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!sql) return null;

  const handleCopy = async (e) => {
    e.stopPropagation();
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  // Basic SQL keyword highlight
  const highlighted = sql
    .replace(
      /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|ON|GROUP BY|ORDER BY|LIMIT|HAVING|WITH|AS|DISTINCT|COUNT|SUM|AVG|MAX|MIN|AND|OR|NOT|IN|LIKE|BETWEEN|IS|NULL|CASE|WHEN|THEN|ELSE|END|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TABLE|VIEW|INDEX|SCHEMA|DESC|ASC)\b/gi,
      (m) => `<span class="sql-keyword">${m}</span>`
    )
    .replace(/('[^']*')/g, '<span class="sql-string">$1</span>')
    .replace(/(\b\d+(?:\.\d+)?\b)/g, '<span class="sql-number">$1</span>');

  return (
    <div className="sql-viewer">
      <button
        onClick={() => setOpen(v => !v)}
        className="sql-viewer__toggle"
      >
        <span className="sql-viewer__toggle-icon">
          <Code2 size={11} color="#a855f7" />
        </span>
        <span>Generated SQL</span>
        {meta?.source && (
          <span className="sql-viewer__source">{meta.source}</span>
        )}
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.22, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            <div className="sql-viewer__panel">
              {/* Toolbar */}
              <div className="sql-viewer__toolbar">
                <div className="sql-viewer__toolbar-left">
                  <Database size={11} color="#a855f7" />
                  <span className="sql-viewer__lang">SQL</span>
                  {meta?.execution_time_ms && (
                    <span className="sql-viewer__time">
                      <Clock size={9} />
                      {Math.round(meta.execution_time_ms)}ms
                    </span>
                  )}
                </div>
                <button onClick={handleCopy} className={`sql-viewer__copy ${copied ? 'sql-viewer__copy--done' : ''}`}>
                  {copied ? <Check size={11} /> : <Copy size={11} />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>

              {/* Code */}
              <div className="sql-viewer__code scrollbar-neural">
                <pre
                  className="sql-viewer__pre"
                  dangerouslySetInnerHTML={{ __html: highlighted }}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default SqlViewer;
