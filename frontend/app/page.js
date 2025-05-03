"use client";
import { useState, useRef } from 'react';
import axios from 'axios';

export default function Home() {
  const [file, setFile] = useState(null);
  const [uploadId, setUploadId] = useState(null);
  const [fastaFile, setFastaFile] = useState(null);
  const [metadataFile, setMetadataFile] = useState(null);
  const [isEncoding, setIsEncoding] = useState(false);
  const [isDecoding, setIsDecoding] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [downloadLink, setDownloadLink] = useState(null);
  const fileInputRef = useRef();
  const fastaInputRef = useRef();
  const metadataInputRef = useRef();

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleFastaChange = (e) => {
    setFastaFile(e.target.files[0]);
  };

  const handleMetadataChange = (e) => {
    setMetadataFile(e.target.files[0]);
  };

  const uploadFile = async () => {
    if (!file) {
      alert('Please select a file first');
      return;
    }
  
    setIsEncoding(true);
    setProgress(0);
    setResult(null);
  
    try {
      const formData = new FormData();
      formData.append('file', file);
  
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / (progressEvent.total || 100)
          );
          setProgress(percentCompleted);
        },
      });
  
      setProgress(100);
      setResult(response.data);
      setUploadId(response.data.upload_id);
    } catch (error) {
      console.error('Upload error:', error);
      setResult({ 
        error: 'Upload failed',
        details: error.response?.data?.error || error.message,
        stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
      });
    } finally {
      setIsEncoding(false);
    }
  };

  const decodeFile = async () => {
    if (!fastaFile || !metadataFile) {
      alert('Please select both FASTA and metadata files');
      return;
    }

    setIsDecoding(true);
    setProgress(0);
    setResult(null);

    const formData = new FormData();
    formData.append('file', fastaFile);
    formData.append('metadata', metadataFile);

    try {
      const interval = setInterval(() => {
        setProgress((prev) => {
          const newProgress = prev + 10;
          if (newProgress >= 90) clearInterval(interval);
          return newProgress;
        });
      }, 300);

      const response = await axios.post('/api/decode', formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 90) / progressEvent.total
          );
          setProgress(percentCompleted);
        },
      });

      clearInterval(interval);
      setProgress(100);
      setResult(response.data);
      
      if (response.data.decoded_file) {
        setDownloadLink(response.data.decoded_file);
      }

      setTimeout(() => {
        setProgress(0);
        setIsDecoding(false);
      }, 1000);
    } catch (error) {
      console.error('Error decoding file:', error);
      setResult({ error: error.message });
      setProgress(0);
      setIsDecoding(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setFastaFile(null);
    setMetadataFile(null);
    setResult(null);
    setDownloadLink(null);
    setUploadId(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (fastaInputRef.current) fastaInputRef.current.value = '';
    if (metadataInputRef.current) metadataInputRef.current.value = '';
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-gray-900 mb-2">
            Chromify DNA Storage Simulator
          </h1>
          <p className="text-lg text-gray-600">
            Encode files into synthetic DNA sequences and decode them back
          </p>
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Encode a File to DNA
          </h2>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select file to encode
            </label>
            <input
              type="file"
              onChange={handleFileChange}
              ref={fileInputRef}
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
              disabled={isEncoding}
            />
          </div>

          {isEncoding && (
            <div className="mb-4">
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium text-blue-700">
                  Encoding in progress...
                </span>
                <span className="text-sm font-medium text-blue-700">
                  {progress}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className="bg-blue-600 h-2.5 rounded-full"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}

          <div className="flex space-x-3">
            <button
              onClick={uploadFile}
              disabled={!file || isEncoding}
              className={`px-4 py-2 rounded-md text-sm font-medium text-white ${
                !file || isEncoding
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              Encode to DNA
            </button>
            <button
              onClick={resetForm}
              className="px-4 py-2 rounded-md text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200"
            >
              Reset
            </button>
          </div>

          {result && !isEncoding && (
            <div className="mt-4 p-4 bg-blue-50 rounded-md">
              {result.error ? (
                <p className="text-red-600">{result.error}</p>
              ) : (
                <>
                  <h3 className="font-medium text-blue-800 mb-2">Encoding Results</h3>
                  <p className="text-sm text-gray-700">
                    File: <span className="font-mono">{result.filename}</span>
                  </p>
                  <p className="text-sm text-gray-700">
                    DNA length: <span className="font-mono">{result.length_bases}</span> bases
                  </p>
                  <p className="text-sm text-gray-700">
                    GC content: <span className="font-mono">{result.validation.gc_content}%</span>
                  </p>
                  {uploadId && (
                    <p className="text-sm text-gray-700 mt-2">
                      Use upload ID: <span className="font-mono bg-blue-100 px-2 py-1 rounded">{uploadId}</span>
                    </p>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Decode DNA to File
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                FASTA file
              </label>
              <input
                type="file"
                onChange={handleFastaChange}
                ref={fastaInputRef}
                accept=".fasta,.fa"
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-md file:border-0
                  file:text-sm file:font-semibold
                  file:bg-green-50 file:text-green-700
                  hover:file:bg-green-100"
                disabled={isDecoding}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Metadata file
              </label>
              <input
                type="file"
                onChange={handleMetadataChange}
                ref={metadataInputRef}
                accept=".json"
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-md file:border-0
                  file:text-sm file:font-semibold
                  file:bg-green-50 file:text-green-700
                  hover:file:bg-green-100"
                disabled={isDecoding}
              />
            </div>
          </div>

          {isDecoding && (
            <div className="mb-4">
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium text-green-700">
                  Decoding in progress...
                </span>
                <span className="text-sm font-medium text-green-700">
                  {progress}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className="bg-green-600 h-2.5 rounded-full"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}

          <div className="flex space-x-3">
            <button
              onClick={decodeFile}
              disabled={!fastaFile || !metadataFile || isDecoding}
              className={`px-4 py-2 rounded-md text-sm font-medium text-white ${
                !fastaFile || !metadataFile || isDecoding
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-green-600 hover:bg-green-700'
              }`}
            >
              Decode to Original File
            </button>
            <button
              onClick={resetForm}
              className="px-4 py-2 rounded-md text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200"
            >
              Reset
            </button>
          </div>

          {result && !isDecoding && (
            <div className="mt-4 p-4 bg-green-50 rounded-md">
              {result.error ? (
                <p className="text-red-600">{result.error}</p>
              ) : (
                <>
                  <h3 className="font-medium text-green-800 mb-2">Decoding Results</h3>
                  <p className="text-sm text-gray-700">
                    Segments recovered: <span className="font-mono">{result.segments_recovered}</span>/
                    <span className="font-mono">{result.total_segments}</span>
                  </p>
                  <p className="text-sm text-gray-700">
                    Recovery rate: <span className="font-mono">{result.recovery_rate}</span>
                  </p>
                  {downloadLink && (
                    <div className="mt-3">
                      <a
                        href={`/api/download?path=${encodeURIComponent(result.decoded_file)}`}
                        className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                      >
                        Download Decoded File
                      </a>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        <div className="mt-8 text-center text-sm text-gray-500">
          <p>Chromify - DNA-based File Storage Simulator</p>
        </div>
      </div>
    </div>
  );
}