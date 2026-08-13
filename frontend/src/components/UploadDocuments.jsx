import { useState, useEffect, useRef } from "react";
import './UploadDocuments.css'

function UploadDocuments({ sessionId, documentReset }) {
  const [uploadedFile, setUploadedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const loadDocument = async () => {
      try {
        const res = await fetch(
          `http://localhost:8000/document?session_id=${sessionId}`
        );

        if (!res.ok) throw new Error("Failed to fetch document");

        const data = await res.json();

        setUploadedFile(data.filename || null);
      } catch (err) {
        console.error("Error loading document:", err);
      }
    };

    if (sessionId) {
      loadDocument();
    }
  }, [documentReset]);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      handleUpload(selected);
    }
  };

  const removeFile = () => {
    setUploadedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUpload = async (fileToUpload) => {


    const formData = new FormData();
    formData.append("file", fileToUpload);
    formData.append("session_id", sessionId);

    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      setUploadedFile(data.filename);

    } catch (error) {
      console.error("Upload failed:", error);
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="upload-container">
      <label className="upload-button">
        {loading
          ? "Uploading Document..."
          : uploadedFile
            ? "Uploaded"
            : "Upload Document"
        }
        <input type="file" ref={fileInputRef} hidden onChange={handleFileChange} />
      </label>

      {uploadedFile && (
        <div className="file-card">
          <span className="file-name">{uploadedFile}</span>
        </div>
      )}
    </div>

  );
}

export default UploadDocuments;