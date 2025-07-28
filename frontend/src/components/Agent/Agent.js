import React, { useState, useEffect, useRef } from "react";
import "./AgentNew.css";
import NavHead from "../Home/NavHead/NavHead.js";
import { motion } from "framer-motion";
import Card from "react-bootstrap/Card";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowRight,
  faPaperPlane,
  faHistory,
  faMessage,
  faTimes,
  faCog,
  faClipboardList,
  faCogs,
  faBolt, // --- NEW ---: Icon for running tool
  faCheck, // --- NEW ---: Icon for completed tool
} from "@fortawesome/free-solid-svg-icons";
import { Link, useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown"; // --- NEW ---: Import for rendering markdown

// --- ADK INTEGRATION: API Configuration ---
const ADK_API_BASE_URL = "http://0.0.0.0:9999";
const ADK_APP_NAME = "src";
const getUserId = () => {
  let userId = localStorage.getItem("adk-user-id");
  if (!userId) {
    userId = `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem("adk-user-id", userId);
  }
  return userId;
};
const ADK_USER_ID = getUserId();
// --- END ADK INTEGRATION ---


// --- NEW ---: Component for displaying tool/function calls
const ToolCallMessage = ({ toolName, status }) => {
  const isRunning = status === 'running';

  return (
    <div className={`tool-call-message ${isRunning ? 'tool-call-running' : 'tool-call-completed'}`}>
      <div className="tool-call-icon">
        <FontAwesomeIcon icon={isRunning ? faBolt : faCheck} />
      </div>
      <span className="tool-call-name">{toolName}</span>
    </div>
  );
};
// --- END NEW COMPONENT ---


const Agent = () => {
  // --- Hooks ---
  const navigate = useNavigate();

  // --- States ---
  const [formColor, setFormColor] = useState("");
  const [activeButton, setActiveButton] = useState(null);
  const [userInput, setUserInput] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [showFinalOptions, setShowFinalOptions] = useState(false);
  const [finalPayload, setFinalPayload] = useState(null);

  // --- MODIFIED ---: Messages state now includes a 'type' property
  const [messages, setMessages] = useState([
    {
      type: "text",
      functionCall: "", 
      sender: "bot",
      text: "Hello, I am Acube! Let's Get Started!",
    },
  ]);
  const [chatHistory, setChatHistory] = useState([]);

  // --- Refs ---
  const chatContainerRef = useRef(null);
  const inputRef = useRef(null);

  // --- Effects ---
  useEffect(() => {
    const fetchChatHistory = async () => {
      try {
        const response = await fetch(`${ADK_API_BASE_URL}/apps/${ADK_APP_NAME}/users/${ADK_USER_ID}/sessions`);
        if (!response.ok) throw new Error(`Failed to fetch sessions: ${response.statusText}`);
        const sessions = await response.json();
        const history = sessions.map(session => {
          const firstUserEvent = session.events.find(event => event.author === 'user' && event.content?.parts?.[0]?.text);
          const title = firstUserEvent ? firstUserEvent.content.parts[0].text.substring(0, 40) + '...' : "Untitled Chat";
          return { id: session.id, title: title, timestamp: session.lastUpdateTime * 1000 };
        }).sort((a, b) => b.timestamp - a.timestamp);
        setChatHistory(history);
      } catch (error) {
        console.error("Failed to load chat history from ADK:", error);
      }
    };
    fetchChatHistory();
  }, []);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);


  // --- Functions ---
  
  // --- MODIFIED ---: Helper now creates messages with the new structure
  const formatEventsToMessages = (events = []) => {
    const formattedMessages = [];
    events.forEach(event => {
      if (event.content && event.content.parts) {
        event.content.parts.forEach(part => {
          if (part.text) {
            formattedMessages.push({
              type: 'text', // <-- Add type
              sender: event.author === 'user' ? 'user' : 'bot',
              text: part.text,
            });
          }
          // Note: This helper currently doesn't format tool calls from historical events.
          // This could be an enhancement for later if needed.
        });
      }
    });
    return formattedMessages;
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !isLoading) {
      handleSendMessage();
    }
  };

  const handleButtonClick = async (color, buttonName) => {
    const serviceName = buttonName === "blue" ? "CI/CD Setup" : buttonName === "red" ? "Modify Resources" : "Observability";
    await startNewChat(`I'd like to start the ${serviceName} process.`);
    setFormColor(`${color}-form`);
    setActiveButton(buttonName);
    inputRef.current?.focus();
  };


  // --- MODIFIED ---: Main interaction logic now handles text and tool_call parts
  const handleSendMessage = async () => {
    if (!userInput.trim() || isLoading) return;

    if (!currentSessionId) {
      await startNewChat(userInput.trim());
      return;
    }

    const messageText = userInput.trim();
    setUserInput("");
    setMessages(prev => [...prev, { type: 'text', sender: 'user', text: messageText }]); // Add user message with type
    setIsLoading(true);
    setShowFinalOptions(false);

    try {
      const response = await fetch(`${ADK_API_BASE_URL}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          appName: ADK_APP_NAME,
          userId: ADK_USER_ID,
          sessionId: currentSessionId,
          newMessage: { parts: [{ text: messageText }], role: "user" },
        }),
      });

      if (!response.ok) throw new Error(`API Error: ${response.statusText}`);

      const responseEvents = await response.json();
      
      responseEvents.forEach(event => {
        if (event.author !== 'user' && event.content?.parts) {
          event.content.parts.forEach(part => {
            // Handle standard text responses
            console.log("PARTS : ",part)
            if (part.text) {
              setMessages(prev => [...prev, { type: 'text', sender: 'bot', text: part.text }]);
            }

            // Handle new tool call responses
            if (part.functionCall && part.functionCall.name) {
              const toolName = part.functionCall.name;
              const runningMessage = {
                type: 'tool_call',
                toolName: "Tool Called : "+toolName,
                status: 'running',
                id: `${toolName}-${Date.now()}`
              };
              setMessages(prev => [...prev, runningMessage]);

              // Simulate completion after a delay for visual effect
              setTimeout(() => {
                setMessages(prev => prev.map(msg =>
                  msg.id === runningMessage.id ? { ...msg, status: 'completed' } : msg
                ));
              }, 1500);
            }
          });
        }

        if (event.customMetadata?.status === 'data_collection_complete') {
          setShowFinalOptions(true);
          setFinalPayload(event.customMetadata.payload);
        }
      });

    } catch (error) {
      console.error("Error sending message to ADK:", error);
      setMessages(prev => [...prev, { type: 'text', sender: 'bot', text: `Sorry, an error occurred: ${error.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  const loadChatHistory = async (sessionSummary) => {
    if (!sessionSummary || !sessionSummary.id) return;
    setIsLoading(true);
    setIsSidebarOpen(false);
    try {
      const response = await fetch(`${ADK_API_BASE_URL}/apps/${ADK_APP_NAME}/users/${ADK_USER_ID}/sessions/${sessionSummary.id}`);
      if (!response.ok) throw new Error(`Failed to fetch session ${sessionSummary.id}`);
      const sessionData = await response.json();
      setCurrentSessionId(sessionData.id);
      setMessages(formatEventsToMessages(sessionData.events));
      setActiveButton(null);
      setFormColor("");
      setShowFinalOptions(false);
      setFinalPayload(null);
    } catch (error) {
      console.error("Failed to load session:", error);
      setMessages([{ type: 'text', sender: 'bot', text: "Could not load the selected chat history." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const startNewChat = async (firstUserMessage = null) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${ADK_API_BASE_URL}/apps/${ADK_APP_NAME}/users/${ADK_USER_ID}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (!response.ok) throw new Error(`Failed to create session: ${response.statusText}`);
      const newSession = await response.json();
      
      setCurrentSessionId(newSession.id);
      // --- MODIFIED ---: Use new message structure
      setMessages([{ type: 'text', sender: "bot", text: "Hello, I am Acube! Let's Get Started!" }]);
      setActiveButton(null);
      setFormColor("");
      setShowFinalOptions(false);
      setFinalPayload(null);
      setIsSidebarOpen(false);
      setUserInput("");

      setChatHistory(prev => [{
        id: newSession.id,
        title: "New Conversation",
        timestamp: newSession.lastUpdateTime * 1000,
      }, ...prev].sort((a, b) => b.timestamp - a.timestamp));

      if (firstUserMessage) {
        setUserInput(firstUserMessage);
        setTimeout(() => handleSendMessage(), 0);
      }
    } catch (error) {
      console.error("Error starting new chat:", error);
      setMessages([{ type: 'text', sender: "bot", text: `Error: Could not start a new session. ${error.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteChatHistory = async (sessionIdToDelete, e) => {
    e.stopPropagation();
    try {
      const response = await fetch(`${ADK_API_BASE_URL}/apps/${ADK_APP_NAME}/users/${ADK_USER_ID}/sessions/${sessionIdToDelete}`, { method: 'DELETE' });
      if (!response.ok) throw new Error(`Failed to delete session: ${response.statusText}`);
      setChatHistory(prevHistory => prevHistory.filter(chat => chat.id !== sessionIdToDelete));
      if (currentSessionId === sessionIdToDelete) await startNewChat();
    } catch (error) {
      console.error("Error deleting session:", error);
    }
  };

  // --- Button Handlers
  const handleNavigateToReviewDashboard = () => {
    navigate('/review-dashboard', { state: { ...finalPayload, serviceType: activeButton } });
  };
  const handleNavigateToMain = () => {
    navigate('/main', { state: { ...finalPayload, serviceType: activeButton } });
  };
  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  // --- JSX Return ---
  return (
    <div className="agent-fullscreen">
      <NavHead />
      <button className="sidebar-toggle-btn" onClick={toggleSidebar} title={isSidebarOpen ? "Close History" : "Open History"}>
        <FontAwesomeIcon icon={isSidebarOpen ? faTimes : faHistory} />
      </button>
      <Link to="/settings" className="settings-toggle-btn" title="Settings">
        <FontAwesomeIcon icon={faCog} />
      </Link>
      <div className={`chat-sidebar ${isSidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <h3>Chat History</h3>
          <button className="new-chat-btn" onClick={() => startNewChat()} title="Start New Chat"> New Chat </button>
        </div>
        <div className="sidebar-content">
          {chatHistory.length === 0 ? <p className="no-history">No chat history yet</p> : (
            <ul className="history-list">
              {chatHistory.map(chat => (
                <li key={chat.id} onClick={() => loadChatHistory(chat)} className="history-item" title={`Load: ${chat.title}`}>
                  <div className="history-item-content">
                    <FontAwesomeIcon icon={faMessage} className="history-icon" />
                    <div className="history-details">
                      <span className="history-title">{chat.title || "Untitled Chat"}</span>
                      <span className="history-date">{new Date(chat.timestamp).toLocaleDateString()} {new Date(chat.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                  <button className="delete-history-btn" onClick={(e) => deleteChatHistory(chat.id, e)} title="Delete conversation"><FontAwesomeIcon icon={faTimes} /></button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className={`agent-main ${isSidebarOpen ? 'sidebar-open' : ''}`}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="agent-container">
          <Card className="agent-card">
            <Card.Body className="agent-card-body">
              <div ref={chatContainerRef} className="chat-messages-container">
                {/* --- MODIFIED: Main message rendering logic --- */}
                {messages.map((message, index) => {
                  const key = `${message.type}-${message.id || index}`;

                  if (message.type === 'tool_call') {
                    return <ToolCallMessage key={key} {...message} />;
                  }

                  return (
                    <div key={key} className={`message ${message.sender === "bot" ? "bot-message" : "user-message"}`}>
                      {message.sender === "bot" && (
                        <div className="bot-avatar"> <img src="/ChatBot-Logo.png" alt="Acube Bot" /> </div>
                      )}
                      <div className="message-content">
                        <ReactMarkdown>{message.text}</ReactMarkdown>
                      </div>
                    </div>
                  );
                })}
                {isLoading && (
                  <div className="message bot-message">
                    <div className="bot-avatar"> <img src="/ChatBot-Logo.png" alt="Acube Bot Typing" /> </div>
                    <div className="message-content"> <div className="typing-indicator"> <span></span><span></span><span></span> </div> </div>
                  </div>
                )}
              </div>

              {!activeButton && messages.length <= 1 && (
                <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="button-options">
                  <button className={`agent-button agent-button-blue`} onClick={() => handleButtonClick("blue", "blue")}> CI/CD Setup </button>
                  <button className={`agent-button agent-button-red`} onClick={() => handleButtonClick("red", "red")}> Modify Resources </button>
                  <button className={`agent-button agent-button-green`} onClick={() => handleButtonClick("green", "green")}> Observability </button>
                </motion.div>
              )}

              {showFinalOptions && (
                <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="button-options post-collection-options">
                  <button className={`agent-button agent-button-review`} onClick={handleNavigateToReviewDashboard} title="Review collected data before proceeding"><FontAwesomeIcon icon={faClipboardList} /> Review Dashboard</button>
                  <button className={`agent-button agent-button-proceed`} onClick={handleNavigateToMain} title="Proceed directly to setup"><FontAwesomeIcon icon={faCogs} /> Setup CI/CD</button>
                </motion.div>
              )}
              
              {activeButton && !showFinalOptions && (
                <div className={`chat-input-container ${formColor}`}>
                  <input type="text" ref={inputRef} className="chat-input" placeholder={isLoading ? "Acube is thinking..." : "Type your message..."} value={userInput} onChange={(e) => setUserInput(e.target.value)} onKeyPress={handleKeyPress} disabled={isLoading} aria-label="Chat input" />
                  <button className="send-button" onClick={handleSendMessage} disabled={isLoading || !userInput.trim()} title="Send Message" aria-label="Send Message"><FontAwesomeIcon icon={faPaperPlane} /></button>
                </div>
              )}
            </Card.Body>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default Agent;