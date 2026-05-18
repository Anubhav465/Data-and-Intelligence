import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';
import './LoadingPulse.css';

const LoadingPulse = () => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      className="loading-pulse"
    >
      {/* Brain icon */}
      <motion.div
        animate={{ scale: [1, 1.15, 1] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        className="loading-pulse__icon"
      >
        <Brain size={15} color="#a855f7" />
      </motion.div>

      {/* Dots + text */}
      <div className="loading-pulse__content">
        <div className="loading-pulse__dots">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="loading-pulse__dot"
              animate={{ opacity: [0.2, 1, 0.2], scale: [0.8, 1.2, 0.8] }}
              transition={{
                duration: 1.2,
                repeat: Infinity,
                delay: i * 0.18,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
        <span className="loading-pulse__text">Processing query…</span>
      </div>
    </motion.div>
  );
};

export default LoadingPulse;
