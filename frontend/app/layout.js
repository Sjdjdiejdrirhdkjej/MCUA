import { Geist, Geist_Mono } from "next/font/google";
import Image from "next/image";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "Fancy Chat App",
  description: "Chat with Manus AI",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <div className="flex flex-col h-screen">
          <header className="p-4 bg-white shadow-md flex items-center">
            <Image
              src="/logo.png"
              alt="Fancy Chat App Logo"
              width={40}
              height={40}
              className="mr-2"
            />
            <h1 className="text-2xl font-bold text-gray-800">Fancy Chat App</h1>
          </header>
          <div className="flex flex-1 overflow-hidden">
            <div className="w-2/3 border-r bg-gray-100">
              {children}
            </div>
            <div className="w-1/3 bg-gray-50">
              {/* Other functionalities can go here */}
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}