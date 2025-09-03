import { createContext, useContext, useState } from "react";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState({
    userId: null,
    userName: "",
  });
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const login = (userData) => {
    setUser({
      userId: userData.id,
      userName: userData.name,
    });
    setIsAuthenticated(true);
  };
  const logout = () => {
    setUser({
      userId: null,
      userName: "",
    });
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, user }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
