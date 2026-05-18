import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Loader2, Zap, Database } from 'lucide-react';
import './ChatInput.css';

const ChatInput = ({ input, setInput, onSend, isLoading, placeholder, autoFocus, compact, selectedDatasets = [], activeDataset }) => {
  // Support legacy activeDataset prop (WelcomeScreen compact mode)
  const _selected = selectedDatasets.length > 0
    ? selectedDatasets
    : activeDataset ? [activeDataset] : [];
  const textareaRef = useRef(null);

  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }, [input]);

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const canSend = input.trim() && !isLoading;

  return (
    <div className={compact ? 'chat-input-compact' : 'chat-input-wrapper'}>
      <div className={compact ? 'chat-input-inner-compact' : 'chat-input-inner'}>

        {/* Active dataset badge */}
        <AnimatePresence>
          {_selected.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              className="chat-input-dataset-badge"
            >
              <Database size={10} color="#22d3ee" />
              {_selected.length === 1 ? (
                <>
                  <span>Active: <strong>{_selected[0].table_name.replace('user_table_', '')}</strong></span>
                  <span className="chat-input-badge-rows">{_selected[0].row_count?.toLocaleString()} rows</span>
                </>
              ) : (
                <span>
                  Querying <strong>{_selected.length} datasets</strong>
                  {' · '}{_selected.map(d => d.table_name.replace('user_table_', '')).join(', ')}
                </span>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        <motion.div
          className="chat-input-box"
          animate={
            isLoading
              ? {
                  boxShadow: [
                    '0 0 0 1px rgba(168,85,247,0.3)',
                    '0 0 18px rgba(168,85,247,0.4)',
                    '0 0 0 1px rgba(168,85,247,0.3)',
                  ],
                }
              : {}
          }
          transition={{ duration: 1.5, repeat: isLoading ? Infinity : 0 }}
        >
          {/* Left accent bar */}
          <div
            className="chat-input-accent"
            style={{
              background: isLoading
                ? 'linear-gradient(to bottom, #a855f7, #22d3ee)'
                : _selected.length > 1
                ? 'linear-gradient(to bottom, #a855f7, #34d399)'
                : _selected.length === 1
                ? 'linear-gradient(to bottom, #34d399, #22d3ee)'
                : 'linear-gradient(to bottom, #22d3ee, #7c3aed)',
            }}
          />

          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={placeholder || 'Ask about sales, products, deliveries...'}
            rows={1}
            disabled={isLoading}
            className="chat-input-textarea"
          />

          {/* Send / Loading button */}
          <AnimatePresence mode="wait">
            {isLoading ? (
              <motion.div
                key="loading"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                className="chat-input-btn chat-input-btn--loading"
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
                >
                  <Loader2 size={16} color="#a855f7" />
                </motion.div>
              </motion.div>
            ) : (
              <motion.button
                key="send"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                whileHover={canSend ? { scale: 1.08 } : {}}
                whileTap={canSend ? { scale: 0.92 } : {}}
                onClick={onSend}
                disabled={!canSend}
                className={`chat-input-btn ${canSend ? 'chat-input-btn--active' : 'chat-input-btn--disabled'}`}
              >
                {canSend ? (
                  <Zap size={15} color="white" />
                ) : (
                  <Send size={14} color="rgba(255,255,255,0.25)" />
                )}
              </motion.button>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Hint */}
        {!compact && (
          <p className="chat-input-hint">
            Press <kbd>Enter</kbd> to send &nbsp;·&nbsp;
            <kbd>Shift+Enter</kbd> for newline
          </p>
        )}
      </div>
    </div>
  );
};

export default ChatInput;
