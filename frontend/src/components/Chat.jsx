import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "github-markdown-css/github-markdown-light.css";
import SendIcon from "@mui/icons-material/Send";

import {
  Box,
  Paper,
  Button,
  TextField,
  Drawer,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Typography,
  CircularProgress,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import ChatIcon from "@mui/icons-material/Chat";
import axios from "axios";

// Typing Indicator
function TypingIndicator() {
  return (
    <Box sx={{ display: "flex", gap: 0.5, alignItems: "center", p: 1 }}>
      {[...Array(3)].map((_, i) => (
        <Box
          key={i}
          sx={{
            width: 8,
            height: 8,
            bgcolor: "grey.500",
            borderRadius: "50%",
            animation: `typing 1s infinite ${i * 0.2}s`,
          }}
        />
      ))}
      <style>{`
        @keyframes typing {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }
      `}</style>
    </Box>
  );
}

export default function Dashboard() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const [chatHistory, setChatHistory] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [messages, setMessages] = useState([
    { sender: "bot", text: "Hello! I’m your AI assistant. How can I help you today?" },
  ]);
  const [input, setInput] = useState("");
  const [loadingSessions, setLoadingSessions] = useState(false);
  const messagesEndRef = useRef(null);

  // Fetch chat sessions
  useEffect(() => {
    const fetchChatSessions = async () => {
      setLoadingSessions(true);
      try {
        const response = await axios.get(
          `http://localhost:8000/chat/sessions/${user.userId}`
        );
        setChatHistory(response.data);
      } catch (error) {
        console.error("Error fetching chat sessions:", error);
      } finally {
        setLoadingSessions(false);
      }
    };
    if (user.userId) fetchChatSessions();
  }, [user.userId]);

  const handleNewChat = () => {
    setMessages([
      { sender: "bot", text: "Hello! I'm your AI assistant. How can I help you today?" },
    ]);
    setCurrentChatId(null);
  };

  const handleChatSelect = async (chatId) => {
    setCurrentChatId(chatId);
    try {
      const response = await axios.get(
        `http://localhost:8000/chat/history/${chatId}?user_id=${user.userId}`
      );
      const formattedMessages = response.data.chats
        .map((chat) => [
          { sender: "user", text: chat.query },
          { sender: "bot", text: chat.answer },
        ])
        .flat();
      setMessages(formattedMessages);
    } catch (error) {
      console.error("Error fetching chat history:", error);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    const botTyping = { sender: "bot", isTyping: true };
    setMessages((prev) => [...prev, userMessage, botTyping]);
    setInput("");

    try {
      const requestBody = {
        query: input,
        chat_session_id: currentChatId,
      };
      const response = await axios.post(
        `http://localhost:8000/chat/?user_id=${user.userId}`,
        requestBody
      );

      if (!currentChatId) {
        setCurrentChatId(response.data.chat_session_id);
        setChatHistory((prev) => [
          {
            chat_session_id: response.data.chat_session_id,
            created_at: new Date().toISOString(),
            chat_query: response.data.query,
          },
          ...prev,
        ]);
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.isTyping
            ? { sender: "bot", text: response.data.answer || "Sorry, I couldn't process that request." }
            : msg
        )
      );
    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.isTyping ? { sender: "bot", text: "Sorry, there was an error processing your request." } : msg
        )
      );
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* Top Navbar */}
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", px: 4, py: 2, bgcolor: "#1877f2", color: "white" }}>
        <Typography variant="h6" sx={{ fontWeight: "bold" }}>MyApp</Typography>
        <Box sx={{ flexGrow: 1, display: "flex", justifyContent: "center", gap: 4 }}>
          <Link to="/home" style={{ color: "white", textDecoration: "none" }}>Home</Link>
          <Link to="/saved" style={{ color: "white", textDecoration: "none" }}>Saved Papers</Link>
          <Link to="/chat" style={{ color: "white", textDecoration: "none", fontWeight: "bold" }}>RAG Chat</Link>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Typography>Hello, {user.userName || "User"} 👋</Typography>
          <Button variant="contained" sx={{ backgroundColor: "white", color: "#1877f2", "&:hover": { backgroundColor: "#f0f0f0" } }} onClick={handleLogout}>
            Logout
          </Button>
        </Box>
      </Box>

      {/* Sidebar + Chat Area */}
      <Box sx={{ display: "flex", flexGrow: 1, overflow: "hidden" }}>
        {/* Sidebar */}
        <Drawer variant="permanent" sx={{ width: 240, flexShrink: 0, "& .MuiDrawer-paper": { width: 240, boxSizing: "border-box" } }}>
          <Box sx={{ overflow: "auto" }}>
            <List>
              <ListItem button onClick={handleNewChat}>
                <ListItemIcon><AddIcon /></ListItemIcon>
                <ListItemText primary="New Chat" />
              </ListItem>
              <Divider />
              {loadingSessions ? (
                <Box sx={{ display: "flex", justifyContent: "center", p: 2 }}><CircularProgress size={24} /></Box>
              ) : (
                chatHistory.map((chat) => (
                  <ListItem key={chat.chat_session_id} button selected={currentChatId === chat.chat_session_id} onClick={() => handleChatSelect(chat.chat_session_id)}>
                    <ListItemIcon><ChatIcon /></ListItemIcon>
                    <ListItemText primary={chat.chat_query} secondary={new Date(chat.created_at).toLocaleDateString()} primaryTypographyProps={{ sx: { textWrap: "nowrap", overflow: "hidden", textOverflow: "ellipsis" } }} />
                  </ListItem>
                ))
              )}
            </List>
          </Box>
        </Drawer>

        {/* Main Chat Content */}
        <Box sx={{ flexGrow: 1, display: "flex", flexDirection: "column" }}>
          <Box sx={{ flex: 1, overflowY: "auto", px: 2, py: 3, bgcolor: "#f5f5f5", display: "flex", flexDirection: "column" }}>
            {messages.map((msg, idx) => (
              <Box key={idx} sx={{ display: "flex", justifyContent: msg.sender === "user" ? "flex-end" : "flex-start", mb: 2 }}>
                <Paper elevation={1} sx={{ p: 2, maxWidth: "80%", borderRadius: 3, bgcolor: msg.sender === "user" ? "primary.main" : "background.paper", color: msg.sender === "user" ? "white" : "text.primary", overflowX: "auto" }}>
                  {msg.isTyping ? <TypingIndicator /> : <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>}
                </Paper>
              </Box>
            ))}
            <div ref={messagesEndRef} />
          </Box>

          <Box sx={{ borderTop: "1px solid #ddd", p: 2, display: "flex", alignItems: "center", bgcolor: "background.paper" }}>
            <TextField fullWidth variant="outlined" placeholder="Send a message..." value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSend()} />
            <Button variant="contained" onClick={handleSend} sx={{ minWidth: 0, ml: 1, p: 1, borderRadius: "50%", height: "3.5rem", width: "3.5rem" }}>
              <SendIcon />
            </Button>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
