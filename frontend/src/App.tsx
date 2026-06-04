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
  recommended_price_rule_based: number;
  rule_applied: string | null;
  recommended_price_ml_based: number | null;
}

interface OccupancyData {
  facility_id: number;
  date: string;
  booked_rooms: number;
}

interface Rule {
  id: number;
  facility_id: number;
  occupancy_threshold_percent: number;
  price_multiplier: number;
  active: boolean;
}

function App() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacility, setSelectedFacility] = useState<number | null>(null);

  // New state for Date Selection
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);

  const [recommendation, setRecommendation] = useState<PriceRecommendation | null>(null);
  const [occupancy, setOccupancy] = useState<OccupancyData | null>(null);
  const [rules, setRules] = useState<Rule[]>([]);

  useEffect(() => {
    fetchFacilities();
  }, []);

  useEffect(() => {
    if (selectedFacility && selectedDate) {
      fetchDashboardData(selectedFacility, selectedDate);
      fetchRules(selectedFacility);
    }
  }, [selectedFacility, selectedDate]);

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

  const fetchRules = async (facilityId: number) => {
    try {
      const response = await axios.get(`http://localhost:8000/rules?facility_id=${facilityId}`);
      setRules(response.data);
    } catch (error) {
      console.error("Error fetching rules:", error);
    }
  };

  const fetchDashboardData = async (facilityId: number, date: string) => {
    try {
      setRecommendation(null); // Optional: loading state
      const occResponse = await axios.get(`http://localhost:8000/occupancy?facility_id=${facilityId}&date=${date}`);
      const dayOcc = occResponse.data.find((o: any) => o.date === date);
      setOccupancy(dayOcc || null);

      const recResponse = await axios.get(`http://localhost:8000/recommendations/${facilityId}/${date}`);
      setRecommendation(recResponse.data);
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
      setRecommendation(null);
      setOccupancy(null);
    }
  };

  const toggleRule = async (ruleId: number) => {
    try {
      await axios.put(`http://localhost:8000/rules/${ruleId}/toggle`);
      if (selectedFacility && selectedDate) {
        fetchRules(selectedFacility);
        fetchDashboardData(selectedFacility, selectedDate); // Recalculate recommendation
      }
    } catch (error) {
       console.error("Error toggling rule:", error);
    }
  }

  const selectedFacilityData = facilities.find(f => f.id === selectedFacility);

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-5xl mx-auto">
        <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center space-y-4 md:space-y-0">
          <h1 className="text-3xl font-bold text-gray-800">Revenue Control Dashboard</h1>
          <div className="flex space-x-4">
             <input
              type="date"
              className="p-2 border rounded shadow-sm focus:ring focus:ring-blue-200"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
            />
            <select
              className="p-2 border rounded shadow-sm focus:ring focus:ring-blue-200"
              value={selectedFacility || ''}
              onChange={(e) => setSelectedFacility(Number(e.target.value))}
            >
              {facilities.map(f => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          </div>
        </header>

        {selectedFacilityData && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-sm font-semibold text-gray-500 uppercase">Base Price</h2>
              <p className="text-3xl font-bold text-gray-800 mt-2">¥{selectedFacilityData.base_price.toLocaleString()}</p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-sm font-semibold text-gray-500 uppercase">Occupancy ({selectedDate})</h2>
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

            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500 transition-all duration-300">
              <h2 className="text-sm font-semibold text-blue-500 uppercase">Rule-based Price</h2>
              {recommendation ? (
                <>
                  <p className="text-3xl font-bold text-gray-800 mt-2">¥{recommendation.recommended_price_rule_based.toLocaleString()}</p>
                  {recommendation.rule_applied ? (
                    <p className="text-xs font-semibold text-blue-600 bg-blue-100 inline-block px-2 py-1 rounded mt-2">
                      Rule: {recommendation.rule_applied}
                    </p>
                  ) : (
                    <p className="text-xs font-semibold text-gray-500 mt-2">
                      No active rules applied
                    </p>
                  )}
                </>
              ) : (
                <p className="text-xl text-gray-500 mt-2">Calculating...</p>
              )}
            </div>

            <div className="bg-gradient-to-br from-purple-50 to-white rounded-lg shadow p-6 border-l-4 border-purple-500 relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-purple-500 text-white text-xs px-2 py-1 rounded-bl-lg font-bold">AI Prediction</div>
              <h2 className="text-sm font-semibold text-purple-600 uppercase">ML Predicted Price</h2>
              {recommendation?.recommended_price_ml_based ? (
                <>
                  <p className="text-3xl font-bold text-gray-800 mt-2">¥{recommendation.recommended_price_ml_based.toLocaleString()}</p>
                  <p className="text-xs text-gray-500 mt-2 leading-tight">
                    Predicted using Random Forest trained on 1-year historical data.
                  </p>
                </>
              ) : (
                <p className="text-xl text-gray-500 mt-2">Training model...</p>
              )}
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-800 mb-4">Pricing Rules Configuration</h2>
          <p className="text-gray-600 mb-4 text-sm">
            Rules are evaluated in descending order of occupancy threshold. Toggle a rule to see its effect instantly on the dashboard above.
          </p>
          <div className="space-y-3">
             {rules.length > 0 ? rules.map(rule => (
                <div key={rule.id} className="flex items-center justify-between bg-gray-50 p-4 rounded border">
                    <div>
                      <p className={`font-medium ${rule.active ? 'text-gray-800' : 'text-gray-400'}`}>
                        If Occupancy &gt;= {rule.occupancy_threshold_percent * 100}%, multiply price by {rule.price_multiplier}
                      </p>
                    </div>
                    <button
                      onClick={() => toggleRule(rule.id)}
                      className={`px-4 py-2 rounded font-semibold text-sm transition-colors ${
                        rule.active
                          ? 'bg-green-100 text-green-700 hover:bg-green-200'
                          : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                      }`}
                    >
                      {rule.active ? 'Active' : 'Inactive'}
                    </button>
                </div>
             )) : (
               <p className="text-gray-500">No rules configured for this facility.</p>
             )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
