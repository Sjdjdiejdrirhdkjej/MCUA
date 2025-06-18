"use client";
import React, { useState, useEffect } from "react";

const InputBox = ({ addMessage }) => {
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("chat");
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    if (isDarkMode) {
      document.body.classList.add("dark-mode");
    } else {
      document.body.classList.remove("dark-mode");
    }
  }, [isDarkMode]);

  const handleSend = () => {
    addMessage(input, "user");
    setInput("");
  };

  return (
    <div className={`p-4 border-t ${isDarkMode ? "bg-gray-800" : "bg-white"}`}>
      <select
        value={mode}
        onChange={(e) => setMode(e.target.value)}
        className={`mb-2 p-2 border rounded-lg w-full ${
          isDarkMode ? "bg-gray-700 text-white" : "bg-white"
        }`}
      >
        <option value="chat">Chat Mode</option>
        <option value="agent">Agent Mode</option>
      </select>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        className={`w-full p-2 border rounded-lg ${
          isDarkMode ? "bg-gray-700 text-white" : "bg-white"
        }`}
        placeholder="Type a message..."
      />
      <button
        onClick={handleSend}
        className={`mt-2 ${
          isDarkMode ? "bg-blue-600" : "bg-blue-500"
        } text-white p-2 rounded-lg w-full`}
      >
        Send
      </button>
      <button
        onClick={() => setIsDarkMode(!isDarkMode)}
        className={`mt-2 ${
          isDarkMode ? "bg-gray-700" : "bg-gray-300"
        } text-white p-2 rounded-lg w-full`}
      >
        {isDarkMode ? "Light Mode" : "Dark Mode"}
      </button>
    </div>
  );
};

export default InputBox;
