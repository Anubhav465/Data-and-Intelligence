import { motion } from 'framer-motion';
import { Brain, Activity, Zap } from 'lucide-react';
import './Header.css';

const Header = ({ isThinking }) => {
  return (
    <motion.header
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className="header"
    >
      {/* Left — logo + title */}
      <div className="header__left">
        <div
          className="header__icon-wrap"
          style={{
            boxShadow: isThinking
              ? '0 0 20px rgba(34,211,238,0.5), 0 0 40px rgba(168,85,247,0.3)'
              : '0 0 10px rgba(34,211,238,0.2)',
          }}
        >
          <Brain size={18} color={isThinking ? '#a855f7' : '#22d3ee'} />
          {isThinking && (
            <motion.span
              className="header__icon-pulse"
              animate={{ opacity: [0.3, 0.8, 0.3] }}
              transition={{ duration: 1.2, repeat: Infinity }}
            />
          )}
        </div>

        <div className="header__title-group">
          <h1 className="header__title gradient-text">Neural Analytics</h1>
          <p className="header__subtitle">Olist E-Commerce AI</p>
        </div>
      </div>

      {/* Right — status indicators */}
      <div className="header__right">
        <motion.div
          className={`header__status ${isThinking ? 'header__status--thinking' : ''}`}
          animate={isThinking ? { scale: [1, 1.03, 1] } : { scale: 1 }}
          transition={{ duration: 1.5, repeat: isThinking ? Infinity : 0 }}
        >
          {isThinking ? (
            <>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
              >
                <Zap size={11} color="#a855f7" />
              </motion.div>
              <span className="header__status-text" style={{ color: '#c084fc' }}>
                Processing
              </span>
            </>
          ) : (
            <>
              <motion.div
                className="header__status-dot"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              <span className="header__status-text" style={{ color: '#67e8f9' }}>
                Ready
              </span>
            </>
          )}
        </motion.div>

        <div className="header__version">
          <Activity size={13} color="rgba(34,211,238,0.5)" />
          <span className="mono text-xs text-muted">v2.0</span>
        </div>
      </div>
    </motion.header>
  );
};

export default Header;
