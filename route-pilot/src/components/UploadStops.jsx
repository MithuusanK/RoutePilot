import { useState } from 'react';
import './UploadStops.css';

export default function UploadStops() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [errors, setErrors] = useState([]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.csv')) {
        setErrors(['Please select a CSV file']);
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setErrors([]);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setErrors(['Please select a file first']);
      return;
    }

    setUploading(true);
    setErrors([]);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/upload-stops', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setResult(data);
        setFile(null);
        // Reset file input
        document.getElementById('file-input').value = '';
      } else {
        setErrors(data.errors || [data.detail || 'Upload failed']);
      }
    } catch (error) {
      setErrors([`Network error: ${error.message}. Is the backend running on port 8000?`]);
    } finally {
      setUploading(false);
    }
  };

  const downloadSampleCSV = () => {
    const sampleData = `stop_sequence,stop_type,address,city,state,zip,latitude,longitude,earliest_time,latest_time,service_duration_minutes,notes,contact_name,contact_phone,reference_number
1,PICKUP,1200 Industrial Pkwy,Dallas,TX,75247,32.8357,-96.9217,2026-01-20T08:00:00,2026-01-20T10:00:00,45,Use dock 3. Gate code 1234,John Smith,2145551234,PO-98765
2,DELIVERY,450 Commerce Dr,Oklahoma City,OK,73102,35.4676,-97.5164,2026-01-20T14:00:00,2026-01-20T18:00:00,30,Call before arrival,Maria Garcia,4055559876,BOL-54321
3,WAYPOINT,,,,,39.7392,-104.9903,,,15,Fuel stop - Pilot Flying J,,,
4,DELIVERY,8900 Warehouse Blvd,Kansas City,MO,64161,39.2045,-94.5701,2026-01-21T09:00:00,2026-01-21T12:00:00,60,Liftgate required,Tom Johnson,8165552468,DEL-78910`;

    const blob = new Blob([sampleData], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'route-stops-sample.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="upload-container">
      <div className="upload-card">
        <h2 className="upload-title">Upload Route Stops</h2>
        <p className="upload-subtitle">Upload a CSV file with your delivery stops and pickup locations</p>

        {/* Download Sample */}
        <div className="sample-section">
          <button
            type="button"
            onClick={downloadSampleCSV}
            className="btn-sample"
          >
            📥 Download Sample CSV
          </button>
        </div>

        {/* File Upload Area */}
        <div className="upload-area">
          <label htmlFor="file-input" className="file-label">
            <input
              id="file-input"
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="file-input"
              disabled={uploading}
            />
            <div className="file-label-content">
              <span className="file-icon">📄</span>
              <span className="file-text">
                {file ? file.name : 'Tap to select CSV file'}
              </span>
              <span className="file-subtext">CSV files only</span>
            </div>
          </label>
        </div>

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="btn-upload"
        >
          {uploading ? '⏳ Validating...' : '🚀 Upload & Validate'}
        </button>

        {/* Error Display */}
        {errors.length > 0 && (
          <div className="alert alert-error">
            <h3 className="alert-title">❌ Validation Errors</h3>
            <ul className="error-list">
              {errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Success Display */}
        {result && (
          <div className="alert alert-success">
            <h3 className="alert-title">✅ {result.message}</h3>
            <p className="result-info">
              File: <strong>{result.filename}</strong> • Stops: <strong>{result.stops_count}</strong>
            </p>

            {result.preview && result.preview.length > 0 && (
              <div className="preview-section">
                <h4 className="preview-title">Preview (first {result.preview.length} stops):</h4>
                <div className="preview-scroll">
                  <table className="preview-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Type</th>
                        <th>Location</th>
                        <th>Service Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.preview.map((stop, idx) => (
                        <tr key={idx}>
                          <td>{stop.stop_sequence}</td>
                          <td>
                            <span className={`badge badge-${stop.stop_type.toLowerCase()}`}>
                              {stop.stop_type}
                            </span>
                          </td>
                          <td>
                            {stop.city && stop.state ? (
                              <span>{stop.city}, {stop.state}</span>
                            ) : stop.latitude && stop.longitude ? (
                              <span className="coords">
                                {stop.latitude.toFixed(4)}, {stop.longitude.toFixed(4)}
                              </span>
                            ) : (
                              <span className="text-muted">—</span>
                            )}
                          </td>
                          <td>{stop.service_duration_minutes} min</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Instructions */}
        <div className="instructions">
          <h4 className="instructions-title">CSV Requirements:</h4>
          <ul className="instructions-list">
            <li><strong>Required columns:</strong> stop_sequence, stop_type, service_duration_minutes</li>
            <li><strong>Location:</strong> Provide either (latitude + longitude) OR (address + city + state + zip)</li>
            <li><strong>Stop types:</strong> PICKUP, DELIVERY, or WAYPOINT</li>
            <li><strong>Time format:</strong> ISO8601 (e.g., 2026-01-20T08:00:00)</li>
            <li><strong>Phone format:</strong> 10 digits, no dashes (e.g., 2145551234)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
