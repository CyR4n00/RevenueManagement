import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Facility {
  id: number;
  name: string;
  base_price: number;
  total_rooms: number;
}

interface PriceRecommendation {
  facility_id: number;
  date: string;
  recommended_price: number;
  rule_applied: string | null;
}

interface OccupancyData {
  facility_id: number;
  date: string;
  booked_rooms: number;
}

function App() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacility, setSelectedFacility] = useState<number | null>(null);
  const [recommendation, setRecommendation] = useState<PriceRecommendation | null>(null);
  const [occupancy, setOccupancy] = useState<OccupancyData | null>(null);

  useEffect(() => {
    fetchFacilities();
  }, []);

  useEffect(() => {
    if (selectedFacility) {
      fetchDashboardData(selectedFacility);
    }
  }, [selectedFacility]);

  const fetchFacilities = async () => {
    try {
      const response = await axios.get('http://localhost:8000/facilities');
      setFacilities(response.data);
      if (response.data.length > 0) {
        setSelectedFacility(response.data[0].id);
      }
    } catch (error) {
      console.error("Error fetching facilities:", error);
    }
  };

  const fetchDashboardData = async (facilityId: number) => {
    try {
      const today = new Date().toISOString().split('T')[0];

      const occResponse = await axios.get(`http://localhost:8000/occupancy?facility_id=${facilityId}`);
      const todayOcc = occResponse.data.find((o: any) => o.date === today);
      setOccupancy(todayOcc || null);

      const recResponse = await axios.get(`http://localhost:8000/recommendations/${facilityId}/${today}`);
      setRecommendation(recResponse.data);
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
      setRecommendation(null);
      setOccupancy(null);
    }
  };

  const selectedFacilityData = facilities.find(f => f.id === selectedFacility);

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <header className="mb-8 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-800">Revenue Control Dashboard</h1>
          <select
            className="p-2 border rounded shadow-sm"
            value={selectedFacility || ''}
            onChange={(e) => setSelectedFacility(Number(e.target.value))}
          >
            {facilities.map(f => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </select>
        </header>

        {selectedFacilityData && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-sm font-semibold text-gray-500 uppercase">Base Price</h2>
              <p className="text-3xl font-bold text-gray-800 mt-2">¥{selectedFacilityData.base_price.toLocaleString()}</p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-sm font-semibold text-gray-500 uppercase">Today's Occupancy</h2>
              {occupancy ? (
                <>
                  <p className="text-3xl font-bold text-blue-600 mt-2">
                    {Math.round((occupancy.booked_rooms / selectedFacilityData.total_rooms) * 100)}%
                  </p>
                  <p className="text-sm text-gray-500 mt-1">{occupancy.booked_rooms} / {selectedFacilityData.total_rooms} rooms</p>
                </>
              ) : (
                <p className="text-xl text-gray-500 mt-2">No data</p>
              )}
            </div>

            <div className="bg-white rounded-lg shadow p-6 border-2 border-blue-500">
              <h2 className="text-sm font-semibold text-blue-500 uppercase">Recommended Price</h2>
              {recommendation ? (
                <>
                  <p className="text-3xl font-bold text-gray-800 mt-2">¥{recommendation.recommended_price.toLocaleString()}</p>
                  {recommendation.rule_applied && (
                    <p className="text-xs font-semibold text-green-600 bg-green-100 inline-block px-2 py-1 rounded mt-2">
                      Rule: {recommendation.rule_applied}
                    </p>
                  )}
                </>
              ) : (
                <p className="text-xl text-gray-500 mt-2">Calculating...</p>
              )}
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-800 mb-4">Pricing Rules</h2>
          <p className="text-gray-600 mb-4">
            Rules are evaluated in order of occupancy threshold. Currently showing active rules for the selected facility.
            (UI for adding/editing rules will be implemented here).
          </p>
          <div className="bg-gray-50 p-4 rounded border">
             <p className="text-sm text-gray-700">✓ If Occupancy &gt;= 80%, increase price by 30%</p>
             <p className="text-sm text-gray-700 mt-2">✓ If Occupancy &gt;= 50%, increase price by 10%</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
