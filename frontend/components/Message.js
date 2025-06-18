import React from "react";

const Message = ({ text, sender, timestamp }) => {
  return (
    <div
      className={`p-4 mb-4 rounded-lg max-w-xs ${
        sender === "user"
          ? "bg-blue-500 text-white ml-auto"
          : "bg-white text-gray-800"
      }`}
      style={{ alignSelf: sender === "user" ? "flex-end" : "flex-start" }}
    >
      <p>{text}</p>
      <p className="text-xs text-gray-500 mt-1">
        {new Date(timestamp).toLocaleTimeString()}
      </p>
    </div>
  );
};

export default Message;
