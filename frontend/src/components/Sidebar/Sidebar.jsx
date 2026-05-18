import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, Upload, Database } from 'lucide-react';
import FileUpload from '../FileUpload/FileUpload';
import DatasetSelector from '../DatasetSelector/DatasetSelector';
import DatasetPreview from '../DatasetPreview/DatasetPreview';
import VersionHistory from '../VersionHistory/VersionHistory';
import { useDataset } from '../../context/DatasetContext';
import './Sidebar.css';

const Sidebar = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { activeDataset, datasets } = useDataset();

  return (
    <>
      {/* ── Sidebar panel ── */}
      <motion.aside
        animate={{ width: collapsed ? 0 : 264 }}
        transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        className="sidebar"
      >
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="sidebar__inner scrollbar-neural"
            >
              {/* Upload section */}
              <div className="sidebar__section">
                <div className="sidebar__section-head">
                  <Upload size={11} color="#64748b" />
                  <span>UPLOAD DATASET</span>
                </div>
                <FileUpload />
              </div>

              {/* Datasets list */}
              {datasets.length > 0 && (
                <>
                  <div className="sidebar__divider" />
                  <div className="sidebar__section">
                    <DatasetSelector />
                  </div>
                </>
              )}

              {/* Active dataset preview */}
              {activeDataset && (
                <>
                  <div className="sidebar__divider" />
                  <div className="sidebar__section">
                    <div className="sidebar__section-head">
                      <Database size={11} color="#64748b" />
                      <span>ACTIVE DATASET</span>
                    </div>
                    <DatasetPreview />
                  </div>
                </>
              )}

              {/* Olist notice */}
              {!activeDataset && datasets.length === 0 && (
                <div className="sidebar__empty">
                  <p className="sidebar__empty-text">
                    Upload a CSV to query your own data, or use the chat to explore the built-in Olist e-commerce dataset.
                  </p>
                </div>
              )}

              {/* Spacer pushes version history to bottom */}
              <div className="sidebar__spacer" />

              <div className="sidebar__divider" />

              {/* Version history */}
              <div className="sidebar__section">
                <VersionHistory />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.aside>

      {/* ── Collapse toggle ── */}
      <button
        className={`sidebar__toggle ${collapsed ? 'sidebar__toggle--collapsed' : ''}`}
        onClick={() => setCollapsed((p) => !p)}
        title={collapsed ? 'Open sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={13} /> : <ChevronLeft size={13} />}
      </button>
    </>
  );
};

export default Sidebar;
