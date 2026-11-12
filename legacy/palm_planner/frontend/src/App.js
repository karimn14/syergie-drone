import React, { useState, useRef, useEffect } from 'react';

const LeafletLoader = () => {
  const [scriptsLoaded, setScriptsLoaded] = useState(false);

  useEffect(() => {
    // Load Leaflet CSS
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
    link.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
    link.crossOrigin = '';
    document.head.appendChild(link);

    // Load Leaflet JS
    const scriptLeaflet = document.createElement('script');
    scriptLeaflet.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    scriptLeaflet.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
    scriptLeaflet.crossOrigin = '';
    
    scriptLeaflet.onload = () => {
      // Fix for default Leaflet icons
      const L = window.L;
      delete L.Icon.Default.prototype._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      });
      
      setScriptsLoaded(true);
    };

    document.head.appendChild(scriptLeaflet);

    return () => {
      if (document.head.contains(link)) {
        document.head.removeChild(link);
      }
      if (document.head.contains(scriptLeaflet)) {
        document.head.removeChild(scriptLeaflet);
      }
    };
  }, []);

  return null;
};

function App() {
  const [selectedBounds, setSelectedBounds] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [resultMessage, setResultMessage] = useState('');
  const [waypointsFile, setWaypointsFile] = useState(null);
  const [error, setError] = useState('');
  const [librariesLoaded, setLibrariesLoaded] = useState(false);
  const [mapCenter, setMapCenter] = useState([-6.851366105594212, 107.31648370693048]);
  const [mapZoom, setMapZoom] = useState(17);
  const [visualization, setVisualization] = useState('');
  const [statistics, setStatistics] = useState(null);
  
  // Model state
  const [currentModel, setCurrentModel] = useState('local_custom');
  const [availableModels, setAvailableModels] = useState([
    'local_custom',
    'roboflow_workflow',
    'roboflow_local'
  ]);
  
  // State untuk input koordinat
  const [inputCoord, setInputCoord] = useState({
    lat: '-6.851366105594212',
    lng: '107.31648370693048'
  });
  const [coordError, setCoordError] = useState('');

  const mapRef = useRef(null);
  const rectangleRef = useRef(null);

  useEffect(() => {
    const interval = setInterval(() => {
      if (window.L) {
        clearInterval(interval);
        setLibrariesLoaded(true);
      }
    }, 100);

    return () => clearInterval(interval);
  }, []);

  const handleSelection = (bounds) => {
    setSelectedBounds(bounds);
  };
  
  // Fungsi untuk switch model
  const switchModel = async (modelName) => {
    try {
      const response = await fetch('http://localhost:5000/switch_model', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ model: modelName }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setCurrentModel(modelName);
        // Reset results ketika ganti model
        setResultMessage('');
        setWaypointsFile(null);
        setVisualization('');
        setStatistics(null);
        setError('');
        
        // Show success message
        setResultMessage(`Model switched to ${modelName} successfully`);
        setTimeout(() => setResultMessage(''), 3000);
      } else {
        const errorData = await response.json();
        setError(`Failed to switch model: ${errorData.error}`);
      }
    } catch (error) {
      console.error('Error switching model:', error);
      setError(`Error switching model: ${error.message}`);
    }
  };

  // Fungsi untuk handle input koordinat
  const handleCoordInput = () => {
    const lat = parseFloat(inputCoord.lat);
    const lng = parseFloat(inputCoord.lng);
    
    if (isNaN(lat) || isNaN(lng)) {
      setCoordError('Format koordinat tidak valid. Gunakan format angka.');
      return;
    }
    
    if (lat < -90 || lat > 90) {
      setCoordError('Latitude harus antara -90 dan 90 derajat');
      return;
    }
    
    if (lng < -180 || lng > 180) {
      setCoordError('Longitude harus antara -180 dan 180 derajat');
      return;
    }
    
    setCoordError('');
    setMapCenter([lat, lng]);
    
    // Reset selection ketika pindah lokasi
    setSelectedBounds(null);
    setResultMessage('');
    setWaypointsFile(null);
    setVisualization('');
    setStatistics(null);
  };
  
  // Fungsi untuk menggunakan lokasi saat ini
  const useCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          
          setInputCoord({
            lat: lat.toString(),
            lng: lng.toString()
          });
          setMapCenter([lat, lng]);
          setCoordError('');
        },
        (error) => {
          setCoordError('Tidak dapat mengakses lokasi saat ini: ' + error.message);
        }
      );
    } else {
      setCoordError('Browser tidak mendukung geolocation');
    }
  };

  const handleProcess = async () => {
    if (!selectedBounds) {
      setError('Silakan pilih sebuah area di peta terlebih dahulu.');
      return;
    }
    
    setIsLoading(true);
    setError('');
    setResultMessage('');
    setWaypointsFile(null);
    setVisualization('');
    setStatistics(null);

    try {
      // Convert bounds to format expected by backend
      const boundsData = {
        _southWest: {
          lat: selectedBounds.getSouthWest().lat,
          lng: selectedBounds.getSouthWest().lng
        },
        _northEast: {
          lat: selectedBounds.getNorthEast().lat,
          lng: selectedBounds.getNorthEast().lng
        }
      };

      const response = await fetch('http://localhost:5000/process_region', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ bounds: boundsData }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setResultMessage(data.message);
      if (data.waypoints_file) {
        setWaypointsFile(data.waypoints_file);
      }
      if (data.visualization) {
        setVisualization(data.visualization);
      }
      if (data.statistics) {
        setStatistics(data.statistics);
      }

    } catch (e) {
      setError(`Gagal memproses: ${e.message}`);
      console.error('Error details:', e);
    } finally {
      setIsLoading(false);
    }
  };

  // Fungsi untuk download file waypoints
  const handleDownloadWaypoints = () => {
    if (!waypointsFile) return;
    
    const blob = new Blob([waypointsFile], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'mission.waypoints';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Fungsi untuk preview waypoints data
  const handlePreviewWaypoints = async () => {
    if (!selectedBounds) {
      setError('Silakan pilih area terlebih dahulu.');
      return;
    }

    try {
      const boundsData = {
        _southWest: {
          lat: selectedBounds.getSouthWest().lat,
          lng: selectedBounds.getSouthWest().lng
        },
        _northEast: {
          lat: selectedBounds.getNorthEast().lat,
          lng: selectedBounds.getNorthEast().lng
        }
      };

      const response = await fetch('http://localhost:5000/get_waypoints_data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ bounds: boundsData }),
      });

      if (!response.ok) {
        throw new Error('Gagal mengambil data waypoints');
      }

      const data = await response.json();
      alert(`Preview Waypoints:\n\nTotal Waypoints: ${data.waypoints_count}\nFile akan berisi ${data.waypoints_count} waypoints termasuk home position dan loiter points.`);

    } catch (error) {
      setError('Gagal memuat preview waypoints: ' + error.message);
    }
  };

  // Fungsi untuk langsung download waypoints tanpa processing
  const handleDirectDownloadWaypoints = async () => {
    if (!selectedBounds) {
      setError('Silakan pilih area terlebih dahulu.');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const boundsData = {
        _southWest: {
          lat: selectedBounds.getSouthWest().lat,
          lng: selectedBounds.getSouthWest().lng
        },
        _northEast: {
          lat: selectedBounds.getNorthEast().lat,
          lng: selectedBounds.getNorthEast().lng
        }
      };

      const response = await fetch('http://localhost:5000/download_waypoints', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ bounds: boundsData }),
      });

      if (!response.ok) {
        throw new Error('Gagal mengunduh file waypoints');
      }

      // Handle file download
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'mission.waypoints';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setResultMessage('File waypoints berhasil diunduh!');

    } catch (e) {
      setError(`Gagal mengunduh waypoints: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  if (!librariesLoaded) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <LeafletLoader />
        <div className="text-xl font-semibold text-gray-600">Memuat Pustaka Peta...</div>
      </div>
    );
  }

  const MapWithSelection = ({ center, zoom, onSelection }) => {
    const mapContainerRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const startPosRef = useRef(null);
    const currentRectRef = useRef(null);
    const isDrawingRef = useRef(false);

    useEffect(() => {
      if (!mapContainerRef.current || mapInstanceRef.current) return;

      // Initialize map
      const map = window.L.map(mapContainerRef.current).setView(center, zoom);
      mapInstanceRef.current = map;

      // Add Satellite Imagery Layer (Google Satellite)
      const googleSat = window.L.tileLayer('https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
        maxZoom: 20,
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
        attribution: '&copy; Google'
      });

      // Add OpenStreetMap as fallback
      const osm = window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      });

      googleSat.addTo(map);

      // Store map instance in parent ref
      if (mapRef.current) {
        mapRef.current.map = map;
      }

      // Update map view when center changes
      const updateMapView = () => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.setView(center, zoom);
        }
      };

      // Right-click selection logic
      const handleContextMenu = (e) => {
        e.originalEvent.preventDefault();
        
        isDrawingRef.current = true;
        startPosRef.current = e.latlng;
        
        if (currentRectRef.current) {
          map.removeLayer(currentRectRef.current);
        }
        
        currentRectRef.current = window.L.rectangle([startPosRef.current, startPosRef.current], {
          color: 'red',
          weight: 2,
          fillOpacity: 0.1,
          dashArray: '5,5'
        }).addTo(map);
      };

      const handleMouseMove = (e) => {
        if (!isDrawingRef.current || !startPosRef.current) return;
        currentRectRef.current.setBounds([startPosRef.current, e.latlng]);
      };

      const handleMouseUp = (e) => {
        if (!isDrawingRef.current || !startPosRef.current) return;
        
        if (e.originalEvent.button === 0) {
          isDrawingRef.current = false;
          const bounds = window.L.latLngBounds(startPosRef.current, e.latlng);
          
          if (currentRectRef.current) {
            map.removeLayer(currentRectRef.current);
            currentRectRef.current = null;
          }
          
          if (rectangleRef.current) {
            map.removeLayer(rectangleRef.current);
          }
          
          rectangleRef.current = window.L.rectangle(bounds, {
            color: 'blue',
            weight: 3,
            fillOpacity: 0.1
          }).addTo(map);
          
          onSelection(bounds);
          startPosRef.current = null;
        }
      };

      // Add event listeners
      map.on('contextmenu', handleContextMenu);
      map.on('mousemove', handleMouseMove);
      map.on('mouseup', handleMouseUp);

      // Cleanup function
      return () => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.remove();
          mapInstanceRef.current = null;
        }
      };
    }, []);

    // Effect untuk update center
    useEffect(() => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.setView(center, zoom);
      }
    }, [center, zoom]);

    return <div ref={mapContainerRef} style={{ height: '100%', width: '100%' }} />;
  };

  return (
    <div className="flex flex-col h-screen font-sans bg-gray-50">
      <LeafletLoader />
      
      {/* Header */}
      <header className="bg-green-800 text-white p-4 shadow-lg z-10">
        <div className="container mx-auto">
          <h1 className="text-2xl font-bold">Palm Tree Mission Planner</h1>
          <p className="text-sm text-green-200">Deteksi Pohon Sawit dari Citra Satelit - Sistem Cerdas Perkebunan</p>
        </div>
      </header>
      
      <div className="flex flex-grow overflow-hidden">
        {/* Control Panel */}
        <div className="w-1/3 bg-white p-6 overflow-y-auto z-10 border-r border-gray-200 shadow-inner">
          <div className="space-y-6">
            
            {/* Input Koordinat Section */}
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <h2 className="text-lg font-semibold text-blue-800 mb-3">📍 Set Koordinat Peta</h2>
              
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-blue-700 mb-1">Latitude</label>
                  <input
                    type="text"
                    value={inputCoord.lat}
                    onChange={(e) => setInputCoord({...inputCoord, lat: e.target.value})}
                    placeholder="-6.851366105594212"
                    className="w-full p-2 border border-blue-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-blue-700 mb-1">Longitude</label>
                  <input
                    type="text"
                    value={inputCoord.lng}
                    onChange={(e) => setInputCoord({...inputCoord, lng: e.target.value})}
                    placeholder="107.31648370693048"
                    className="w-full p-2 border border-blue-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                
                {coordError && (
                  <div className="text-red-500 text-sm bg-red-50 p-2 rounded border border-red-200">
                    ⚠️ {coordError}
                  </div>
                )}
                
                <div className="flex space-x-2">
                  <button
                    onClick={handleCoordInput}
                    className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition duration-200 font-medium"
                  >
                    Setel Peta
                  </button>
                  
                  <button
                    onClick={useCurrentLocation}
                    className="bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition duration-200 font-medium"
                    title="Gunakan lokasi saat ini"
                  >
                    📍
                  </button>
                </div>
              </div>
            </div>

            {/* Instructions */}
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <h2 className="text-xl font-semibold text-gray-800 mb-3">📋 Petunjuk Penggunaan</h2>
              <ol className="list-decimal list-inside space-y-2 text-gray-600 text-sm">
                <li>Setel koordinat peta atau gunakan lokasi saat ini</li>
                <li><strong>Klik kanan</strong> untuk memulai seleksi area</li>
                <li><strong>Geser mouse</strong> untuk menentukan area seleksi</li>
                <li><strong>Klik kiri</strong> untuk mengakhiri seleksi</li>
                <li>Klik <strong>"Proses Area Terpilih"</strong> untuk analisis</li>
                <li>Download file mission waypoints jika berhasil</li>
              </ol>
            </div>
            
            {/* Model selection */}
            <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 rounded-lg border border-purple-200">
              <h3 className="font-semibold text-purple-800 mb-3">AI Model Selection</h3>
              
              <div className="grid grid-cols-1 gap-2">
                <button
                  onClick={() => switchModel('local_custom')}
                  className={`p-3 rounded-lg border-2 text-left ${
                    currentModel === 'local_custom'
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-300 bg-white hover:bg-gray-50'
                  }`}
                >
                  <div className="font-medium">Custom YOLO Model</div>
                  <div className="text-sm text-gray-600">Your trained model - Best Performance</div>
                </button>
                
                <button
                  onClick={() => switchModel('roboflow_workflow')}
                  className={`p-3 rounded-lg border-2 text-left ${
                    currentModel === 'roboflow_workflow'
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-300 bg-white hover:bg-gray-50'
                  }`}
                >
                  <div className="font-medium">Roboflow Cloud</div>
                  <div className="text-sm text-gray-600">Real-time API - Most Accurate</div>
                </button>
                
                <button
                  onClick={() => switchModel('roboflow_local')}
                  className={`p-3 rounded-lg border-2 text-left ${
                    currentModel === 'roboflow_local'
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-300 bg-white hover:bg-gray-50'
                  }`}
                >
                  <div className="font-medium">Local Roboflow</div>
                  <div className="text-sm text-gray-600">Offline - Fast Inference</div>
                </button>
              </div>
              
              <div className="mt-3 p-2 bg-blue-50 rounded border border-blue-200">
                <div className="text-sm text-blue-700">
                  <span className="font-medium">Current: </span>
                  {currentModel === 'local_custom' && '🔧 Custom YOLO Model'}
                  {currentModel === 'roboflow_workflow' && '🌐 Roboflow Cloud Workflow'}
                  {currentModel === 'roboflow_local' && '💻 Local Roboflow Model'} 
                </div>
              </div>
            </div>
            
            {/* Quick Actions */}
            <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
              <h3 className="font-semibold text-yellow-800 mb-3">Quick Actions</h3>
              
              <div className="grid grid-cols-1 gap-2">
                <button
                  onClick={handlePreviewWaypoints}
                  disabled={!selectedBounds}
                  className={`p-3 rounded-lg border-2 text-left ${
                    !selectedBounds ? 'bg-gray-100 text-gray-400' : 'bg-white border-yellow-300 hover:bg-yellow-50'
                  }`}
                >
                  <div className="font-medium">Preview Waypoints</div>
                  <div className="text-sm">Lihat preview waypoints sebelum download</div>
                </button>
                
                <button
                  onClick={handleDirectDownloadWaypoints}
                  disabled={!selectedBounds || isLoading}
                  className={`p-3 rounded-lg border-2 text-left ${
                    !selectedBounds || isLoading ? 'bg-gray-100 text-gray-400' : 'bg-white border-green-300 hover:bg-green-50'
                  }`}
                >
                  <div className="font-medium">Direct Download Waypoints</div>
                  <div className="text-sm">Download waypoints tanpa processing detail</div>
                </button>
              </div>
            </div>

            {/* Action Button */}
            <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
              <button 
                onClick={handleProcess}
                disabled={isLoading || !selectedBounds}
                className={`w-full py-3 px-4 rounded-lg font-bold transition duration-300 ${
                  isLoading || !selectedBounds
                    ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                    : 'bg-green-600 text-white hover:bg-green-700 shadow-md hover:shadow-lg transform hover:-translate-y-0.5'
                }`}
              >
                {isLoading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Memproses...
                  </span>
                ) : 'Proses Area Terpilih'}
              </button>
            </div>

            {/* Selected Area Info */}
            {selectedBounds && (
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                <h3 className="font-semibold text-blue-800 mb-2">Area Terpilih:</h3>
                <div className="text-sm text-blue-700 space-y-1">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="font-medium">Barat Daya:</span>
                      <div>Lat: {selectedBounds.getSouthWest().lat.toFixed(6)}</div>
                      <div>Lng: {selectedBounds.getSouthWest().lng.toFixed(6)}</div>
                    </div>
                    <div>
                      <span className="font-medium">Timur Laut:</span>
                      <div>Lat: {selectedBounds.getNorthEast().lat.toFixed(6)}</div>
                      <div>Lng: {selectedBounds.getNorthEast().lng.toFixed(6)}</div>
                    </div>
                  </div>
                  <div className="pt-2 border-t border-blue-200">
                    <span className="font-medium">Luas Area: </span>
                    {((selectedBounds.getNorthEast().lat - selectedBounds.getSouthWest().lat) * 
                      (selectedBounds.getNorthEast().lng - selectedBounds.getSouthWest().lng) * 
                      10000).toFixed(2)} hektar
                  </div>
                </div>
              </div>
            )}

            {/* Results Section */}
            <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
              <h3 className="font-semibold text-lg text-gray-800 mb-3">📊 Hasil Analisis</h3>
              
              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center text-red-800 font-medium mb-1">
                    <span className="text-lg mr-2">❌</span>
                    Terjadi Kesalahan
                  </div>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              )}
              
              {resultMessage && (
                <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center text-green-800 font-medium mb-1">
                    <span className="text-lg mr-2">✅</span>
                    Berhasil
                  </div>
                  <p className="text-green-700">{resultMessage}</p>
                  
                  {statistics && (
                    <div className="mt-3 p-2 bg-white rounded border border-green-100">
                      <div className="grid grid-cols-2 gap-2 text-sm text-green-800">
                        <div>Pohon Terdeteksi: <span className="font-bold">{statistics.trees_detected}</span></div>
                        <div>Luas Area: <span className="font-bold">{statistics.area_hectares.toFixed(2)} ha</span></div>
                        <div>Kepadatan: <span className="font-bold">{statistics.tree_density.toFixed(2)}/ha</span></div>
                        {statistics.average_confidence && (
                          <div>Confidence: <span className="font-bold">{(statistics.average_confidence * 100).toFixed(1)}%</span></div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {waypointsFile && (
                <div className="mb-4">
                  <button
                    onClick={handleDownloadWaypoints}
                    className="w-full bg-green-500 text-white font-bold py-3 px-4 rounded-lg hover:bg-green-600 transition duration-300 shadow-md hover:shadow-lg"
                  >
                    📥 Download Mission.waypoints
                  </button>
                  <div className="mt-2 text-sm text-gray-600 text-center">
                    Format QGC WPL 110 dengan loiter time 5 detik
                  </div>
                </div>
              )}

              {/* Visualization */}
              {visualization && (
                <div className="mt-4">
                  <h4 className="font-semibold text-gray-700 mb-2">Visualisasi Deteksi</h4>
                  <img 
                    src={visualization} 
                    alt="Hasil deteksi pohon sawit" 
                    className="w-full rounded-lg border border-gray-300 shadow-sm"
                  />
                  <p className="text-xs text-gray-500 mt-2 text-center">
                    Peta distribusi pohon sawit yang terdeteksi dalam area terpilih
                  </p>
                </div>
              )}

              {!isLoading && !resultMessage && !error && (
                <div className="text-center py-8 text-gray-400">
                  <div className="text-4xl mb-2">🌴</div>
                  <p>Pilih area pada peta untuk memulai analisis</p>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Map */}
        <div className="w-2/3 h-full relative">
          <div className="absolute top-4 left-4 z-20 bg-white px-3 py-2 rounded-lg shadow-md border border-gray-200">
            <div className="text-sm text-gray-600">
              <div>Center: {mapCenter[0].toFixed(6)}, {mapCenter[1].toFixed(6)}</div>
              <div>Zoom: {mapZoom}</div>
              <div>Model: {currentModel === 'local_custom' ? 'Custom YOLO' : currentModel}</div>
            </div>
          </div>
          
          <MapWithSelection 
            center={mapCenter}
            zoom={mapZoom}
            onSelection={handleSelection}
          />
        </div>
      </div>
    </div>
  );
}

export default App;