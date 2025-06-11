import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import "./SprawdzPage.css";

const SprawdzPage = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [email, setEmail] = useState("");
  const [isValidEmail, setIsValidEmail] = useState(true);
  const [wantsEmail, setWantsEmail] = useState(false);

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
    setIsValidEmail(/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      alert("Nie dodano żadnych plików.");
      return;
    }

    if (wantsEmail && !isValidEmail) {
      alert("Podaj poprawny adres e-mail.");
      return;
    }

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    formData.append("uploader_email", wantsEmail ? email : "anonymous@example.com");

    try {
      const response = await fetch("http://localhost:8002/api/documents/", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      console.log("Odpowiedź z backendu:", data);

      const dokumenty = Array.isArray(data) ? data : [data];
      const ids = dokumenty.map((d) => d.documentId).filter(Boolean);

      if (ids.length === 0) {
        alert("Brak ID dokumentów w odpowiedzi.");
        return;
      }

      navigate("/ladowanie", { state: { ids } });
    } catch (err) {
      alert(`Błąd połączenia: ${err.message}`);
    }
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

          <button className="custom-button sprawdz-button" onClick={handleUpload}>
            SPRAWDŹ
          </button>
        </div>
      </div>

      <div className="footer">Obsługiwane formaty: PDF, DOCX, XLSX, CSV, HTML, TXT, JSON i XML. Maksymalny rozmiar przesyłanego pliku: 10 MB</div>
    </div>
  );
};

export default SprawdzPage;
