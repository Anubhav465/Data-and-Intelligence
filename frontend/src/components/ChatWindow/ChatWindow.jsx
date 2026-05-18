import { useEffect, useRef } from 'react';
import { AnimatePresence } from 'framer-motion';
import MessageBubble from '../MessageBubble/MessageBubble';
import LoadingPulse from '../LoadingPulse/LoadingPulse';
import './ChatWindow.css';

const ChatWindow = ({ messages, isLoading }) => {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-window scrollbar-neural">
      <div className="chat-window__inner">
        <AnimatePresence initial={false}>
          {messages.map((msg, index) => (
            <MessageBubble key={index} message={msg} index={index} />
          ))}
        </AnimatePresence>

        <AnimatePresence>
          {isLoading && <LoadingPulse key="loading" />}
        </AnimatePresence>

        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default ChatWindow;
