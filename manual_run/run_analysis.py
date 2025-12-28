import pandas as pd
import sys
import os
import osmnx as ox
import json
from datetime import datetime

# 1. SETUP ENVIRONMENT
# Ensure the local Advanced_Optimization package is findable
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
try:
    from Advanced_Optimization import ga_vrp_solver as ga_solver
except ImportError:
    print("Error: Could not find Advanced_Optimization.ga_vrp_solver.")
    sys.exit(1)

import solve_unified_vrp as data_loader

def main():
    print("\n" + "="*70)
    print("   TEAM ROUTEMIND | HYDERABAD SWM OPTIMIZATION ENGINE v2.0")
    print("   Advanced Hybrid GA-SA Solver (Production Algorithm)")
    print("="*70 + "\n")
    
    # 2. LOAD DATA
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📂 Loading Geospatial Datasets...")
    df_clusters, df_sctp, fleet_base, G = data_loader.load_data()
    
    if G is None:
        print("❌ Error: Could not load road network graph (hyderabad_network.graphml).")
        return

    # 3. ROAD CONSTRAINTS (HYBRID HIERARCHY)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🗺️  Calculating Road Constraints...")
    all_lats = df_clusters['lat'].tolist()
    all_lons = df_clusters['lon'].tolist()
    nearest_nodes = ox.distance.nearest_nodes(G, all_lons, all_lats)
    
    gvp_limits = {}
    TIER_1_ARTERIAL = ['trunk', 'primary', 'secondary', 'tertiary', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link']
    TIER_3_NARROW = ['living_street', 'service', 'track', 'path', 'pedestrian', 'private', 'alley']
    
    for i, (idx, row) in enumerate(df_clusters.iterrows()):
        node_id = nearest_nodes[i]
        max_kg = 8000 # Default
        edges = list(G.edges(node_id, data=True))
        
        if not edges:
            max_kg = 4000
        else:
            is_tier_1 = any(data.get('highway') in TIER_1_ARTERIAL for _, _, data in edges)
            is_tier_3 = all(data.get('highway') in TIER_3_NARROW for _, _, data in edges)
            
            if is_tier_1:
                max_kg = 16000
            elif is_tier_3:
                max_kg = 4000
            else:
                # Neighborhood check for shallow arterial access
                is_shallow = False
                for n in G.neighbors(node_id):
                    if any(d.get('highway') in TIER_1_ARTERIAL for _, _, d in G.edges(n, data=True)):
                        is_shallow = True
                        break
                max_kg = 16000 if is_shallow else 8000
        
        gvp_limits[row['GVP_ID']] = max_kg

    # 4. OPTIMIZATION LOOP
    all_routes_data = []
    zones = df_clusters['Assigned_SCTP_ID'].unique()
    total_waste_global = df_clusters['Waste_Tonnes'].sum()
    
    # Trip Limits for Fleet Sustainability
    trip_limits = {t['name']: (t['count'] * 2 if t['name'] != 'Mini Tipper 4T' else 9999) for t in fleet_base}

    print(f"\n🚀 Running Optimization for {len(zones)} Logistics Zones...\n")

    for z_id in zones:
        sctp_row = df_sctp[df_sctp['SCTP_ID'] == z_id].iloc[0]
        zone_gvps = df_clusters[df_clusters['Assigned_SCTP_ID'] == z_id].copy()
        zone_gvps['max_kg'] = zone_gvps['GVP_ID'].map(gvp_limits)
        
        share = zone_gvps['Waste_Tonnes'].sum() / total_waste_global
        dynamic_fleet = [{**t, 'trips_allowed': (max(1, round(trip_limits[t['name']] * share)) if t['name'] != 'Mini Tipper 4T' else 9999)} for t in fleet_base]
        
        print(f"  > Processing: {sctp_row['SCTP_Name'].ljust(20)} | GVPs: {len(zone_gvps):3}")
        
        try:
            result = ga_solver.solve_scenario(zone_gvps, dynamic_fleet, G, depot_loc=(sctp_row['lat'], sctp_row['lon']))
            routes = result['routes']['features']
            
            for i, r in enumerate(routes):
                props = r['properties']
                all_routes_data.append({
                    'SCTP_Name': sctp_row['SCTP_Name'],
                    'VehicleID': f"TRK_{z_id}_{i+1}",
                    'Truck_Type': props['type'],
                    'Payload_Capacity_T': 16.0 if '16T' in props['type'] else (8.0 if '8T' in props['type'] else 4.0),
                    'Load_kg': props['load'],
                    'Utilization_%': round((props['load'] / (16000 if '16T' in props['type'] else (8000 if '8T' in props['type'] else 4000))) * 100, 1),
                    'Dist_km': props['distance_km'],
                    'Duration_mins': props['duration_min'],
                    'CO2_kg': props['co2']
                })
        except Exception as e:
            print(f"    ⚠️ Warning in Zone {z_id}: {e}")

    # 5. GENERATE REPORTS
    print("\n" + "-"*70)
    print(f"✅ ANALYSIS COMPLETE")
    print(f"   Total Distance:    {sum(r['Dist_km'] for r in all_routes_data):,.2f} km")
    print(f"   Total Waste:        {sum(r['Load_kg'] for r in all_routes_data)/1000:,.1f} Tonnes")
    print(f"   Fleet Efficiency:   {sum(r['Utilization_%'] for r in all_routes_data)/len(all_routes_data):.1f}% Avg Util")
    print("-" * 70)

    # Export to Excel (Detailed Analysis)
    df_out = pd.DataFrame(all_routes_data)
    excel_path = "detailed_project_analysis.xlsx"
    df_out.to_excel(excel_path, index=False)
    
    # Export to JSON (Technical Results)
    json_path = "analysis_results.json"
    with open(json_path, "w") as f:
        json.dump({"summary": {"total_dist": sum(r['Dist_km'] for r in all_routes_data), "total_waste": sum(r['Load_kg'] for r in all_routes_data)}, "routes": all_routes_data}, f, indent=4)

    print(f"\n[SUCCESS] Reports generated:")
    print(f"  - {excel_path} (For Presentation/Verification)")
    print(f"  - {json_path} (For Technical Review)")
    print("\nSimulation Finished.")

if __name__ == "__main__":
    main()
