import { motion } from 'framer-motion';
import { User, Bot, Clock, AlertTriangle } from 'lucide-react';
import SummaryBlock from '../SummaryBlock/SummaryBlock';
import ChartRenderer from '../ChartRenderer/ChartRenderer';
import DataTable from '../DataTable/DataTable';
import SqlViewer from '../SqlViewer/SqlViewer';
import './MessageBubble.css';

const formatTime = () =>
  new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

const MessageBubble = ({ message }) => {
  const time = formatTime();

  // ── User bubble ──────────────────────────────
  if (message.type === 'user') {
    return (
      <motion.div
        initial={{ opacity: 0, x: 20, y: 6 }}
        animate={{ opacity: 1, x: 0, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="msg msg--user"
      >
        <div className="msg__user-content">
          <motion.div whileHover={{ scale: 1.01 }} className="msg__user-bubble">
            {message.content}
          </motion.div>
          <span className="msg__time msg__time--right">
            <Clock size={9} />
            {time}
          </span>
        </div>
        <div className="msg__avatar msg__avatar--user">
          <User size={13} color="white" />
        </div>
      </motion.div>
    );
  }

  // ── AI bubble ────────────────────────────────
  const d = message.content;
  // Explicit error flag from frontend catch, OR heuristic for backend error responses
  const isError = d._isError || (!d.data && !d.chart_spec && d.summary && !d.summary.includes('•') && !d.summary.includes('\n'));

  return (
    <motion.div
      initial={{ opacity: 0, x: -16, y: 8 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="msg msg--ai"
    >
      {/* AI avatar */}
      <motion.div
        animate={{
          boxShadow: isError
            ? [
                '0 0 8px rgba(248,113,113,0.3)',
                '0 0 18px rgba(248,113,113,0.5)',
                '0 0 8px rgba(248,113,113,0.3)',
              ]
            : [
                '0 0 8px rgba(34,211,238,0.3)',
                '0 0 18px rgba(34,211,238,0.5)',
                '0 0 8px rgba(34,211,238,0.3)',
              ],
        }}
        transition={{ duration: 2.5, repeat: Infinity }}
        className={`msg__avatar msg__avatar--ai ${isError ? 'msg__avatar--error' : ''}`}
      >
        {isError ? <AlertTriangle size={15} color="#f87171" /> : <Bot size={15} color="#22d3ee" />}
      </motion.div>

      {/* Content card */}
      <div className="msg__ai-body">
        <motion.div className={`msg__ai-card ${isError ? 'msg__ai-card--error' : ''}`}>
          {/* Top accent bar */}
          <div className={`msg__accent-bar ${isError ? 'msg__accent-bar--error' : ''}`} />

          <div className="msg__ai-inner">
            {/* Error state */}
            {d.summary && isError && (
              <div className="msg__error-block">
                <AlertTriangle size={16} color="#f87171" />
                <p className="msg__error">{d.summary}</p>
              </div>
            )}

            {/* Summary */}
            {d.summary && !isError && <SummaryBlock summary={d.summary} />}

            {/* Chart */}
            {d.chart_spec && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                <ChartRenderer chartSpec={d.chart_spec} />
              </motion.div>
            )}

            {/* Table */}
            {d.data && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.25 }}
              >
                <DataTable data={d.data} />
              </motion.div>
            )}

            {/* SQL */}
            {d.sql && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                <SqlViewer sql={d.sql} meta={d.meta} />
              </motion.div>
            )}
          </div>
        </motion.div>

        <span className="msg__time msg__time--left">
          <Clock size={9} />
          {time}
          {d.meta?.execution_time_ms && (
            <span className="msg__exec-time">
              &nbsp;·&nbsp;{Math.round(d.meta.execution_time_ms)}ms
            </span>
          )}
        </span>
      </div>
    </motion.div>
  );
};

export default MessageBubble;
