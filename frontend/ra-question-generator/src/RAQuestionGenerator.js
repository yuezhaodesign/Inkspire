import React, { useState, useRef } from 'react';
import { Upload, FileText, BookOpen, Users, User, Brain, Lightbulb, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

const RAQuestionGenerator = () => {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  // Function to process the uploaded file with Python backend
  const processFile = async () => {
    if (!file) {
      setError('Please upload a file first.');
      return;
    }

    setIsProcessing(true);
    setError('');
    
    try {
      // Create FormData to send file to backend
      const formData = new FormData();
      formData.append('file', file);

      // Call your Python backend API
      const response = await fetch('http://localhost:8000/process-file', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Transform backend response to match our UI structure
      const transformedResults = {
        extracted_info: data.extracted_info || 'No information extracted',
        relevant_context: data.relevant_context || 'No relevant context found',
        questions: data.questions || 'No questions generated',
        prompts: data.prompts || 'No prompts generated',
        evaluation: data.evaluation || 'No evaluation available'
      };

      setResults(transformedResults);
    } catch (err) {
      console.error('Error processing file:', err);
      setError(`Error processing file: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFileUpload = (event) => {
    const uploadedFile = event.target.files[0];
    if (uploadedFile) {
      const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
      if (validTypes.includes(uploadedFile.type)) {
        setFile(uploadedFile);
        setError('');
        setResults(null); // Clear previous results
      } else {
        setError('Please upload a PDF, DOCX, or TXT file.');
        setFile(null);
      }
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      const event = { target: { files: [droppedFile] } };
      handleFileUpload(event);
    }
  };

  const formatContent = (content) => {
    if (!content || typeof content !== 'string') return null;
    
    return content.split('\n').map((line, index) => {
      if (line.trim() === '') return <br key={index} />;
      if (line.startsWith('•') || line.startsWith('-')) {
        return <li key={index} className="ml-4 list-disc">{line.substring(1).trim()}</li>;
      }
      if (line.match(/^\d+\./)) {
        return <div key={index} className="font-medium text-gray-800 mt-2">{line}</div>;
      }
      return <p key={index} className="mb-2">{line}</p>;
    });
  };

  const getDimensionIcon = (index) => {
    const icons = [
      <Users className="w-5 h-5 text-blue-600" />,
      <User className="w-5 h-5 text-green-600" />,
      <Brain className="w-5 h-5 text-purple-600" />,
      <Lightbulb className="w-5 h-5 text-orange-600" />
    ];
    return icons[index] || <FileText className="w-5 h-5 text-gray-600" />;
  };

  const getDimensionName = (index) => {
    const names = ['Social', 'Personal', 'Cognitive', 'Knowledge-Building'];
    return names[index] || 'Question';
  };

  const getDimensionColor = (index) => {
    const colors = ['bg-blue-50 border-blue-200', 'bg-green-50 border-green-200', 'bg-purple-50 border-purple-200', 'bg-orange-50 border-orange-200'];
    return colors[index] || 'bg-gray-50 border-gray-200';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <BookOpen className="w-12 h-12 text-indigo-600 mr-3" />
            <h1 className="text-4xl font-bold text-gray-800">Reading Apprenticeship</h1>
          </div>
          <h2 className="text-2xl text-gray-600 mb-2">Question Generator</h2>
          <p className="text-gray-500 max-w-2xl mx-auto">
            Upload your educational content and generate Reading Apprenticeship framework questions 
            with teacher facilitation prompts automatically.
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
          <h3 className="text-xl font-semibold text-gray-800 mb-6 flex items-center">
            <Upload className="w-6 h-6 mr-2 text-indigo-600" />
            Upload Your Document
          </h3>
          
          {/* File Upload Area */}
          <div className="max-w-2xl mx-auto">
            <div
              className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-indigo-400 transition-colors cursor-pointer"
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-lg text-gray-600 mb-2">
                Drop your file here or <span className="text-indigo-600 font-medium">click to browse</span>
              </p>
              <p className="text-sm text-gray-500">
                Supports PDF, DOCX, and TXT files (Max 10MB)
              </p>
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileUpload}
                accept=".pdf,.docx,.txt"
                className="hidden"
              />
            </div>
            
            {file && (
              <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center">
                  <FileText className="w-5 h-5 text-green-600 mr-2" />
                  <span className="text-green-800 font-medium">{file.name}</span>
                </div>
                <p className="text-sm text-green-600 mt-1">
                  {(file.size / 1024).toFixed(1)} KB • Ready to process
                </p>
              </div>
            )}
          </div>

          {error && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center max-w-2xl mx-auto">
              <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
              <span className="text-red-800">{error}</span>
            </div>
          )}

          <div className="mt-8 flex justify-center">
            <button
              onClick={processFile}
              disabled={!file || isProcessing}
              className="px-10 py-4 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center text-lg"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-6 h-6 mr-3 animate-spin" />
                  Generating Questions...
                </>
              ) : (
                <>
                  <Brain className="w-6 h-6 mr-3" />
                  Generate RA Questions
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results Section */}
        {results && (
          <div className="space-y-6">
            {/* Extracted Information */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
                <FileText className="w-6 h-6 mr-2 text-indigo-600" />
                Document Analysis
              </h3>
              <div className="prose prose-sm max-w-none text-gray-700">
                {formatContent(results.extracted_info)}
              </div>
            </div>

            {/* Relevant Context */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
                <BookOpen className="w-6 h-6 mr-2 text-indigo-600" />
                Relevant Context
              </h3>
              <div className="prose prose-sm max-w-none text-gray-700">
                {formatContent(results.relevant_context)}
              </div>
            </div>

            {/* Generated Questions */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-xl font-semibold text-gray-800 mb-6 flex items-center">
                <Brain className="w-6 h-6 mr-2 text-indigo-600" />
                Reading Apprenticeship Questions
              </h3>
              
              <div className="grid gap-4">
                {results.questions.split('\n').filter(line => line.match(/^\d+\./)).map((question, index) => (
                  <div key={index} className={`p-4 rounded-lg border-2 ${getDimensionColor(index)}`}>
                    <div className="flex items-start mb-3">
                      {getDimensionIcon(index)}
                      <div className="ml-3">
                        <span className="font-semibold text-gray-800">{getDimensionName(index)} Dimension</span>
                      </div>
                    </div>
                    <p className="text-gray-700 leading-relaxed">
                      {question.replace(/^\d+\.\s*/, '')}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Teacher Prompts */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-xl font-semibold text-gray-800 mb-6 flex items-center">
                <Users className="w-6 h-6 mr-2 text-green-600" />
                Teacher Facilitation Prompts
              </h3>
              
              <div className="grid gap-4">
                {results.prompts.split('\n').filter(line => line.match(/^\d+\./)).map((prompt, index) => (
                  <div key={index} className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-start mb-2">
                      <span className="inline-flex items-center justify-center w-6 h-6 bg-green-600 text-white text-sm font-bold rounded-full mr-3">
                        {index + 1}
                      </span>
                      <span className="font-medium text-gray-800">{getDimensionName(index)} Prompt</span>
                    </div>
                    <p className="text-gray-700 ml-9">
                      {prompt.replace(/^\d+\.\s*/, '')}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Quality Evaluation */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
                <CheckCircle className="w-6 h-6 mr-2 text-green-600" />
                Quality Evaluation
              </h3>
              <div className="prose prose-sm max-w-none text-gray-700">
                {formatContent(results.evaluation)}
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-12 text-center text-gray-500 text-sm">
          <p>Reading Apprenticeship Question Generator • Powered by AI</p>
          <p className="mt-1">Upload educational content to generate framework-aligned questions automatically</p>
        </div>
      </div>
    </div>
  );
};

export default RAQuestionGenerator;