import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Database, Trash2, CheckSquare, Square } from 'lucide-react';
import { useDataset } from '../../context/DatasetContext';
import { deleteTable } from '../../services/api';
import './DatasetSelector.css';

const DatasetSelector = () => {
  const { datasets, activeDataset, setActiveDataset, removeDataset, selectedTables, toggleTable, MAX_SELECTED } = useDataset();
  const [deleting, setDeleting] = useState(null);

  if (datasets.length === 0) return null;

  const handleDelete = async (e, tableName) => {
    e.stopPropagation();
    setDeleting(tableName);
    try {
      await deleteTable(tableName);
    } catch {
      // ignore — may already be gone
    } finally {
      removeDataset(tableName);
      setDeleting(null);
    }
  };

  const selectedCount = selectedTables.size;

  return (
    <div className="ds">
      <div className="ds__header">
        <p className="ds__label">YOUR DATASETS</p>
        {datasets.length > 1 && (
          <span className="ds__sel-count">
            {selectedCount}/{MAX_SELECTED} querying
          </span>
        )}
      </div>

      <div className="ds__list">
        <AnimatePresence initial={false}>
          {datasets.map((ds) => {
            const isActive = activeDataset?.table_name === ds.table_name;
            const isSelected = selectedTables.has(ds.table_name);
            const canSelect = isSelected || selectedCount < MAX_SELECTED;
            const shortName = ds.table_name.replace('user_table_', '');

            return (
              <motion.div
                key={ds.table_name}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8, height: 0, marginBottom: 0 }}
                transition={{ duration: 0.2 }}
                className={`ds__item ${isActive ? 'ds__item--active' : ''} ${isSelected ? 'ds__item--selected' : ''}`}
              >
                {/* Checkbox toggle */}
                <button
                  className={`ds__check ${isSelected ? 'ds__check--on' : ''} ${!canSelect ? 'ds__check--disabled' : ''}`}
                  onClick={() => canSelect && toggleTable(ds.table_name)}
                  title={isSelected ? 'Remove from query' : canSelect ? 'Add to query' : `Max ${MAX_SELECTED} datasets`}
                >
                  {isSelected
                    ? <CheckSquare size={14} color="#22d3ee" />
                    : <Square size={14} color={canSelect ? '#475569' : '#1e293b'} />
                  }
                </button>

                {/* Name + meta — click to preview */}
                <button
                  className="ds__item-body"
                  onClick={() => setActiveDataset(ds)}
                >
                  <div className={`ds__item-icon ${isActive ? 'ds__item-icon--active' : ''}`}>
                    <Database size={12} color={isActive ? '#22d3ee' : '#64748b'} />
                  </div>
                  <div className="ds__item-info">
                    <span className="ds__item-name" title={ds.table_name}>{shortName}</span>
                    <span className="ds__item-meta">{ds.row_count?.toLocaleString()} rows · {ds.columns?.length} cols</span>
                  </div>
                </button>

                {/* Delete */}
                <button
                  className="ds__delete"
                  onClick={(e) => handleDelete(e, ds.table_name)}
                  disabled={deleting === ds.table_name}
                  title="Delete dataset"
                >
                  {deleting === ds.table_name
                    ? <motion.div animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}>
                        <Trash2 size={11} color="#f87171" />
                      </motion.div>
                    : <Trash2 size={11} />
                  }
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {selectedCount > 1 && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="ds__multi-hint"
        >
          Chat will query all {selectedCount} datasets — JOINs applied automatically
        </motion.p>
      )}
    </div>
  );
};

export default DatasetSelector;
