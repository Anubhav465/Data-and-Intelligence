import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';
import ChatInput from '../ChatInput/ChatInput';
import SuggestionChips from '../SuggestionChips/SuggestionChips';
import './WelcomeScreen.css';

const WelcomeScreen = ({ input, setInput, onSend, isLoading, selectedDatasets = [] }) => {
  const activeDataset = selectedDatasets[0] ?? null;
  const handleSuggest = (text) => {
    setInput(text);
  };

  return (
    <div className="welcome">
      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.55, ease: 'easeOut' }}
        className="welcome__container"
      >
        {/* Card */}
        <div className="welcome__card">
          {/* Grid overlay */}
          <div className="welcome__grid-overlay" />

          {/* Icon */}
          <motion.div
            animate={{ y: [0, -6, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            className="welcome__icon"
          >
            <Brain size={36} color="#22d3ee" />
            <motion.div
              className="welcome__icon-glow"
              animate={{ opacity: [0.3, 0.7, 0.3] }}
              transition={{ duration: 2.5, repeat: Infinity }}
            />
          </motion.div>

          {/* Heading */}
          <motion.h1
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="welcome__heading"
          >
            Neural Analytics
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="welcome__subtext"
          >
            {selectedDatasets.length > 1
              ? `Query ${selectedDatasets.length} datasets with natural language`
              : activeDataset
              ? `Query "${activeDataset.table_name.replace('user_table_', '')}" in natural language`
              : 'Ask anything about Olist e-commerce data'}
          </motion.p>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="welcome__powered"
          >
            Powered by Cohere AI + PostgreSQL
          </motion.p>

          {/* Input */}
          <ChatInput
            input={input}
            setInput={setInput}
            onSend={onSend}
            isLoading={isLoading}
            selectedDatasets={selectedDatasets}
            placeholder={
              selectedDatasets.length > 1
                ? `Ask anything across ${selectedDatasets.length} datasets…`
                : activeDataset
                ? `Ask anything about ${activeDataset.table_name.replace('user_table_', '')}…`
                : 'e.g. Top 10 product categories by revenue...'
            }
            autoFocus
            compact
          />

          {/* Suggestions */}
          <SuggestionChips onSelect={handleSuggest} />
        </div>
      </motion.div>
    </div>
  );
};

export default WelcomeScreen;
