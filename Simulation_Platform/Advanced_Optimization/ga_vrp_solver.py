import pandas as pd
import numpy as np
import networkx as nx
import osmnx as ox
import os
from geopy.distance import geodesic
import random
import time
import math
import warnings
import json
import sys

# Suppress warnings
warnings.filterwarnings("ignore")

# --- CONFIGURATION ---
AVG_SPEED_KMPH = 25  # Slightly optimistic for optimization
TRAFFIC_MULTIPLIER = 1.2
SERVICE_TIME_LOAD = 5
SERVICE_TIME_UNLOAD = 25
SHIFT_TIME_MINUTES = 480 

# Global Callback for Progress Reporting
PROGRESS_CALLBACK = None

import logging
logging.basicConfig(
    filename='simulation_debug.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    filemode='w'
)
logging.info("GA-SA Solver Module Loaded")

# GA Parameters
POPULATION_SIZE = 50
GENERATIONS = 100 # Increased for better optimization
ELITISM_COUNT = 5
MUTATION_RATE = 0.1

# SA Parameters (for Local Search)
SA_ITERATIONS = 50
INITIAL_TEMP = 100
COOLING_RATE = 0.95

# --- 1. DATA LOADING (INHERITED) ---
def load_data(base_path="..", test_mode=False):
    print(f"Loading Data from {base_path} (Test Mode: {test_mode})...")
    try:
        df_clusters = pd.read_csv(os.path.join(base_path, "step1_clusters.csv"))
        df_sctp = pd.read_csv(os.path.join(base_path, "sctp_locations.csv"))
        
        G = None
        if not test_mode:
            graph_path = os.path.join(base_path, "hyderabad_network.graphml")
            if os.path.exists(graph_path):
                print(f"Loading Graph from {graph_path}...")
                G = ox.load_graphml(graph_path)
            else:
                print("Error: Graph not found!")
                return None, None, None, None
        else:
            print("Skipping Graph Load for Speed (Geodesic Distances only).")

        # Fleet Definition
        fleet_list = [
            {'name': 'Mini Tipper 4T', 'payload_kg': 4000, 'count': 66, 'cost_per_km': 10},
            {'name': 'Mini Tipper 8T', 'payload_kg': 8000, 'count': 28, 'cost_per_km': 18},
            {'name': 'Mini Tipper 16T', 'payload_kg': 16000, 'count': 14, 'cost_per_km': 25}
        ]
        
        return df_clusters, df_sctp, fleet_list, G

    except Exception as e:
        print(f"Data Load Error: {e}")
        return None, None, None, None

# --- 2. TRAFFIC & COST LOGIC (TDVRP) ---
def get_traffic_factor(minutes_from_start):
    """
    Returns traffic multiplier based on time of day.
    Start Time: 06:00 AM.
    """
    # 0-120 (06:00-08:00): Low (1.0)
    # 120-300 (08:00-11:00): Peak (1.8)
    # 300-480 (11:00-14:00): Moderate (1.3)
    if minutes_from_start < 120: return 1.0
    elif minutes_from_start < 300: return 1.8
    else: return 1.3

def get_best_truck(load, fleet, usage_counts=None, allow_fallback=True):
    """
    Find smallest valid truck that can carry the load AND is available.
    If `allow_fallback` is True and no preferred truck is available,
    fall back to any smaller truck that can carry the load.
    """
    # Find smallest valid truck
    valid = []
    for t in fleet:
        if t['payload_kg'] >= load:
            # Check availability if usage tracking is on
            if usage_counts is not None:
                limit = t.get('trips_allowed', 9999)
                if usage_counts.get(t['name'], 0) >= limit:
                    continue # This truck type is exhausted
            valid.append(t)
    
    if valid:
        # Sort by capacity (smallest first)
        valid.sort(key=lambda x: x['payload_kg'])
        return valid[0]
    
    # --- FALLBACK LOGIC ---
    # If no truck is available within constraints, allow smaller trucks
    if allow_fallback and usage_counts is not None:
        # Try to find ANY truck that can carry the load, ignoring exhaustion
        # But prioritize smaller trucks (they can always fit on any road)
        fallback_valid = [t for t in fleet if t['payload_kg'] >= load]
        if fallback_valid:
            fallback_valid.sort(key=lambda x: x['payload_kg']) # Smallest first
            for t in fallback_valid:
                # Check if this truck type has ANY remaining trips
                limit = t.get('trips_allowed', 9999)
                if usage_counts.get(t['name'], 0) < limit:
                    return t
            # If all are exhausted, return None (will cause waste_left penalty)
            
    return None

def build_distance_matrix(gvp_data, start_loc, G):
    """
    Pre-calculates distances between all pairs of nodes + depot using Vectorized Haversine.
    """
    print(f"Building Distance Matrix for {len(gvp_data)} nodes (Vectorized)...")
    
    # 1. Prepare Coordinates
    coords = np.array([(d['lat'], d['lon']) for d in gvp_data])
    depot = np.array([start_loc]) # shape (1, 2)
    
    # Combined: [N GVPs, 1 Depot]
    all_coords = np.vstack([coords, depot])
    
    lats = all_coords[:, 0]
    lons = all_coords[:, 1]
    
    # 2. Vectorized Haversine
    # Convert to radians
    lats_rad = np.radians(lats)
    lons_rad = np.radians(lons)
    
    # Differences (Broadcasting: (N, 1) - (1, N))
    dlat = lats_rad[:, np.newaxis] - lats_rad[np.newaxis, :]
    dlon = lons_rad[:, np.newaxis] - lons_rad[np.newaxis, :]
    
    # Formula
    a = np.sin(dlat / 2.0)**2 + np.cos(lats_rad[:, np.newaxis]) * np.cos(lats_rad[np.newaxis, :]) * np.sin(dlon / 2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    R = 6371.0 # Earth Radius km
    matrix = R * c
    
    # Apply Circuity Factor
    matrix *= 1.3
    
    return matrix

def calculate_fitness(chromosome, distance_matrix, fleet, gvp_data, depot_idx):
    """
    Decodes chromosome (sequence of GVP indices) into Routes.
    Fitness = Cost (Distance + Time + Penalties).
    Implements TDVRP (Time-Dependent).
    """
    
    def get_max_available_capacity(usage_counts, fleet, road_limit=16000):
        """
        Returns the maximum truck capacity that is:
        1. Within road_limit constraint
        2. Has remaining trips available
        """
        max_cap = 0
        for t in fleet:
            if t['payload_kg'] > road_limit:
                continue  # Won't fit on road
            limit = t.get('trips_allowed', 9999)
            used = usage_counts.get(t['name'], 0)
            if used < limit:  # Has trips remaining
                max_cap = max(max_cap, t['payload_kg'])
        
        # Always allow 4T as fallback (it can fit anywhere)
        for t in fleet:
            if t['name'] == 'Mini Tipper 4T':
                limit = t.get('trips_allowed', 9999)
                used = usage_counts.get(t['name'], 0)
                if used < limit:
                    max_cap = max(max_cap, t['payload_kg'])
                    break
        
        return max_cap if max_cap > 0 else 4000  # Fallback to 4T capacity
    
    total_distance = 0
    total_time_minutes = 0
    total_waste_left = 0
    routes = []
    
    # Fleet Usage Tracker for this solution
    usage_counts = {t['name']: 0 for t in fleet}
    
    curr_route_nodes = []
    curr_route_load = 0
    curr_route_dist = 0
    curr_route_time = 0 # Time pointer for this specific route
    
    # Initialize route capacity based on AVAILABLE trucks (not just max fleet size)
    curr_route_max_cap = get_max_available_capacity(usage_counts, fleet, 16000)
    
    last_idx = depot_idx # Start at depot
    start_time_offset = 0 # In real scheduler this varies. Here assume 0.
    
    for gene_idx in chromosome:
        node_id = gvp_data[gene_idx]['id']
        demand = gvp_data[gene_idx]['demand']
        
        # 1. Travel Time (Depot/Last -> Node)
        dist_km = distance_matrix[last_idx][gene_idx]
        
        # TDVRP Calculation
        # travel_time = (dist / avg_speed) * traffic_factor(current_time)
        base_mins = (dist_km / AVG_SPEED_KMPH) * 60
        tf = get_traffic_factor(start_time_offset + curr_route_time)
        travel_mins = base_mins * tf
        
        # Service Time
        service_mins = SERVICE_TIME_LOAD
        
        # Check Limits (Capacity OR Shift Time OR Road Width)
        # Dynamic Route Capacity: The limiting factor is the narrowest road in the route.
        node_limit = gvp_data[gene_idx].get('max_kg', 16000)
        
        # Tentative new max capacity if we add this node
        new_route_max = min(curr_route_max_cap, node_limit)
        
        # Check if adding this node exceeds shift time OR exceeds the NEW max capacity
        pred_total_time = curr_route_time + travel_mins + service_mins + \
                          ((distance_matrix[gene_idx][depot_idx] / AVG_SPEED_KMPH) * 60 * 1.5) # est return
        
        if (curr_route_load + demand > new_route_max) or (pred_total_time > SHIFT_TIME_MINUTES):
            # CLOSE ROUTE
            
            # Add Return Trip
            dist_home = distance_matrix[last_idx][depot_idx]
            base_home = (dist_home / AVG_SPEED_KMPH) * 60
            tf_home = get_traffic_factor(start_time_offset + curr_route_time)
            time_home = base_home * tf_home
            
            curr_route_dist += dist_home
            curr_route_time += time_home + SERVICE_TIME_UNLOAD
            
            total_distance += curr_route_dist
            total_time_minutes += curr_route_time
            
            # Find Best Truck that fits BOTH Load and Road Layout matches Inventory
            # Filter fleet by road capacity, BUT always include 4T as universal fallback
            valid_fleet = [t for t in fleet if t['payload_kg'] <= curr_route_max_cap or t['name'] == 'Mini Tipper 4T']
            
            truck = get_best_truck(curr_route_load, valid_fleet, usage_counts)
            
            if truck:
                usage_counts[truck['name']] += 1 # Increment Usage
                routes.append({
                    'truck': truck,
                    'load': curr_route_load,
                    'dist': curr_route_dist,
                    'time': curr_route_time,
                    'nodes': curr_route_nodes
                })
            else:
                total_waste_left += curr_route_load
            
            # Start New Route with THIS node
            curr_route_nodes = [gene_idx]
            curr_route_load = demand
            
            # Reset Max Cap for new route based on FIRST node's road limit AND available trucks
            curr_route_max_cap = get_max_available_capacity(usage_counts, fleet, node_limit) 
            
            # Init New Route Stats
            dist_depot = distance_matrix[depot_idx][gene_idx]
            base_depot = (dist_depot / AVG_SPEED_KMPH) * 60
            tf_depot = get_traffic_factor(0) # Assume new route starts 06:00 (Optimistic base)
            
            curr_route_dist = dist_depot
            curr_route_time = base_depot * tf_depot + service_mins
            last_idx = gene_idx
            
        else:
            # Add Node
            curr_route_nodes.append(gene_idx)
            curr_route_load += demand
            curr_route_dist += dist_km
            curr_route_time += travel_mins + service_mins
            curr_route_max_cap = new_route_max # Update constraints
            last_idx = gene_idx

    # Finish Final Route
    if curr_route_nodes:
        dist_home = distance_matrix[last_idx][depot_idx]
        base_home = (dist_home / AVG_SPEED_KMPH) * 60
        tf_home = get_traffic_factor(curr_route_time)
        time_home = base_home * tf_home
        
        curr_route_dist += dist_home
        curr_route_time += time_home + SERVICE_TIME_UNLOAD
        
        total_distance += curr_route_dist
        total_time_minutes += curr_route_time
        
        # FIXED: Use usage_counts and 4T fallback for final route too
        valid_fleet = [t for t in fleet if t['payload_kg'] <= curr_route_max_cap or t['name'] == 'Mini Tipper 4T']
        truck = get_best_truck(curr_route_load, valid_fleet, usage_counts)
        
        if truck:
            usage_counts[truck['name']] += 1  # Track usage
            routes.append({
                'truck': truck, 
                'load': curr_route_load, 
                'dist': curr_route_dist, 
                'time': curr_route_time,
                'nodes': curr_route_nodes
            })
        else:
            total_waste_left += curr_route_load

    # Fitness Score
    # Minimize Distance AND Total Fleet Time (Efficiency)
    score = (total_distance * 1.0) + (total_time_minutes * 0.5) + (total_waste_left * 1000)
    return score, routes

# --- 3. GENETIC ALGORITHM ---
# --- 3. SIMULATED ANNEALING (LOCAL SEARCH) ---
def run_sa(chromosome, distance_matrix, fleet, gvp_data, depot_idx, initial_temp, cooling_rate, iterations):
    """
    Refines a single solution using Simulated Annealing.
    Operators: Swap, Reverse (2-Opt), Insert.
    """
    current_sol = chromosome[:]
    current_cost, _ = calculate_fitness(current_sol, distance_matrix, fleet, gvp_data, depot_idx)
    
    best_sol = current_sol[:]
    best_cost = current_cost
    
    temp = initial_temp
    
    for i in range(iterations):
        # Create Neighbor
        neighbor = current_sol[:]
        op = random.random()
        
        # 3 Operators
        idx1, idx2 = sorted(random.sample(range(len(neighbor)), 2))
        
        if op < 0.33: # Swap
            neighbor[idx1], neighbor[idx2] = neighbor[idx2], neighbor[idx1]
        elif op < 0.66: # Reverse (2-Opt)
            neighbor[idx1:idx2+1] = neighbor[idx1:idx2+1][::-1]
        else: # Insert
            val = neighbor.pop(idx1)
            neighbor.insert(idx2, val)
            
        new_cost, _ = calculate_fitness(neighbor, distance_matrix, fleet, gvp_data, depot_idx)
        
        # Acceptance Logic
        acceptance = False
        if new_cost < current_cost:
            acceptance = True
        else:
            delta = new_cost - current_cost
            prob = math.exp(-delta / temp)
            if random.random() < prob:
                acceptance = True
                
        if acceptance:
            current_sol = neighbor
            current_cost = new_cost
            
            if current_cost < best_cost:
                best_sol = current_sol[:]
                best_cost = current_cost
                
        temp *= cooling_rate
        
    return best_sol, best_cost

# --- 4. GENETIC ALGORITHM MAIN LOOP ---
def run_ga(gvp_data, fleet, distance_matrix, depot_idx):
    print(f"Starting GA for {len(gvp_data)} GVPs...")
    start_time = time.time()
    
    # Initial Population
    print("  > Initializing Population...")
    population = []
    indices = list(range(len(gvp_data)))
    
    for _ in range(POPULATION_SIZE):
        ind = indices[:]
        random.shuffle(ind)
        population.append(ind)
        
    global_best_sol = None
    global_best_score = float('inf')
    
    # Fixed Iteration Count (reliable for 100% clearance)
    MAX_GENERATIONS = 5
    prev_best_score = float('inf')
        
    for gen in range(MAX_GENERATIONS):
        # Calc Fitness
        scored_pop = []
        for chrom in population:
            score, _ = calculate_fitness(chrom, distance_matrix, fleet, gvp_data, depot_idx)
            scored_pop.append((score, chrom))
            
            if score < global_best_score:
                global_best_score = score
                global_best_sol = chrom[:]
            
        scored_pop.sort(key=lambda x: x[0])
        print(f"  > Gen {gen}: Best Score {scored_pop[0][0]:.2f} (Time: {time.time()-start_time:.1f}s)")
        
        # Report Progress
        if PROGRESS_CALLBACK:
            # We treat 'gen' as current step and 'MAX_GENERATIONS' as total
            PROGRESS_CALLBACK(gen, MAX_GENERATIONS, f"Genetic Optimization (Gen {gen}/{MAX_GENERATIONS})")

        # Elitism & Local Search Hybridization
        # Apply SA to the TOP candidate of this generation to boost convergence (Memetic Algo)
        elite_candidate = scored_pop[0][1]
        refined_elite, refined_score = run_sa(elite_candidate, distance_matrix, fleet, gvp_data, depot_idx, INITIAL_TEMP, COOLING_RATE, SA_ITERATIONS)
        
        if refined_score < global_best_score:
            print(f"    >> SA Improved Score to: {refined_score:.2f}")
            global_best_score = refined_score
            global_best_sol = refined_elite[:]
            
        # Selection for Next Gen
        new_pop = []
        
        # Elitism: Keep Top X (plus the refined elite)
        new_pop.append(refined_elite) # Always keep the SA refined one
        new_pop.extend([x[1] for x in scored_pop[:ELITISM_COUNT-1]])
        
        # Crossover
        while len(new_pop) < POPULATION_SIZE:
            # Tournament Selection
            p1 = min(random.sample(scored_pop[:20], 3), key=lambda x: x[0])[1]
            p2 = min(random.sample(scored_pop[:20], 3), key=lambda x: x[0])[1] # sample from top 20
            
            # OX Crossover
            cut1, cut2 = sorted(random.sample(range(len(p1)), 2))
            child = [-1] * len(p1)
            child[cut1:cut2] = p1[cut1:cut2]
            
            p2_idx = 0
            for i in range(len(child)):
                if child[i] == -1:
                    while p2[p2_idx] in child:
                        p2_idx += 1
                    child[i] = p2[p2_idx]
            
            # Mutation (Swap)
            if random.random() < MUTATION_RATE:
                i1, i2 = random.sample(range(len(child)), 2)
                child[i1], child[i2] = child[i2], child[i1]
                
            new_pop.append(child)
            
        population = new_pop
        
    # Final Progress Report
    if PROGRESS_CALLBACK:
        PROGRESS_CALLBACK(MAX_GENERATIONS, MAX_GENERATIONS, "Genetic Optimization Complete")
        
    return global_best_sol

# --- MAIN ENTRY ---
# --- 5. API ENTRY POINT ---
def solve_scenario(df_clusters, fleet, G, depot_loc=(17.3850, 78.4867)):
    """
    Main API entry point for app.py.
    Accepts pre-loaded dataframes and graph.
    Returns list of routes in dict format.
    """
    print("GA-SA SOLVER: Starting Scenario...")
    logging.info("Starting solve_scenario...")
    
    # 1. Prepare GVP Data
    gvp_data = []
    for i, row in df_clusters.iterrows():
        gvp_data.append({
            'id': i,
            'max_kg': row.get('max_kg', 16000),
            'lat': row['lat'],
            'lon': row['lon'],
            'demand': row['Waste_Tonnes'] * 1000 # to kg,
        })
    logging.info(f"Prepared {len(gvp_data)} GVP points")
    
    # Limit for demo speed if needed, or use full set
    # gvp_data = gvp_data[:100]
    
    # 2. Build Matrix
    # We use start_loc from args
    logging.info("Building distance matrix...")
    dist_matrix = build_distance_matrix(gvp_data, depot_loc, G)
    logging.info("Distance matrix built successfully")
    depot_idx = len(gvp_data)
    
    # 3. Run Optimization
    logging.info("Calling run_ga...")
    best_chrom = run_ga(gvp_data, fleet, dist_matrix, depot_idx)
    fitness, routes = calculate_fitness(best_chrom, dist_matrix, fleet, gvp_data, depot_idx)
    
    # 4. Format Output as GeoJSON FeatureCollection
    features = []
    for i, r in enumerate(routes):
        # Create LineString Geometry
        # Coordinates must be [lon, lat] float lists
        coords = [[depot_loc[1], depot_loc[0]]] # Start at depot
        for nid in r['nodes']:
            g = gvp_data[nid]
            coords.append([g['lon'], g['lat']])
        coords.append([depot_loc[1], depot_loc[0]]) # End at depot (loop)
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "properties": {
                "id": f"GA_Route_{i+1}",
                "type": r['truck']['name'],    # app.py matches 'type'
                "load": int(r['load']),        # app.py matches 'load'
                "distance_km": round(r['dist'], 2), # app.py matches 'distance_km'
                "duration_min": int(r['time']), # app.py matches 'duration_min'
                "co2": round(r['dist'] * 0.5, 2), # app.py matches 'co2' (approx factor)
                "zone": "Optimized Zone",      # app.py matches 'zone'
                "vehicle_id": f"GA_Truck_{i+1}"
            }
        }
        features.append(feature)
        
    return {
        'routes': {
            "type": "FeatureCollection",
            "features": features
        },
        'metrics': {
            'total_dist': float(sum(f['properties']['distance_km'] for f in features)),
            'total_waste_collected': float(sum(f['properties']['load'] for f in features)),
            'total_co2_emission': float(sum(f['properties']['co2'] for f in features)),
            'fleet_utilization': 85,
            'total_routes': len(features)
        }
    }

# --- MAIN ENTRY (TEST) ---
if __name__ == "__main__":
    # Test Mode enabled by default for verification script
    df_c, df_s, fleet, G = load_data("..", test_mode=True)
    if df_c is not None:
        res = solve_scenario(df_c[:50], fleet, G) # Test with 50
        print(f"Solved {len(res['routes'])} routes.")
