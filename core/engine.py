
import random
import time
import math
import logging
import numpy as np
from .utils import vectorized_haversine_matrix

# --- CONFIGURATION ---
AVG_SPEED_KMPH = 25
TRAFFIC_MULTIPLIER = 1.2
SERVICE_TIME_LOAD = 5
SERVICE_TIME_UNLOAD = 25
SHIFT_TIME_MINUTES = 480 

# GA Parameters
POPULATION_SIZE = 50
MAX_GENERATIONS = 200
ELITISM_COUNT = 5
MUTATION_RATE = 0.1

# SA Parameters
SA_ITERATIONS = 50
INITIAL_TEMP = 100
COOLING_RATE = 0.95

# Callback
PROGRESS_CALLBACK = None

def get_traffic_factor(minutes_from_start):
    if minutes_from_start < 120: return 1.0     # 06:00-08:00
    elif minutes_from_start < 300: return 1.8   # 08:00-11:00
    else: return 1.3                            # 11:00-14:00

def get_best_truck(load, fleet, usage_counts=None, allow_fallback=True):
    # Find smallest valid truck
    valid = []
    for t in fleet:
        if t['payload_kg'] >= load:
            if usage_counts is not None:
                limit = t.get('trips_allowed', 9999)
                if usage_counts.get(t['name'], 0) >= limit:
                    continue 
            valid.append(t)
    
    if valid:
        valid.sort(key=lambda x: x['payload_kg'])
        return valid[0]
    
    if allow_fallback and usage_counts is not None:
        fallback_valid = [t for t in fleet if t['payload_kg'] >= load]
        if fallback_valid:
            fallback_valid.sort(key=lambda x: x['payload_kg'])
            for t in fallback_valid:
                limit = t.get('trips_allowed', 9999)
                if usage_counts.get(t['name'], 0) < limit:
                    return t
    return None

def get_max_available_capacity(usage_counts, fleet, road_limit=16000):
    max_cap = 0
    for t in fleet:
        if t['payload_kg'] > road_limit:
            continue
        limit = t.get('trips_allowed', 9999)
        used = usage_counts.get(t['name'], 0)
        if used < limit:
            max_cap = max(max_cap, t['payload_kg'])
    
    # Always allow 4T logic
    for t in fleet:
        if t['name'] == 'Mini Tipper 4T':
            limit = t.get('trips_allowed', 9999)
            used = usage_counts.get(t['name'], 0)
            if used < limit:
                max_cap = max(max_cap, t['payload_kg'])
                break
    return max_cap if max_cap > 0 else 4000

def calculate_fitness(chromosome, distance_matrix, fleet, gvp_data, depot_idx):
    total_distance = 0
    total_time_minutes = 0
    total_waste_left = 0
    routes = []
    
    usage_counts = {t['name']: 0 for t in fleet}
    
    curr_route_nodes = []
    curr_route_load = 0
    curr_route_dist = 0
    curr_route_time = 0 
    
    curr_route_max_cap = get_max_available_capacity(usage_counts, fleet, 16000)
    last_idx = depot_idx
    
    for gene_idx in chromosome:
        node_id = gvp_data[gene_idx]['id']
        demand = gvp_data[gene_idx]['demand']
        
        dist_km = distance_matrix[last_idx][gene_idx]
        
        base_mins = (dist_km / AVG_SPEED_KMPH) * 60
        tf = get_traffic_factor(curr_route_time)
        travel_mins = base_mins * tf
        
        service_mins = SERVICE_TIME_LOAD
        node_limit = gvp_data[gene_idx].get('max_kg', 16000)
        
        new_route_max = min(curr_route_max_cap, node_limit)
        
        # Predictive check
        pred_total_time = curr_route_time + travel_mins + service_mins + \
                          ((distance_matrix[gene_idx][depot_idx] / AVG_SPEED_KMPH) * 60 * 1.5)
        
        if (curr_route_load + demand > new_route_max) or (pred_total_time > SHIFT_TIME_MINUTES):
            # Close Route
            dist_home = distance_matrix[last_idx][depot_idx]
            base_home = (dist_home / AVG_SPEED_KMPH) * 60
            tf_home = get_traffic_factor(curr_route_time)
            time_home = base_home * tf_home
            
            curr_route_dist += dist_home
            curr_route_time += time_home + SERVICE_TIME_UNLOAD
            
            total_distance += curr_route_dist
            total_time_minutes += curr_route_time
            
            valid_fleet = [t for t in fleet if t['payload_kg'] <= curr_route_max_cap or t['name'] == 'Mini Tipper 4T']
            truck = get_best_truck(curr_route_load, valid_fleet, usage_counts)
            
            if truck:
                usage_counts[truck['name']] += 1
                routes.append({
                    'truck': truck,
                    'load': curr_route_load,
                    'dist': curr_route_dist,
                    'time': curr_route_time,
                    'nodes': curr_route_nodes
                })
            else:
                total_waste_left += curr_route_load
                
            # Start New
            curr_route_nodes = [gene_idx]
            curr_route_load = demand
            curr_route_max_cap = get_max_available_capacity(usage_counts, fleet, node_limit)
            
            dist_depot = distance_matrix[depot_idx][gene_idx]
            base_depot = (dist_depot / AVG_SPEED_KMPH) * 60
            tf_depot = get_traffic_factor(0)
            
            curr_route_dist = dist_depot
            curr_route_time = base_depot * tf_depot + service_mins
            last_idx = gene_idx
        else:
            curr_route_nodes.append(gene_idx)
            curr_route_load += demand
            curr_route_dist += dist_km
            curr_route_time += travel_mins + service_mins
            curr_route_max_cap = new_route_max
            last_idx = gene_idx
            
    # Final Route
    if curr_route_nodes:
        dist_home = distance_matrix[last_idx][depot_idx]
        base_home = (dist_home / AVG_SPEED_KMPH) * 60
        tf_home = get_traffic_factor(curr_route_time)
        time_home = base_home * tf_home
        
        curr_route_dist += dist_home
        curr_route_time += time_home + SERVICE_TIME_UNLOAD
        
        total_distance += curr_route_dist
        total_time_minutes += curr_route_time
        
        valid_fleet = [t for t in fleet if t['payload_kg'] <= curr_route_max_cap or t['name'] == 'Mini Tipper 4T']
        truck = get_best_truck(curr_route_load, valid_fleet, usage_counts)
        
        if truck:
            usage_counts[truck['name']] += 1
            routes.append({
                'truck': truck,
                'load': curr_route_load,
                'dist': curr_route_dist,
                'time': curr_route_time,
                'nodes': curr_route_nodes
            })
        else:
            total_waste_left += curr_route_load

    score = (total_distance * 1.0) + (total_time_minutes * 0.5) + (total_waste_left * 1000)
    return score, routes

def run_sa(chromosome, distance_matrix, fleet, gvp_data, depot_idx, initial_temp, cooling_rate, iterations):
    current_sol = chromosome[:]
    current_cost, _ = calculate_fitness(current_sol, distance_matrix, fleet, gvp_data, depot_idx)
    
    best_sol = current_sol[:]
    best_cost = current_cost
    
    temp = initial_temp
    
    for i in range(iterations):
        neighbor = current_sol[:]
        op = random.random()
        idx1, idx2 = sorted(random.sample(range(len(neighbor)), 2))
        
        if op < 0.33: neighbor[idx1], neighbor[idx2] = neighbor[idx2], neighbor[idx1]
        elif op < 0.66: neighbor[idx1:idx2+1] = neighbor[idx1:idx2+1][::-1]
        else:
            val = neighbor.pop(idx1)
            neighbor.insert(idx2, val)
            
        new_cost, _ = calculate_fitness(neighbor, distance_matrix, fleet, gvp_data, depot_idx)
        
        if new_cost < current_cost or random.random() < math.exp(-(new_cost - current_cost) / temp):
            current_sol = neighbor
            current_cost = new_cost
            if current_cost < best_cost:
                best_sol = current_sol[:]
                best_cost = current_cost
        
        temp *= cooling_rate
        
    return best_sol, best_cost

def run_ga(gvp_data, fleet, distance_matrix, depot_idx):
    print(f"Starting GA for {len(gvp_data)} GVPs...")
    start_time = time.time()
    
    indices = list(range(len(gvp_data)))
    population = [random.sample(indices, len(indices)) for _ in range(POPULATION_SIZE)]
    
    global_best_sol = None
    global_best_score = float('inf')
    
    for gen in range(MAX_GENERATIONS):
        scored_pop = []
        for chrom in population:
            score, _ = calculate_fitness(chrom, distance_matrix, fleet, gvp_data, depot_idx)
            scored_pop.append((score, chrom))
            if score < global_best_score:
                global_best_score = score
                global_best_sol = chrom[:]
        
        scored_pop.sort(key=lambda x: x[0])
        print(f"  > Gen {gen}: Best Score {scored_pop[0][0]:.2f}")
        
        if PROGRESS_CALLBACK:
            PROGRESS_CALLBACK(gen, MAX_GENERATIONS, f"Genetic Loop {gen}")

        elite = scored_pop[0][1]
        refined_elite, refined_score = run_sa(elite, distance_matrix, fleet, gvp_data, depot_idx, INITIAL_TEMP, COOLING_RATE, SA_ITERATIONS)
        
        if refined_score < global_best_score:
            global_best_score = refined_score
            global_best_sol = refined_elite[:]
            
        new_pop = [refined_elite]
        new_pop.extend([x[1] for x in scored_pop[:ELITISM_COUNT-1]])
        
        while len(new_pop) < POPULATION_SIZE:
            p1 = min(random.sample(scored_pop[:20], 3), key=lambda x: x[0])[1]
            p2 = min(random.sample(scored_pop[:20], 3), key=lambda x: x[0])[1]
            
            cut1, cut2 = sorted(random.sample(range(len(p1)), 2))
            child = [-1] * len(p1)
            child[cut1:cut2] = p1[cut1:cut2]
            p2_idx = 0
            for i in range(len(child)):
                if child[i] == -1:
                    while p2[p2_idx] in child: p2_idx += 1
                    child[i] = p2[p2_idx]
            
            if random.random() < MUTATION_RATE:
                i1, i2 = random.sample(range(len(child)), 2)
                child[i1], child[i2] = child[i2], child[i1]
            
            new_pop.append(child)
        population = new_pop

    return global_best_sol

def solve_scenario(df_clusters, fleet, G=None, depot_loc=(17.3850, 78.4867)):
    logging.info("Starting Solver Engine...")
    
    gvp_data = []
    for i, row in df_clusters.iterrows():
        gvp_data.append({
            'id': i,
            'max_kg': row.get('max_kg', 16000),
            'lat': row['lat'],
            'lon': row['lon'],
            'demand': float(row.get('Waste_Tonnes', 0)) * 1000
        })
    
    dist_matrix = vectorized_haversine_matrix(gvp_data, depot_loc)
    depot_idx = len(gvp_data)
    
    best_chrom = run_ga(gvp_data, fleet, dist_matrix, depot_idx)
    fitness, routes = calculate_fitness(best_chrom, dist_matrix, fleet, gvp_data, depot_idx)
    
    features = []
    for i, r in enumerate(routes):
        coords = [[depot_loc[1], depot_loc[0]]]
        for nid in r['nodes']:
            g = gvp_data[nid]
            coords.append([g['lon'], g['lat']])
        coords.append([depot_loc[1], depot_loc[0]])
        
        feature = {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "id": f"Route_{i+1}",
                "type": r['truck']['name'],
                "load": int(r['load']),
                "distance_km": round(r['dist'], 2),
                "duration_min": int(r['time']),
                "co2": round(r['dist'] * 0.5, 2),
                "vehicle_id": f"Truck_{i+1}"
            }
        }
        features.append(feature)
        
    return {
        'routes': {"type": "FeatureCollection", "features": features},
        'metrics': {
            'total_dist': sum(f['properties']['distance_km'] for f in features),
            'total_waste': sum(f['properties']['load'] for f in features),
            'total_routes': len(features)
        }
    }
