
import pandas as pd
import osmnx as ox
import os
import sys

def load_data(data_dir):
    """
    Loads clusters, SCTPs, and Graph from the specified data directory.
    Returns: df_clusters, df_sctp, fleet_list, G
    """
    print(f"Loading Data from {data_dir}...")
    
    clusters_path = os.path.join(data_dir, "step1_clusters.csv")
    sctp_path = os.path.join(data_dir, "sctp_locations.csv")
    graph_path = os.path.join(data_dir, "hyderabad_network.graphml")
    
    if not os.path.exists(clusters_path) or not os.path.exists(sctp_path):
        raise FileNotFoundError(f"Missing CSV files in {data_dir}")

    df_clusters = pd.read_csv(clusters_path)
    df_sctp = pd.read_csv(sctp_path)
    
    G = None
    if os.path.exists(graph_path):
        print(f"Loading Graph from {graph_path}...")
        G = ox.load_graphml(graph_path)
    else:
        print("Warning: Graph file not found. Distance calculations might rely purely on geodesic.")
        
    # Fleet Definition (Standard)
    fleet_list = [
        {'name': 'Mini Tipper 4T', 'payload_kg': 4000, 'count': 66, 'cost_per_km': 10},
        {'name': 'Mini Tipper 8T', 'payload_kg': 8000, 'count': 28, 'cost_per_km': 18},
        {'name': 'Mini Tipper 16T', 'payload_kg': 16000, 'count': 14, 'cost_per_km': 25}
    ]
    
    return df_clusters, df_sctp, fleet_list, G
