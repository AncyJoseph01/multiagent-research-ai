import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL; 

// Normalize user ID from different possible response shapes
function getUserId(u) {
  if (!u) return null;
  return (
    u.id ||
    u.user?.id ||
    u.userId ||
    u.user?.userId ||
    u.user_id ||
    u.user?.user_id ||
    null
  );
}

// Simple UUID check
function isLikelyUuid(v) {
  return typeof v === "string" && /^[0-9a-fA-F-]{36}$/.test(v);
}

// Lightweight Markdown parser for headings, bold, bullets
function renderMarkdown(text) {
  if (!text) return null;

  const elements = [];
  const lines = text.split("\n");

  let ulBuffer = [];

  function flushUl() {
    if (ulBuffer.length > 0) {
      elements.push(<ul className="list-disc pl-5 mb-2" key={`ul-${elements.length}`}>{ulBuffer}</ul>);
      ulBuffer = [];
    }
  }

  lines.forEach((line, i) => {
    line = line.trim();
    if (!line) return elements.push(<br key={i} />);

    // Headings
    if (line.startsWith("### ")) {
      flushUl();
      elements.push(<h3 key={i} className="text-lg font-semibold">{line.slice(4)}</h3>);
    } else if (line.startsWith("## ")) {
      flushUl();
      elements.push(<h2 key={i} className="text-xl font-bold">{line.slice(3)}</h2>);
    } else if (line.startsWith("# ")) {
      flushUl();
      elements.push(<h1 key={i} className="text-2xl font-bold">{line.slice(2)}</h1>);
    }
    // Bullets
    else if (line.startsWith("* ")) {
      ulBuffer.push(<li key={i}>{line.slice(2)}</li>);
    }
    // Paragraphs with bold
    else {
      flushUl();
      // Replace **bold** anywhere in line
      const parts = [];
      let lastIndex = 0;
      const regex = /\*\*(.*?)\*\*/g;
      let match;
      while ((match = regex.exec(line)) !== null) {
        if (match.index > lastIndex) {
          parts.push(line.slice(lastIndex, match.index));
        }
        parts.push(<strong key={i + "-" + match.index}>{match[1]}</strong>);
        lastIndex = match.index + match[0].length;
      }
      if (lastIndex < line.length) parts.push(line.slice(lastIndex));

      elements.push(<p key={i} className="mb-1">{parts}</p>);
    }
  });

  flushUl();
  return elements;
}

export default function SavedPapers() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [papers, setPapers] = useState([]);
  const [papersLoading, setPapersLoading] = useState(true);
  const [papersError, setPapersError] = useState("");

  const [selectedPaperId, setSelectedPaperId] = useState(null);
  const [summaries, setSummaries] = useState([]);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");

  const [deletingPaperId, setDeletingPaperId] = useState(null);

  const userId = useMemo(() => getUserId(user), [user]);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  // Fetch papers
  useEffect(() => {
    setPapers([]);
    setPapersError("");
    if (!userId) {
      setPapersLoading(false);
      console.warn("[SavedPapers] No userId found in auth context:", user);
      return;
    }
    if (!isLikelyUuid(userId)) {
      setPapersLoading(false);
      setPapersError("Logged-in user does not have a valid UUID.");
      console.warn("[SavedPapers] userId doesn't look like a UUID:", userId);
      return;
    }

    setPapersLoading(true);
    const url = `${API_BASE}/papers?user_id=${encodeURIComponent(userId)}`;
    console.log("[SavedPapers] Fetching papers:", url);
    fetch(url)
      .then(async (res) => {
        if (!res.ok) {
          const text = await res.text();
          throw new Error(`Papers fetch failed: ${res.status} ${text}`);
        }
        return res.json();
      })
      .then((data) => {
        setPapers(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        console.error(err);
        setPapersError("Failed to load papers.");
      })
      .finally(() => setPapersLoading(false));
  }, [userId]);

  // Fetch summaries
  useEffect(() => {
    setSummaries([]);
    setSummaryError("");
    if (!selectedPaperId) return;

    setSummaryLoading(true);
    const url = `${API_BASE}/summaries/papers/${selectedPaperId}`;
    console.log("[SavedPapers] Fetching summaries:", url);
    fetch(url)
      .then(async (res) => {
        if (res.status === 404) return [];
        if (!res.ok) {
          const text = await res.text();
          throw new Error(`Summaries fetch failed: ${res.status} ${text}`);
        }
        return res.json();
      })
      .then((data) => {
        setSummaries(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        console.error(err);
        setSummaryError("Failed to load summaries.");
      })
      .finally(() => setSummaryLoading(false));
  }, [selectedPaperId]);

  // Delete paper
  const handleDeletePaper = async (paperId) => {
    if (!window.confirm("Are you sure you want to delete this paper?")) return;
    if (!userId) return;

    try {
      setDeletingPaperId(paperId);
      const res = await fetch(`${API_BASE}/papers/${paperId}?user_id=${userId}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Delete failed: ${res.status} ${text}`);
      }

      setPapers((prev) => prev.filter((p) => p.id !== paperId));

      if (selectedPaperId === paperId) {
        setSelectedPaperId(null);
        setSummaries([]);
      }

      alert("Paper deleted successfully!");
    } catch (err) {
      console.error(err);
      alert("Failed to delete paper.");
    } finally {
      setDeletingPaperId(null);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Navbar */}
      <nav className="bg-[#1877f2] text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex-shrink-0">
              <span className="text-xl font-bold">MultiAgent Research Assistant</span>
            </div>
            <div className="flex space-x-6">
              <Link to="/home" className="hover:underline">Home</Link>
              <Link to="/saved" className="hover:underline">Saved Papers</Link>
              <Link to="/chat" className="hover:underline">RAG Chat</Link>
            </div>
            <div className="flex items-center space-x-4">
              <span>Hello, {user?.userName || user?.name || "User"} 👋</span>
              <button
                onClick={handleLogout}
                className="bg-white text-[#1877f2] px-3 py-1 rounded-lg font-medium hover:bg-gray-100"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main: two-column layout */}
      <main className="p-8">
        <h1 className="text-3xl font-semibold mb-4">Saved Papers</h1>

        {!userId && (
          <p className="text-red-600 mb-4">
            Couldn’t find a user id in auth context. Make sure your login stores the user object
            with an <code>id</code> (UUID).
          </p>
        )}

        {papersLoading ? (
          <p>Loading papers...</p>
        ) : papersError ? (
          <p className="text-red-600">{papersError}</p>
        ) : (
          <div className="flex border rounded-lg overflow-hidden h-[70vh]">
            {/* Left: paper list */}
            <div className="w-1/3 border-r p-4 overflow-y-auto">
              <h2 className="font-bold mb-3">Your Papers</h2>
              {papers.length === 0 ? (
                <p className="text-gray-600">No papers found.</p>
              ) : (
                <ul className="space-y-2">
                {papers.map((p) => (
                  <li
                    key={p.id}
                    className={`p-2 rounded cursor-pointer flex justify-between items-center ${
                      p.id === selectedPaperId ? "bg-blue-100" : "hover:bg-gray-100"
                    }`}
                    title={p.title}
                  >
                    {/* Paper title & authors */}
                    <div
                      className="flex-1 overflow-hidden"
                      onClick={() => setSelectedPaperId(p.id)}
                    >
                      <div className="font-medium truncate">{p.title}</div>
                      {p.authors && (
                        <div className="text-xs text-gray-600 truncate">{p.authors}</div>
                      )}
                    </div>

                    {/* Delete icon */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeletePaper(p.id);
                      }}
                      className={`ml-2 p-1 rounded hover:bg-red-100 ${
                        deletingPaperId === p.id ? "cursor-not-allowed opacity-50" : "text-red-600"
                      }`}
                      disabled={deletingPaperId === p.id}
                      title="Delete Paper"
                    >
                      {deletingPaperId === p.id ? (
                        "..." // optional loading indicator
                      ) : (
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-5 w-5"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <polyline points="3 6 5 6 21 6"></polyline>
                          <path d="M19 6l-1 14H6L5 6"></path>
                          <path d="M10 11v6"></path>
                          <path d="M14 11v6"></path>
                          <path d="M9 6V4h6v2"></path>
                        </svg>
                      )}
                    </button>
                  </li>
                ))}
              </ul>

              )}
            </div>

            {/* Right: summaries */}
            <div className="flex-1 p-4 overflow-y-auto">
              {!selectedPaperId ? (
                <p className="text-gray-700">Select a paper to view its summary.</p>
              ) : summaryLoading ? (
                <p>Loading summary…</p>
              ) : summaryError ? (
                <p className="text-red-600">{summaryError}</p>
              ) : summaries.length === 0 ? (
                <p className="text-gray-700">No summaries for this paper yet.</p>
              ) : (
                summaries.map((s) => (
                  <div key={s.id} className="mb-5">
                    <h3 className="font-semibold mb-1">{s.summary_type || "Summary"}</h3>
                    <div className="whitespace-pre-wrap leading-relaxed">
                      {renderMarkdown(s.content)}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {s.created_at ? new Date(s.created_at).toLocaleString() : ""}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
