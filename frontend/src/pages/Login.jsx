import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../App.css";

function Login() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const response = await fetch("http://localhost:8000/users/login", {
        method: "POST",
        body: new URLSearchParams({ email }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Login failed");
      }

      const data = await response.json();

      // ✅ store user info in localStorage (so Home can use it)
      localStorage.setItem("user", JSON.stringify(data));

      // ✅ navigate to home
      navigate("/home");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="login-page app-container">
      <header className="header">
        <img
          src="/start.jpeg"
          alt="Logo"
          style={{
            width: "50%",
            borderRadius: "50%",
            marginBottom: "1rem",
          }}
        />
        <h1>Multiagent Research AI</h1>
        <p>An experimental platform for collaborative AI research agents.</p>
      </header>

      <main className="main">
        <form onSubmit={handleLogin} className="login-form">
          <h2>Login</h2>
          <input
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <button type="submit">Get Started</button>
          {error && <p style={{ color: "red" }}>{error}</p>}
        </form>
      </main>

      <footer className="footer">
        © {new Date().getFullYear()} Multiagent Research AI - Ancy Joseph
      </footer>
    </div>
  );
}

export default Login;
