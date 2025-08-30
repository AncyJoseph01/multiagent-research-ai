function Home() {
  const user = JSON.parse(localStorage.getItem("user"));

  return (
    <div className="app-container">
      <header className="header">
        <h1>Welcome to Home Page</h1>
      </header>

      <main className="main">
        {user ? (
          <div>
            <h2>Hello, {user.name} 👋</h2>
            <p>Your email: {user.email}</p>
          </div>
        ) : (
          <p>No user found. Please login again.</p>
        )}
      </main>

      <footer className="footer">
        © {new Date().getFullYear()} Multiagent Research AI - Ancy Joseph
      </footer>
    </div>
  );
}

export default Home;
