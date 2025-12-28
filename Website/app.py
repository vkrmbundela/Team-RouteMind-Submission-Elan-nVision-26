
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sys
import os
import threading

# Add parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import data, engine

app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app)

# Load Data Global
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
try:
    print("Loading Data...")
    DF_CLUSTERS, DF_SCTP, FLEET, G = data.load_data(DATA_DIR)
    print("Data Loaded Successfully.")
except Exception as e:
    print(f"Error Loading Data: {e}")
    DF_CLUSTERS, DF_SCTP, FLEET, G = None, None, None, None

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/simulate', methods=['POST'])
def simulate():
    if DF_CLUSTERS is None:
        return jsonify({"error": "Server Data not loaded"}), 500
        
    config = request.json or {}
    print(f"Running Simulation Request: {config}")
    
    # Gather Results
    all_features = []
    
    zones = DF_CLUSTERS['Assigned_SCTP_ID'].unique()
    
    total_dist = 0
    total_load = 0
    total_co2 = 0
    
    for z in zones:
        sctp_info = DF_SCTP[DF_SCTP['SCTP_ID'] == z].iloc[0]
        zone_clusters = DF_CLUSTERS[DF_CLUSTERS['Assigned_SCTP_ID'] == z]
        depot_loc = (sctp_info['lat'], sctp_info['lon'])
        
        result = engine.solve_scenario(zone_clusters, FLEET, G, depot_loc)
        
        # Merge properties
        for f in result['routes']['features']:
            f['properties']['zone'] = sctp_info['SCTP_Name']
            all_features.append(f)
            
        total_dist += result['metrics']['total_dist']
        total_load += result['metrics']['total_waste']
        total_co2 += result['metrics']['total_co2']
            
    response = {
        "routes": {
            "type": "FeatureCollection",
            "features": all_features
        },
        "metrics": {
            "total_dist": round(total_dist, 2),
            "total_waste": round(total_load, 1),
            "total_co2": round(total_co2, 2),
            "total_routes": len(all_features)
        }
    }
    
    return jsonify(response)

@app.route('/api/data/static', methods=['GET'])
def get_static_data():
    # Return GVPs and SCTPs as GeoJSONs for map
    if DF_CLUSTERS is None: return jsonify({})
    
    gvps = []
    for _, row in DF_CLUSTERS.iterrows():
        gvps.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row['lon'], row['lat']]},
            "properties": {"waste": row['Waste_Tonnes']}
        })
        
    sctps = []
    if DF_SCTP is not None:
        for _, row in DF_SCTP.iterrows():
            sctps.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row['lon'], row['lat']]},
                "properties": {"name": row['SCTP_Name']}
            })
            
    return jsonify({
        "gvps": {"type": "FeatureCollection", "features": gvps},
        "sctps": {"type": "FeatureCollection", "features": sctps}
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)
