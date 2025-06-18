"use client";

import React, { useState, useEffect, useRef } from "react";
import Message from "./Message";
import InputBox from "./InputBox";

const ChatContainer = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "Hello! How can I assist you today?",
      sender: "manus",
      timestamp: "2023-10-01T12:00:00Z", // Use a fixed timestamp for demonstration
    },
  ]);
  const [isConnected, setIsConnected] = useState(true); // New state for connection status

  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    // Simulate connection check
    const checkConnection = setInterval(() => {
      // Replace this with actual connection check logic
      const isConnected = Math.random() > 0.5;
      setIsConnected(isConnected);
    }, 5000);

    return () => clearInterval(checkConnection);
  }, []);

  const addMessage = (text, sender) => {
    setMessages([
      ...messages,
      {
        id: messages.length + 1,
        text,
        sender,
        timestamp: "2023-10-01T12:00:00Z",
      }, // Use a fixed timestamp for demonstration
    ]);
  };

  const handleReconnect = () => {
    // Logic to attempt reconnection
    setIsConnected(true);
  };

  if (!isConnected) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <p className="text-xl text-red-500">Backend is not connected</p>
        <button
          onClick={handleReconnect}
          className="mt-4 bg-blue-500 text-white p-2 rounded-lg"
        >
          Reconnect
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4">
        {messages.map((message) => (
          <Message
            key={message.id}
            text={message.text}
            sender={message.sender}
            timestamp={message.timestamp}
          />
        ))}
        <div ref={chatEndRef} />
      </div>
      <div className="border-t">
        <InputBox addMessage={addMessage} />
      </div>
    </div>
  );
};

export default ChatContainer;
