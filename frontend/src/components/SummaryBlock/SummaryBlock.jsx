import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import './SummaryBlock.css';

const SummaryBlock = ({ summary }) => {
  if (!summary) return null;

  const bullets = summary
    .split('\n')
    .map(l => l.trim())
    .filter(Boolean)
    .map(l => l.replace(/^[•\-\*\d\.]+\s*/, ''));

  if (bullets.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="summary-block"
    >
      <div className="summary-block__header">
        <Sparkles size={13} color="#22d3ee" />
        <span className="summary-block__label">AI Summary</span>
      </div>
      <div className="summary-block__list">
        {bullets.map((bullet, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08, duration: 0.25 }}
            className="summary-block__item"
          >
            <span className="summary-block__dot" />
            <span>{bullet}</span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};

export default SummaryBlock;
