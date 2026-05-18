import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, X, Loader2, CheckCircle, AlertCircle, Plus } from 'lucide-react';
import { uploadCSV } from '../../services/api';
import { useDataset } from '../../context/DatasetContext';
import './FileUpload.css';

const MAX_FILES = 5;
const MAX_BYTES = 40 * 1024 * 1024;

const formatBytes = (b) => {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(2)} MB`;
};

// status: 'pending' | 'uploading' | 'done' | 'error'
const makeEntry = (file) => ({
  id: `${file.name}-${file.size}-${Date.now()}`,
  file,
  name: file.name,
  size: file.size,
  status: 'pending',
  progress: 0,
  error: null,
});

const validate = (file) => {
  if (!file.name.toLowerCase().endsWith('.csv')) return 'Not a .csv file';
  if (file.size > MAX_BYTES) return 'Exceeds 40 MB limit';
  return null;
};

const FileUpload = () => {
  const { addDataset } = useDataset();
  const [entries, setEntries] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef(null);

  const pendingCount = entries.filter((e) => e.status === 'pending').length;
  const canAddMore = entries.filter((e) => e.status !== 'done').length < MAX_FILES;

  const addFiles = useCallback((files) => {
    const incoming = Array.from(files).slice(0, MAX_FILES);
    setEntries((prev) => {
      const existing = prev.filter((e) => e.status !== 'done');
      const slots = MAX_FILES - existing.length;
      if (slots <= 0) return prev;
      const toAdd = incoming.slice(0, slots).map((f) => {
        const err = validate(f);
        return err ? { ...makeEntry(f), status: 'error', error: err } : makeEntry(f);
      });
      return [...existing, ...toAdd];
    });
  }, []);

  const removeEntry = (id) =>
    setEntries((prev) => prev.filter((e) => e.id !== id));

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const handleUploadAll = async () => {
    const pending = entries.filter((e) => e.status === 'pending');
    if (!pending.length) return;
    setIsUploading(true);

    for (const entry of pending) {
      // Mark as uploading
      setEntries((prev) =>
        prev.map((e) => (e.id === entry.id ? { ...e, status: 'uploading', progress: 0 } : e))
      );

      try {
        const result = await uploadCSV(entry.file, (pct) => {
          setEntries((prev) =>
            prev.map((e) => (e.id === entry.id ? { ...e, progress: pct } : e))
          );
        });
        addDataset(result);
        setEntries((prev) =>
          prev.map((e) =>
            e.id === entry.id ? { ...e, status: 'done', progress: 100 } : e
          )
        );
      } catch (err) {
        setEntries((prev) =>
          prev.map((e) =>
            e.id === entry.id ? { ...e, status: 'error', error: err.message } : e
          )
        );
      }
    }

    setIsUploading(false);
    // Clear done entries after a short delay
    setTimeout(() => {
      setEntries((prev) => prev.filter((e) => e.status !== 'done'));
    }, 2000);
  };

  return (
    <div className="fu">
      {/* Drop zone — shown when entries are empty or more can be added */}
      {(entries.length === 0 || canAddMore) && (
        <div
          className={`fu__zone ${isDragging ? 'fu__zone--drag' : ''}`}
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onClick={() => !isUploading && inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv"
            multiple
            className="fu__hidden-input"
            onChange={(e) => { addFiles(e.target.files); e.target.value = ''; }}
          />
          <motion.div
            animate={isDragging ? { scale: 1.12 } : { scale: 1 }}
            className="fu__icon"
          >
            {entries.length > 0
              ? <Plus size={18} color={isDragging ? '#22d3ee' : '#64748b'} />
              : <Upload size={20} color={isDragging ? '#22d3ee' : '#64748b'} />
            }
          </motion.div>
          <p className="fu__label">
            {isDragging
              ? 'Drop here'
              : entries.length > 0
              ? `Add more (${entries.filter(e => e.status !== 'done').length}/${MAX_FILES})`
              : 'Drop CSV files or click'}
          </p>
          <p className="fu__sublabel">Up to {MAX_FILES} files · Max 40 MB each · .csv only</p>
        </div>
      )}

      {/* File list */}
      <AnimatePresence initial={false}>
        {entries.map((entry) => (
          <motion.div
            key={entry.id}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className={`fu__entry fu__entry--${entry.status}`}
          >
            <div className="fu__entry-row">
              <div className="fu__file-icon">
                {entry.status === 'done'    && <CheckCircle size={13} color="#34d399" />}
                {entry.status === 'error'   && <AlertCircle size={13} color="#f87171" />}
                {entry.status === 'uploading' && (
                  <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
                    <Loader2 size={13} color="#a855f7" />
                  </motion.div>
                )}
                {entry.status === 'pending' && <FileText size={13} color="#22d3ee" />}
              </div>

              <div className="fu__file-meta">
                <p className="fu__file-name">{entry.name}</p>
                <p className="fu__file-size">
                  {entry.status === 'error'
                    ? entry.error
                    : entry.status === 'done'
                    ? 'Loaded'
                    : entry.status === 'uploading'
                    ? `${entry.progress}%`
                    : formatBytes(entry.size)}
                </p>
              </div>

              {entry.status !== 'uploading' && (
                <button className="fu__remove" onClick={() => removeEntry(entry.id)}>
                  <X size={12} />
                </button>
              )}
            </div>

            {entry.status === 'uploading' && (
              <div className="fu__progress-track">
                <motion.div
                  className="fu__progress-fill"
                  initial={{ width: 0 }}
                  animate={{ width: `${entry.progress}%` }}
                />
              </div>
            )}
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Upload button */}
      {pendingCount > 0 && !isUploading && (
        <motion.button
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="fu__upload-btn"
          onClick={handleUploadAll}
        >
          <Upload size={13} />
          Upload {pendingCount} file{pendingCount > 1 ? 's' : ''}
        </motion.button>
      )}
    </div>
  );
};

export default FileUpload;
