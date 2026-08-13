import { useState, useEffect } from "react";
import './Chat.css';
import UploadDocuments from './UploadDocuments';

function Chat({ sessionId, onClearChat }) {
    const [question, setQuestion] = useState("");
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const res = await fetch(`http://localhost:8000/chat_history?session_id=${sessionId}`);

                if (!res.ok) {
                    throw new Error("Failed to fetch chat history");
                }

                const data = await res.json();
                setMessages(data.messages);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchHistory();
    }, []);
    const sendMessage = async () => {
        if (!question) return;

        const userMessage = {
            role: "user",
            content: question
        };

        setMessages(prev => [...prev, userMessage]);

        try {
            const res = await fetch("http://localhost:8000/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    question: question,
                    session_id: sessionId
                })
            });

            const data = await res.json();

            const botMessage = {
                role: "assistant",
                content: data.answer
            };

            setMessages(prev => [...prev, botMessage]);

        } catch (err) {
            console.error(err);
        }

        setQuestion("");
    };

    const handleDeleteChat = async () => {
        const confirmDelete = window.confirm("Are you sure you want to clear the chat?");
        if (!confirmDelete) return;

        try {
            const response = await fetch("http://localhost:8000/delete_chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ session_id: sessionId }),
            });

            if (!response.ok) {
                throw new Error("Failed to delete chat");
            }
            setMessages([]);
            onClearChat();

        } catch (error) {
            console.error("Error deleting chat:", error);
        }
    };

    if (loading) return <div>Loading chat...</div>;
    return (

        <div className="chat-container">
            <button className="clear-chat-x" title="Clear chat" onClick={handleDeleteChat}>
                ✕
            </button>
            <div className="messages">
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.role}`}>
                        <div className="message-inner">
                            <div className="bubble">
                                {msg.content}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
            <div className="input-area">
                <div className="input-inner">
                    <input
                        type="text"
                        placeholder="Ask Something..."
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                    />
                    <button onClick={sendMessage}>Send</button>
                </div>
            </div>
        </div>

    );
}

export default Chat;