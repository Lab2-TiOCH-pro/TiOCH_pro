import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import "./SprawdzPage.css";

const SprawdzPage = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [email, setEmail] = useState("");
  const [isValidEmail, setIsValidEmail] = useState(true);
  const [wantsEmail, setWantsEmail] = useState(false); // Stan dla checkboxa

  const onDrop = useCallback((acceptedFiles) => {
    setFiles((prev) => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
  });

  const handleEmailChange = (e) => {
    const value = e.target.value;
    setEmail(value);
    setIsValidEmail(/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)); // Sprawdzanie poprawności e-maila
  };

  const handleCheck = () => {
    // Jeśli chce e-maila, sprawdzamy jego poprawność
    if (wantsEmail && !isValidEmail) {
      alert("Podaj poprawny adres e-mail.");
      return;
    }

    // Jeśli wszystko jest OK, przechodzimy do strony wyników
    navigate("/wyniki", {
      state: { email: wantsEmail ? email : null }, // Przesyłamy e-mail tylko, jeśli checkbox jest zaznaczony
    });
  };

  return (
    <div className="sprawdz-container">
      <div className="logo">
        <img src="/logo447.png" alt="Logo" style={{ height: "100px", width: "auto" }} />
      </div>

      <div className="top-right-text">PRZ INFORMATYKA 2025</div>

      <div className="sprawdz-content">
        <div className="left-column">
          <h2>Wybierz pliki</h2>
          <div
            {...getRootProps({
              className: `file-upload-button${isDragActive ? " drag-active" : ""}`,
            })}
          >
            <input {...getInputProps()} />
            {isDragActive
              ? "Upuść tutaj pliki..."
              : "Przeciągnij lub kliknij, aby wybrać pliki"}
          </div>

          {/* Checkbox i pole maila */}
          <div style={{ marginTop: "20px" }}>
            <label>
              <input
                type="checkbox"
                checked={wantsEmail}
                onChange={() => setWantsEmail(!wantsEmail)}
              />
              Chcę dostać wyniki na e-maila
            </label>

            {wantsEmail && (
              <div>
                <input
                  type="email"
                  placeholder="Podaj swój adres e-mail"
                  value={email}
                  onChange={handleEmailChange}
                  className="email-input"
                />
                {!isValidEmail && email && (
                  <p style={{ color: "red" }}>Proszę podać poprawny adres e-mail.</p>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="right-column">
          <h2>Twoje pliki</h2>
          <div className="files-box">
            {files.length === 0 ? (
              <p>Tu pokazują się pliki dodane do sprawdzenia</p>
            ) : (
              <p>
                {files.map((file, index) => (
                  <React.Fragment key={index}>
                    • {file.name}
                    {index < files.length - 1 && ","}
                    <br />
                  </React.Fragment>
                ))}
              </p>
            )}
          </div>

          <button className="custom-button sprawdz-button" onClick={handleCheck}>
            SPRAWDŹ
          </button>
        </div>
      </div>

      <div className="footer">Obsługiwane formaty: pdf, word, odt</div>
    </div>
  );
};

export default SprawdzPage;
