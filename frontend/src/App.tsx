import { useEffect } from "react";
import { ChatPanel } from "./components/ChatPanel";
import { DataVintage } from "./components/DataVintage";
import { useChat } from "./hooks/useChat";
import "./App.css";

function App() {
  const {
    messages,
    isLoading,
    error,
    health,
    sendMessage,
    clearChat,
    fetchHealth,
    updateSettings,
  } = useChat();

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__title">
          <span className="app__icon">✈</span>
          <h1>Airport Investment Intelligence</h1>
        </div>
        <div className="app__header-right">
          <DataVintage health={health} onUpdateSettings={updateSettings} />
          {messages.length > 0 && (
            <button className="app__clear" onClick={clearChat} title="New conversation">
              New Chat
            </button>
          )}
        </div>
      </header>
      <main className="app__main">
        <ChatPanel
          messages={messages}
          isLoading={isLoading}
          error={error}
          onSend={sendMessage}
        />
      </main>
    </div>
  );
}

export default App;
