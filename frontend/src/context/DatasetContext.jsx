import { createContext, useContext, useState, useCallback, useMemo } from 'react';

const DatasetContext = createContext(null);

const MAX_SELECTED = 5;

export function DatasetProvider({ children }) {
  const [datasets, setDatasets] = useState([]);
  const [activeDataset, setActiveDataset] = useState(null);
  // Set of table_name strings currently selected for querying
  const [selectedTables, setSelectedTables] = useState(new Set());

  const addDataset = useCallback((dataset) => {
    setDatasets((prev) => {
      const idx = prev.findIndex((d) => d.table_name === dataset.table_name);
      if (idx !== -1) {
        const updated = [...prev];
        updated[idx] = dataset;
        return updated;
      }
      return [dataset, ...prev];
    });
    setActiveDataset(dataset);
    // Auto-select the newly uploaded table (if under limit)
    setSelectedTables((prev) => {
      if (prev.size < MAX_SELECTED) {
        return new Set([...prev, dataset.table_name]);
      }
      return prev;
    });
  }, []);

  const removeDataset = useCallback((tableName) => {
    setDatasets((prev) => prev.filter((d) => d.table_name !== tableName));
    setActiveDataset((prev) => (prev?.table_name === tableName ? null : prev));
    setSelectedTables((prev) => {
      const next = new Set(prev);
      next.delete(tableName);
      return next;
    });
  }, []);

  const toggleTable = useCallback((tableName) => {
    setSelectedTables((prev) => {
      const next = new Set(prev);
      if (next.has(tableName)) {
        next.delete(tableName);
      } else if (next.size < MAX_SELECTED) {
        next.add(tableName);
      }
      return next;
    });
  }, []);

  // Derived: full dataset objects for selected table names (in order)
  const selectedDatasets = useMemo(
    () => datasets.filter((d) => selectedTables.has(d.table_name)),
    [datasets, selectedTables],
  );

  return (
    <DatasetContext.Provider
      value={{
        datasets,
        activeDataset,
        setActiveDataset,
        addDataset,
        removeDataset,
        selectedTables,
        toggleTable,
        selectedDatasets,
        MAX_SELECTED,
      }}
    >
      {children}
    </DatasetContext.Provider>
  );
}

export const useDataset = () => {
  const ctx = useContext(DatasetContext);
  if (!ctx) throw new Error('useDataset must be used within DatasetProvider');
  return ctx;
};
