import { useState } from 'react'
import './App.css'

function App() {
  return (
    <div className="app-container">
      <header className="header">
        <h1>Multiagent Research AI</h1>
        <p>An experimental platform for collaborative AI research agents.</p>
      </header>

      <main className="main">
        <button className="btn primary">Get Started</button>
        <button className="btn secondary">Learn More</button>
      </main>

      <footer className="footer">
        © {new Date().getFullYear()} Multiagent Research AI - Ancy Joseph
      </footer>
    </div>
  )
}

export default App
