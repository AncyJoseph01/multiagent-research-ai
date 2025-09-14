import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import PrivateRoute from "./components/PrivateRoute";
import Login from "./components/Login";
import Home from "./components/Home";
import SavedPapers from "./components/SavedPapers";
import Chat from "./components/Chat";
import PageNotFound from "./components/PageNotFound";

function App() {
  return (
    <>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<Navigate to="/login" />} />
            <Route path="/login" element={<Login />} />
            
            <Route element={<PrivateRoute />}>
              <Route path="/home" element={<Home />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/saved" element={<SavedPapers />} />
            </Route>
            <Route path="*" element={<PageNotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </>
  );
}

export default App;
