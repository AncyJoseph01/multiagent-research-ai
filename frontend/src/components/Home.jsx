import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Home() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Navbar */}
      <nav className="bg-[#1877f2] text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            
            {/* Left - App Name / Logo */}
            <div className="flex-shrink-0">
              <span className="text-xl font-bold">MultiAgent Research Assistant</span>
            </div>

            {/* Center - Nav Links */}
            <div className="flex space-x-6">
              <Link to="/home" className="hover:underline">Home</Link>
              <Link to="/saved" className="hover:underline">Saved Papers</Link>
              <Link to="/chat" className="hover:underline">RAG Chat</Link>
              <Link to="/events" className="hover:underline">Events</Link>
              <Link to="/dashboard" className="hover:underline">Dashboard</Link>
            </div>

            {/* Right - Greeting & Logout */}
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
      <main className="p-8">
        <h1 className="text-3xl font-semibold mb-4">Welcome to Home Page</h1>
        <p className="text-gray-700">
          This is your landing page after login.
        </p>
      </main>
    </div>
  );
}
