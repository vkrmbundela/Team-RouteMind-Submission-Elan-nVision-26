## Folder Structure
- `/Website`: Interactive Infographic Website & Live Simulation.
- `/manual_run`: Terminal-based analysis engine (Python).
- `/QGIS_Visualization`: Raw geospatial project files and GIS datasets.
- `/core` & `/data`: Technical simulation engine and routing source data.

## 1. How to View the Infographic
1. Open the `/Website` folder.
2. Double-click `index.html` to open it in your web browser.
3. Requires an active internet connection for Map Tiles and MathJax.

## 2. Technical Analysis Run (Terminal)
For judges who wish to verify the underlying optimization math using our production-grade Hybrid GA-SA algorithm, follow these detailed steps:

### Prerequisites
- Python 3.8+ installed.
- Internet connection (required for initial road network parsing via OSMnx).

### Execution Steps
1. **Navigate to the Folder**: Open your terminal or Command Prompt in the `/manual_run` directory.
2. **Install Dependencies**: 
   ```bash
   pip install -r requirements.txt
   ```
   *Note: This installs `osmnx` for geospatial analysis and `openpyxl` for Excel generation.*
3. **Run the Solver**:
   ```bash
   python run_analysis.py
   ```
   *Note: On first run, the system will automatically extract the compressed `hyderabad_network.graphml.zip` file (276MB original) to restore the full road network. This process takes ~10 seconds.*
4. **What to Observe**:
   - **Data Audit**: The system snaps 1,583 points to the Hyderabad road network and determines road-width constraints.
   - **Optimization**: You will see real-time "Generation" logs. Our Hybrid algorithm uses Genetic selection for global routing and Simulated Annealing for local route refinements.
   - **Telemetry**: Real-time fitness scores (total distance) will decrease as the GA-SA engine converges on an optimal solution.

### Generated Reports
After the script finishes, three files are created in the `/manual_run` folder:
- **`detailed_project_analysis.xlsx`**: A deep-dive report with route-by-route telemetry, truck types, and utilization percentages.
- **`analysis_results.json`**: Technical metadata for machine verification.
- **`detailed_simulation_log.txt`**: Verbose log of every single route path.

## 3. Submission Form Requirements
Based on the design challenge requirements (shown in the submission form):
- **GitHub Link**: This folder is currently a local Git repository. Please push `Team_RouteMind_Submission` to your public GitHub and provide the link.
- **Demo Video**: This is the video you will record. Ensure it covers both the Interactive Infographic and the Manual Analysis output.
- **.env File**: We have included the `.env` file in the root directory. You can upload this directly to the form as requested.

## Project Summary
Our solution uses a Hybrid GA-SA solver to optimize 1,583 collection points across Hyderabad, reducing carbon intensity to 0.57 kg CO2/T and achieving 100% GVP coverage with 108 vehicles.

## Team
- Vikramaditya Shah Bundela (IIT Hyderabad)
