import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { Link, useNavigate } from "react-router-dom";

export default function Home() {
  const { user, logout } = useAuth();
  const [arxivKeyword, setArxivKeyword] = useState("");
  const [arxivResults, setArxivResults] = useState([]);
  const [pdfFile, setPdfFile] = useState(null);
  const [pdfTitle, setPdfTitle] = useState("");
  const [pdfAuthors, setPdfAuthors] = useState("");
  const [pdfAbstract, setPdfAbstract] = useState("");

  const [loadingArxiv, setLoadingArxiv] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);

  const handleLogout = () => {
    logout();
  };

  // Fetch Arxiv papers
  const fetchArxivPapers = async () => {
    if (!arxivKeyword.trim()) return;
    setLoadingArxiv(true);

    try {
      const params = new URLSearchParams({
        keyword: arxivKeyword,
        user_id: user.userId,
        max_results: "1",
      });

      const res = await fetch(
        `http://localhost:8000/research/papers/arxiv?${params.toString()}`,
        { method: "POST" }
      );

      if (!res.ok) throw new Error(`Error: ${res.statusText}`);

      const data = await res.json();
      setArxivResults(Array.isArray(data) ? data : [data]);
    } catch (error) {
      console.error("Error fetching Arxiv papers:", error);
      alert("Failed to fetch Arxiv papers. Check console for details.");
    } finally {
      setLoadingArxiv(false);
    }
  };

  // Upload PDF
  const uploadPdfPaper = async () => {
    if (!pdfFile) {
      alert("Please select a PDF file first!");
      return;
    }
    setLoadingPdf(true);

    const formData = new FormData();
    formData.append("file", pdfFile);
    formData.append("title", pdfTitle);
    formData.append("authors", pdfAuthors);
    formData.append("abstract", pdfAbstract);
    formData.append("user_id", user.userId);

    try {
      const res = await fetch("http://localhost:8000/pdf_research/papers/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error(`Error: ${res.statusText}`);

      const data = await res.json();
      alert(`Uploaded paper: ${data.title}`);

      setPdfFile(null);
      setPdfTitle("");
      setPdfAuthors("");
      setPdfAbstract("");
    } catch (error) {
      console.error("Error uploading PDF:", error);
      alert("Failed to upload PDF. Check console for details.");
    } finally {
      setLoadingPdf(false);
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
              <span>Hello, {user.userName || "User"} 👋</span>
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

      {/* Main content */}
      <main className="p-8 grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Arxiv Card */}
        <div className="bg-gray-50 p-6 rounded-xl shadow-md">
          <h2 className="text-2xl font-semibold mb-4">Search Arxiv Papers</h2>
          <input
            type="text"
            placeholder="Enter keyword..."
            value={arxivKeyword}
            onChange={(e) => setArxivKeyword(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded mb-4"
          />
          <button
            onClick={fetchArxivPapers}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 flex items-center justify-center"
            disabled={loadingArxiv}
          >
            {loadingArxiv ? (
              <span className="animate-spin border-2 border-white border-t-transparent rounded-full w-5 h-5"></span>
            ) : (
              "Fetch Papers"
            )}
          </button>
          {arxivResults.map((paper, idx) => (
          <li key={idx} className="border p-2 rounded">
            <strong>{paper.title}</strong>
            <p className="text-sm text-gray-600">
              {Array.isArray(paper.authors)
                ? paper.authors.join(", ")
                : paper.authors || "Unknown authors"}
            </p>
            {paper.url && (
              <a
                href={paper.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline text-sm"
              >
                View Paper
              </a>
            )}
          </li>
        ))}

        </div>

        {/* PDF Upload Card */}
        <div className="bg-gray-50 p-6 rounded-xl shadow-md">
          <h2 className="text-2xl font-semibold mb-4">Upload PDF Paper</h2>
          <input
            type="text"
            placeholder="Title"
            value={pdfTitle}
            onChange={(e) => setPdfTitle(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded mb-2"
          />
          <input
            type="text"
            placeholder="Authors (comma separated)"
            value={pdfAuthors}
            onChange={(e) => setPdfAuthors(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded mb-2"
          />
          <textarea
            placeholder="Abstract (optional)"
            value={pdfAbstract}
            onChange={(e) => setPdfAbstract(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded mb-2"
          />
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setPdfFile(e.target.files[0])}
            className="mb-4"
          />
          <button
            onClick={uploadPdfPaper}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 flex items-center justify-center"
            disabled={loadingPdf}
          >
            {loadingPdf ? (
              <span className="animate-spin border-2 border-white border-t-transparent rounded-full w-5 h-5"></span>
            ) : (
              "Upload PDF"
            )}
          </button>
        </div>
      </main>
    </div>
  );
}
