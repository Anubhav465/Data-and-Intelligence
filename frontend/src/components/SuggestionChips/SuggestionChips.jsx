import { motion } from 'framer-motion';
import { TrendingUp, Package, Users, Truck, Star, MapPin, CreditCard, BarChart2 } from 'lucide-react';
import './SuggestionChips.css';

const SUGGESTIONS = [
  { icon: TrendingUp, label: 'Top 10 revenue categories', color: '#22d3ee' },
  { icon: Truck, label: 'Average delivery delay by state', color: '#a855f7' },
  { icon: Users, label: 'Top 5 states by customer count', color: '#34d399' },
  { icon: Package, label: 'Monthly orders in 2018', color: '#f59e0b' },
  { icon: Star, label: 'Sellers with highest review score', color: '#ec4899' },
  { icon: MapPin, label: 'Late delivery percentage', color: '#06b6d4' },
  { icon: CreditCard, label: 'Most used payment methods', color: '#8b5cf6' },
  { icon: BarChart2, label: 'Average order value by category', color: '#10b981' },
];

const SuggestionChips = ({ onSelect }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, duration: 0.4 }}
      className="suggestions"
    >
      <p className="suggestions__label">Try asking</p>
      <div className="suggestions__grid">
        {SUGGESTIONS.map((s, i) => {
          const Icon = s.icon;
          return (
            <motion.button
              key={i}
              onClick={() => onSelect(s.label)}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.55 + i * 0.04 }}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.97 }}
              className="suggestions__chip"
              style={{
                '--chip-color': s.color,
                background: `${s.color}12`,
                borderColor: `${s.color}30`,
                color: s.color,
              }}
            >
              <Icon size={11} />
              {s.label}
            </motion.button>
          );
        })}
      </div>
    </motion.div>
  );
};

export default SuggestionChips;
