import { useState } from "react";
import { useRef } from "react";
import UploadDocuments from "./components/UploadDocuments";
import Chat from "./components/Chat";
import Header from "./components/Header"
import "./App.css";

function App() {
  const sessionIdRef = useRef(null);
  const [documentReset, setDocumentReset] = useState(0);

  if (!sessionIdRef.current) {
    let stored = localStorage.getItem("session_id");

    if (!stored) {
      stored = crypto.randomUUID();
      localStorage.setItem("session_id", stored);
    }

    sessionIdRef.current = stored;
  }

  return (
    <div className="app-container">
      <Header />
      <UploadDocuments sessionId={sessionIdRef.current}
        documentReset={documentReset}
      />
      <Chat sessionId={sessionIdRef.current}
        onClearChat={() => setDocumentReset(prev => prev + 1)}
      />
    </div>
  );
}

export default App;