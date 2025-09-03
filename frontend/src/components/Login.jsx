import axios from "axios";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { TextField, Box, Typography, Alert, Link } from "@mui/material";
import Button from "@mui/material/Button";
import login_bg from "../assets/start.jpeg";
import { useAuth } from "../context/AuthContext";
// import { Link as RouterLink } from "react-router-dom";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: ""
  });

  const [alertData, setAlertData] = useState({
    isOpened: false,
    severity: "",
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prevData) => ({
      ...prevData,
      [name]: value,
    }));
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    console.log("Logging in with:", formData);
    try {
      const response = await axios.post(
        "http://localhost:8000/users/login",
        formData
      );
      setAlertData({
        isOpened: true,
        message: "Logged in successfully!",
        severity: "success",
      });
      login(response.data);
      navigate("/home");
    } catch (error) {
      setAlertData({
        isOpened: true,
        message: "Login failed. Please try again.",
        severity: "error",
      });
    }
  };


  return (
    <div className="flex flex-col items-center justify-center h-full bg-[#7cb4ec]">
      {alertData.isOpened && (
        <Alert className="absolute top-3" severity={alertData.severity}>
          {alertData.message}
        </Alert>
      )}
      <form
        onSubmit={(e) => handleLogin(e)}
        className="border-1  flex flex-col bg-white shadow  border-gray-300 rounded-2xl w-2/3 h-4/6"
      >
        <div className="flex h-full">
          <div className="w-1/2 h-full bg-blue-200 rounded-l-2xl">
            <img
              src={login_bg}
              alt=""
              className="h-full w-full object-cover rounded-l-2xl"
            />
          </div>
          <div className="w-1/2 p-4">
            <div className="h-full flex items-center justify-center">
              <Box
                sx={{
                  gap: 1,
                  display: "flex",
                  flexDirection: "column",
                  width: "60%",
                  height: "100%",
                  justifyContent: "center",
                }}
              >
                <Typography sx={{ marginBottom: 0 }} variant="h4" gutterBottom>
                  Welcome!
                </Typography>
                <Typography variant="body1" gutterBottom>
                  Your next big idea starts right after this login.
                </Typography>
                <TextField
                  label="Email"
                  variant="outlined"
                  size="small"
                  type="email"
                  name="email"
                  onChange={handleChange}
                  required
                />
                <Button type="submit" variant="contained">
                  Get Started
                </Button>
                <Box
                  sx={{
                    typography: "body1",
                    "& > :not(style) ~ :not(style)": {
                      ml: 2,
                    },
                  }}
                >
                </Box>
              </Box>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
