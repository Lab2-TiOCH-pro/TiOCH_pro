import React from "react";
import "./HomePage.css";


const HomePage = () => {
  return (
    <div className="homepage-container">
      {/* Logo  */}
      <div className="logo">LOGO</div>

      {/* Tytuł */}
      <h1 className="title">SPRAWDŹ DOKUMENT</h1>

      {/* Przycisk */}
      <div className="button-container">
        <button className="custom-button">
          <span className="button-text">Przejdź</span>
        </button>
      </div>

      {/* Stopka */}
      <div className="footer">Obsługiwane formaty: pdf, word, odt</div>

      {/* PRZ Informatyka 2025 */}
      <div className="top-right-text">PRZ INFORMATYKA 2025</div>
    </div>
  );
};

export default HomePage;
