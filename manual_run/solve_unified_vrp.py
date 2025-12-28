import pandas as pd
import networkx as nx
import osmnx as ox
import os
from geopy.distance import geodesic
import math
import warnings
warnings.filterwarnings("ignore")

import zipfile

# --- CONFIGURATION ---
AVG_SPEED_KMPH = 20 
TRAFFIC_MULTIPLIER = 1.4 
SERVICE_TIME_LOAD = 5  
SERVICE_TIME_UNLOAD = 25 
SHIFT_TIME_MINUTES = 480 

def load_data():
    print("Loading Data...")
    df_clusters = pd.read_csv("step1_clusters.csv")
    df_sctp = pd.read_csv("sctp_locations.csv")
    
    # Load Network (Handle Compressed Format)
    graph_path = "hyderabad_network.graphml"
    zip_path = "hyderabad_network.graphml.zip"
    
    if not os.path.exists(graph_path) and os.path.exists(zip_path):
        print(f"📦 Unzipping large road network: {zip_path}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
    
    if os.path.exists(graph_path):
        print(f"Loading Graph from {graph_path}...")
        G = ox.load_graphml(graph_path)
    else:
        print("Error: Graph not found!")
        return None, None, None, None

    # Fleet (Aligned to 'Fleet Details' Sheet - Payload Capacity)
    fleet_list = [
        {'name': 'Mini Tipper 4T', 'payload_kg': 4000, 'count': 66},
        {'name': 'Tipper 8T', 'payload_kg': 8000, 'count': 28},
        {'name': 'Compactor 16T', 'payload_kg': 16000, 'count': 14}
    ]
    
    print(f"Fleet Loaded: {len(fleet_list)} types.")
    return df_clusters, df_sctp, fleet_list, G
