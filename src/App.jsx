// App.jsx
import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Home from "./components/Home";
import Chatbox from "./components/Chatbot";
import "./App.css";
import Login from "./components/Login";
import HelpAndSupport from "./components/helpAndSupport";
import Earn from "./components/Earn";
import ReferralsPage from "./components/ReferralsPage";
import PrivacyPolicy from "./components/PrivacyPolicy";
import TermsAndConditions from "./components/TermsAndConditions";
import About from "./components/about.jsx";
import Leaderboard from "./components/leaderboard";

const App = () => {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/referrals" element={<ReferralsPage />} />
          <Route path="/earn" element={<Earn />} />
          {/* by mit prajapati 14-08-2024 */}
          <Route path="/leaderboard" element={<Leaderboard />} /> 
          {/* Add other routes here */}

          {/* foorter routes */}
          <Route path="/about" element={<About />} />
          <Route path="/help-and-support" element={<HelpAndSupport />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/terms" element={<TermsAndConditions />} />
        </Routes>
        <Chatbox />
      </div>
    </Router>
  );
};

export default App;
