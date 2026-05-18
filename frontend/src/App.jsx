import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

import NeuralBackground from './components/NeuralBackground/NeuralBackground';
import Header from './components/Header/Header';
import WelcomeScreen from './components/WelcomeScreen/WelcomeScreen';
import ChatWindow from './components/ChatWindow/ChatWindow';
import ChatInput from './components/ChatInput/ChatInput';
import Sidebar from './components/Sidebar/Sidebar';

import { DatasetProvider, useDataset } from './context/DatasetContext';
import { askQuestion } from './services/api';

// ── Inner app (needs DatasetContext) ────────────────────────────────────────
function AppInner() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);

  const { activeDataset, selectedDatasets } = useDataset();

  const handleSend = async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    setMessages((prev) => [...prev, { type: 'user', content: question }]);
    setInput('');
    setHasStarted(true);
    setIsLoading(true);

    try {
      const tableNames = selectedDatasets.length > 0
        ? selectedDatasets.map((d) => d.table_name)
        : null;
      const data = await askQuestion(question, tableNames);
      setMessages((prev) => [...prev, { type: 'ai', content: data }]);
    } catch (err) {
      const errorMsg = err?.message || 'An unexpected error occurred. Please try again.';
      setMessages((prev) => [
        ...prev,
        { type: 'ai', content: { summary: errorMsg, _isError: true } },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <NeuralBackground isThinking={isLoading} />

      <div className="app-layer app-layer--row">
        {/* ── Left sidebar ── */}
        <Sidebar />

        {/* ── Main content ── */}
        <div className="app-main">
          {/* Header always shown in sidebar layout */}
          <Header isThinking={isLoading} selectedDatasets={selectedDatasets} />

          {/* Chat area */}
          <AnimatePresence mode="wait">
            {!hasStarted ? (
              <motion.div
                key="welcome"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                transition={{ duration: 0.3 }}
                className="app-view"
              >
                <WelcomeScreen
                  input={input}
                  setInput={setInput}
                  onSend={handleSend}
                  isLoading={isLoading}
                  selectedDatasets={selectedDatasets}
                />
              </motion.div>
            ) : (
              <motion.div
                key="chat"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.25 }}
                className="app-view"
              >
                <ChatWindow messages={messages} isLoading={isLoading} />
                <ChatInput
                  input={input}
                  setInput={setInput}
                  onSend={handleSend}
                  isLoading={isLoading}
                  selectedDatasets={selectedDatasets}
                  placeholder={
                    selectedDatasets.length === 1
                      ? `Ask anything about ${selectedDatasets[0].table_name.replace('user_table_', '')}…`
                      : selectedDatasets.length > 1
                      ? `Ask anything across ${selectedDatasets.length} datasets…`
                      : 'Ask about sales, deliveries, products…'
                  }
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

// ── Root with context provider ───────────────────────────────────────────────
export default function App() {
  return (
    <DatasetProvider>
      <AppInner />
    </DatasetProvider>
  );
}
