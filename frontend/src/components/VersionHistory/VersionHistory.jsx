import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Rocket, ChevronDown, ChevronUp, CheckCircle2, Clock } from 'lucide-react';
import './VersionHistory.css';

const CURRENT_VERSION = '2.0.0';

const UPCOMING = {
  version: '2.0.1',
  label: 'Coming Soon',
  features: [
    { id: 1,  icon: '🕘', title: 'Query History & Favorites',    desc: 'Save and share frequently-asked questions across users' },
    { id: 2,  icon: '📊', title: 'Column Profiling',             desc: 'Auto-generate summaries — cardinality, missing %, distribution' },
    { id: 3,  icon: '🔗', title: 'Natural Language Joins',       desc: 'Automatically detects FK relationships from plain-English questions' },
    { id: 4,  icon: '🛢️', title: 'Real-time Data Integration',  desc: 'Connect to live PostgreSQL, MySQL, BigQuery without CSV upload' },
    { id: 5,  icon: '🏷️', title: 'Data Quality Badges',         desc: 'Auto-detect anomalies — duplicates, outliers, schema drift' },
    { id: 6,  icon: '🌐', title: 'Multi-language SQL',           desc: 'Generate queries for T-SQL, BigQuery, Snowflake dialects' },
    { id: 7,  icon: '📱', title: 'Mobile App',                   desc: 'React Native version for on-the-go data exploration' },
    { id: 8,  icon: '👥', title: 'Team Collaboration',           desc: 'Shared workspaces, query comments, and audit logs' },
    { id: 9,  icon: '📈', title: 'Advanced Visualizations',      desc: 'Dashboards, heatmaps, and geo maps via extended chart libraries' },
    { id: 10, icon: '🤖', title: 'Fine-tuned Model',             desc: 'Custom LLM trained on domain-specific SQL patterns for higher accuracy' },
  ],
};

const RELEASED = {
  version: '2.0.0',
  label: 'Current',
  features: [
    'Multi-file CSV upload (up to 5 × 40 MB)',
    'Multi-table natural language queries with automatic JOINs',
    'FAISS semantic schema search for precise SQL generation',
    'Auto-fix pipeline — LLM self-corrects failing queries',
    'Bar, line, pie, histogram & doughnut chart auto-selection',
    'Drag-and-drop sidebar with dataset preview & type badges',
    'Data cleaning report (nulls, duplicates, type coercions)',
    'Strict SQL security — SELECT-only, injection guards',
  ],
};

const VersionHistory = () => {
  const [open, setOpen] = useState(false);

  return (
    <div className="vh">
      {/* Toggle button */}
      <button className="vh__toggle" onClick={() => setOpen((p) => !p)}>
        <div className="vh__toggle-left">
          <Rocket size={12} color="#a855f7" />
          <span className="vh__toggle-label">Version History</span>
        </div>
        <div className="vh__badges">
          <span className="vh__badge vh__badge--current">v{CURRENT_VERSION}</span>
          {open ? <ChevronUp size={12} color="#64748b" /> : <ChevronDown size={12} color="#64748b" />}
        </div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="vh__panel"
          >
            {/* ── Current release ── */}
            <div className="vh__release">
              <div className="vh__release-header">
                <CheckCircle2 size={13} color="#34d399" />
                <span className="vh__release-title">v{RELEASED.version}</span>
                <span className="vh__pill vh__pill--released">Released</span>
              </div>
              <ul className="vh__list">
                {RELEASED.features.map((f, i) => (
                  <li key={i} className="vh__item vh__item--done">
                    <span className="vh__dot vh__dot--done" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>

            <div className="vh__sep" />

            {/* ── Upcoming release ── */}
            <div className="vh__release">
              <div className="vh__release-header">
                <Clock size={13} color="#a855f7" />
                <span className="vh__release-title">v{UPCOMING.version}</span>
                <span className="vh__pill vh__pill--upcoming">{UPCOMING.label}</span>
              </div>
              <ul className="vh__list">
                {UPCOMING.features.map((f) => (
                  <motion.li
                    key={f.id}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: f.id * 0.03 }}
                    className="vh__item vh__item--upcoming"
                  >
                    <span className="vh__feature-icon">{f.icon}</span>
                    <div>
                      <p className="vh__feature-title">{f.title}</p>
                      <p className="vh__feature-desc">{f.desc}</p>
                    </div>
                  </motion.li>
                ))}
              </ul>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default VersionHistory;
