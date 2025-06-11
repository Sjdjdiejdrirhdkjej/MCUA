"use client";

import { useState, FormEvent, useEffect } from "react";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism'; // Or any other theme

type DesktopMode = "idle" | "terminal" | "file_editor" | "browser";

interface CurrentFile {
  filename: string;
  content: string;
  language: string;
}

interface DesktopImage {
  data: string; // Base64 encoded image data
  contentType: string; // e.g., "image/png"
  filename: string; // For alt text or download purposes
}

export default function HomePage() {
  const [inputValue, setInputValue] = useState("");
  const [chatMessages, setChatMessages] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const [desktopMode, setDesktopMode] = useState<DesktopMode>("idle");
  const [desktopContent, setDesktopContent] = useState<string>(""); // For terminal
  const [currentFile, setCurrentFile] = useState<CurrentFile | null>(null); // For file editor
  const [desktopImage, setDesktopImage] = useState<DesktopImage | null>(null); // For browser screenshot
  const [browserImageError, setBrowserImageError] = useState(false); // For image loading errors

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!inputValue.trim()) return;

    const currentMessage = inputValue;
    setInputValue("");
    setChatMessages((prevMessages) => [...prevMessages, `You: ${currentMessage}`]);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: currentMessage }),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      if (response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            if (buffer.trim()) handleStreamedObject(JSON.parse(buffer));
            break;
          }
          buffer += decoder.decode(value, { stream: true });
          let newlineIndex;
          while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
            const line = buffer.substring(0, newlineIndex).trim();
            buffer = buffer.substring(newlineIndex + 1);
            if (line) {
              try {
                handleStreamedObject(JSON.parse(line));
              } catch (e) {
                console.error("Failed to parse JSON line:", line, e);
              }
            }
          }
        }
      } else {
        handleStreamedObject({ type: "message", content: "Orbitron: No response body" });
      }
    } catch (error) {
      console.error("Failed to fetch chat response:", error);
      const msg = error instanceof Error ? error.message : String(error);
      handleStreamedObject({ type: "message", content: `Orbitron: Error - ${msg}` });
    } finally {
      setIsLoading(false);
    }
  };

  const handleStreamedObject = (parsedObject: any) => {
    switch (parsedObject.type) {
      case "message":
        setChatMessages((prevMessages) => [...prevMessages, `Orbitron: ${parsedObject.content}`]);
        break;
      case "error":
        setChatMessages((prevMessages) => [...prevMessages, `Orbitron Error: ${parsedObject.content}`]);
        break;
      case "clear_desktop":
        setDesktopContent("");
        setCurrentFile(null);
        setDesktopImage(null);
        break;
      case "desktop_mode_switch":
        setDesktopMode(parsedObject.mode);
        if (parsedObject.mode !== "file_editor") setCurrentFile(null);
        if (parsedObject.mode !== "terminal") setDesktopContent(""); // Clear terminal on mode switch away
        if (parsedObject.mode !== "browser") setDesktopImage(null);
        break;
      case "desktop_content_stream_start": // For terminal
        setDesktopContent("");
        setCurrentFile(null);
        setDesktopImage(null);
        setBrowserImageError(false); // Reset browser image error
        break;
      case "desktop_content_stream": // For terminal
        // New: Handle structured terminal content
        const { stream_type, content, exit_code } = parsedObject;
        if (stream_type === "stdout") {
          setDesktopContent((prevContent) => prevContent + content + "\n");
        } else if (stream_type === "stderr") {
          setDesktopContent((prevContent) => prevContent + `STDERR: ${content}\n`);
        } else if (stream_type === "exit_code") {
          setDesktopContent((prevContent) => prevContent + `\n--- ${content} (Code: ${exit_code}) ---\n`);
        } else if (stream_type === "execution_error") {
           setDesktopContent((prevContent) => prevContent + `EXECUTION ERROR: ${content}\n`);
        } else {
          // Fallback for older string-only content, or if orchestrator sends simple content
          setDesktopContent((prevContent) => prevContent + content + "\n");
        }
        break;
      case "desktop_content_stream_end": // For terminal
        break;
      case "desktop_content_set": // For file editor or browser
        if (parsedObject.content_type === "image_base64") {
          setDesktopImage({
            data: parsedObject.data,
            contentType: parsedObject.contentType || "image/png", // Use provided or default
            filename: parsedObject.filename,
          });
          setBrowserImageError(false); // Reset error on new image
          setCurrentFile(null);
          setDesktopContent("");
        } else { // Assuming it's for file editor
          setCurrentFile({
            filename: parsedObject.filename,
            content: parsedObject.content,
            language: parsedObject.language
          });
          setDesktopImage(null);
          setDesktopContent("");
        }
        break;
      default:
        console.warn("Received unknown message type:", parsedObject);
    }
  };

  useEffect(() => {
    const chatContainer = document.getElementById("chat-container");
    if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
  }, [chatMessages]);

  useEffect(() => {
    const terminalContainer = document.getElementById("terminal-output");
    if (terminalContainer) terminalContainer.scrollTop = terminalContainer.scrollHeight;
  }, [desktopContent]);

  return (
    <main className="flex h-screen bg-gray-900 text-white">
      {/* Left side: Chat */}
      <div className="w-1/2 h-full flex flex-col p-4 border-r border-gray-700">
        <h1 className="text-2xl font-bold mb-4 text-center text-purple-400">Orbitron CUA</h1>
        <div id="chat-container" className="flex-grow overflow-y-auto mb-4 p-2 bg-gray-800 rounded scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-800">
          {chatMessages.map((msg, index) => (
            <div key={index} className={`mb-2 flex ${msg.startsWith("You:") ? "justify-end" : "justify-start"}`}>
              <div>
                <p className={`text-xs ${msg.startsWith("You:") ? "text-blue-300 text-right" : "text-purple-300 text-left"} mb-0.5`}>
                  {msg.startsWith("You:") ? "You" : "Orbitron"}
                </p>
                <span className={`p-2 rounded-lg inline-block text-sm ${msg.startsWith("You:") ? "bg-blue-600" : "bg-purple-600"}`}>
                  {msg.substring(msg.indexOf(":") + 2)}
                </span>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-center items-center mt-2">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-400"></div>
            </div>
          )}
        </div>
        <form onSubmit={handleSubmit} className="flex">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            className="flex-grow p-2 rounded-l-lg bg-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-purple-500 placeholder-gray-400"
            placeholder="Try 'go_to google.com', 'new_tab', 'switch_tab 0'"
            disabled={isLoading}
          />
          <button
            type="submit"
            className="bg-purple-600 hover:bg-purple-700 text-white p-2 rounded-r-lg disabled:opacity-50"
            disabled={isLoading}
          >
            Send
          </button>
        </form>
      </div>

      {/* Right side: Desktop Representation */}
      <div className="w-1/2 h-full flex flex-col p-4 bg-gray-850">
        {desktopMode === 'terminal' ? (
          <div className="w-full h-full bg-black rounded-lg p-1 flex flex-col shadow-lg">
            <div className="flex-shrink-0 mb-1 px-3 py-1 bg-gray-700 rounded-t-md">
              <span className="text-green-400">●</span> <span className="text-yellow-400">●</span> <span className="text-red-400">●</span>
              <span className="ml-2 text-gray-300 text-sm">Terminal</span>
            </div>
            <pre id="terminal-output" className="flex-grow text-sm text-white overflow-y-auto whitespace-pre-wrap break-all bg-black p-3 rounded-b-md scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-black">
              {desktopContent}
            </pre>
          </div>
        ) : desktopMode === 'file_editor' && currentFile ? (
          <div className="w-full h-full bg-gray-800 rounded-lg flex flex-col shadow-lg">
            <div className="flex-shrink-0 p-2 bg-gray-700 text-white rounded-t-md">
              {currentFile.filename}
            </div>
            <div className="flex-grow overflow-auto h-0">
              <SyntaxHighlighter
                language={currentFile.language} style={atomDark}
                customStyle={{ margin: 0, width: "100%", height: "100%", fontFamily:"'Menlo', 'Monaco', 'Courier New', monospace" }}
                codeTagProps={{ style: { fontFamily: "inherit" } }}
                showLineNumbers={true} lineNumberStyle={{color: '#6b7280', fontSize: '0.8em', marginRight: '8px'}}
              >
                {currentFile.content}
              </SyntaxHighlighter>
            </div>
          </div>
        ) : desktopMode === 'browser' && desktopImage ? (
          <div className="w-full h-full bg-gray-700 rounded-lg flex flex-col shadow-lg overflow-hidden">
            <div className="flex-shrink-0 p-2 bg-gray-600 text-white rounded-t-md">
              Browser View - {desktopImage.filename}
            </div>
            <div className="flex-grow flex justify-center items-center bg-gray-500 p-2 relative">
              {!browserImageError ? (
                <img
                  src={`data:${desktopImage.contentType || 'image/png'};base64,${desktopImage.data}`}
                  alt={desktopImage.filename}
                  className="max-w-full max-h-full object-contain rounded"
                  onError={(e) => {
                    console.error("Browser image failed to load:", e);
                    setBrowserImageError(true);
                  }}
                />
              ) : (
                <div className="text-red-400 p-4 bg-gray-800 rounded">
                  <p>Failed to load browser view.</p>
                  <p className="text-xs">This might be due to an invalid image format or data.</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="w-full h-full bg-gray-800 rounded-lg flex justify-center items-center shadow-lg">
            <p className="text-gray-500 text-2xl">Desktop Area</p>
          </div>
        )}
      </div>
    </main>
  );
}
