/**
 * simulation.js
 * Handles the logic for animating vehicles along their optimized routes.
 */

// Global state for simulation
let simulationRunning = false;
let simulationPaused = false;
let simulationSpeed = 50; // Points per second approx
let activeMarkers = [];
let animationFrameId = null;

// Telemetry Stats
let simStats = {
    distance: 0,
    waste: 0,
    co2: 0,
    progress: 0,
    totalPoints: 0,
    pointsVisited: 0,
    status: "Initializing..."
};

/**
 * Starts the simulation logic.
 * Reads global `routesData` and `map` from script.js scope (attached to window).
 */
function startSimulation() {
    if (simulationRunning) {
        stopSimulation(); // Toggle off if already running
        return;
    }

    // Check if dependencies exist
    if (typeof routesData === 'undefined' || typeof map === 'undefined') {
        console.error("Simulation Error: Missing routesData or map object.");
        return;
    }

    simulationRunning = true;
    simulationPaused = false;
    updateSimButtonText("Stop Simulation");
    updatePauseButtonText("Pause"); // Reset pause button

    // Clear any existing markers
    clearActiveMarkers();

    // Filter routes: We can animate all, or just visible ones.
    // For impact, let's animate ALL routes in the dataset.
    const routes = routesData.features;

    routes.forEach(route => {
        // Skip if geometry is not LineString
        if (!route.geometry || route.geometry.type !== 'LineString') return;

        // Extract coordinates ([lon, lat] format from GeoJSON)
        const coords = route.geometry.coordinates;

        // Skip invalid paths
        if (coords.length < 2) return;

        // Create a marker
        // Color coding based on Type
        let color = '#2ECC71'; // Default 16T Green
        const type = route.properties.type || '16t';

        if (type.toLowerCase().includes('8t')) color = '#3498DB'; // Blue
        if (type.toLowerCase().includes('4t')) color = '#E74C3C'; // Red

        const marker = L.circleMarker([coords[0][1], coords[0][0]], {
            radius: 5,
            fillColor: color,
            color: '#fff',
            weight: 1,
            opacity: 1,
            fillOpacity: 1,
            className: 'sim-vehicle'
        }).addTo(map);

        // Store marker and its animation state
        activeMarkers.push({
            marker: marker,
            path: coords, // Array of [lon, lat]
            currentIndex: 0,
            progress: 0,
            speed: Math.random() * 0.5 + 0.5,
            capacity: route.properties.load || 4000,
            distTotal: 0, // Track local distance
            vehicle_id: route.properties.vehicle_id || 'N/A', // Tag for lookup
            total_load: route.properties.load || 0,
            _uid: route.properties._uid // Stabilized unique lookup ID
        });
    });

    // Expose activeMarkers globally for script.js lookups
    window.activeMarkers = activeMarkers;

    // Reset Sim Stats
    simStats = {
        distance: 0,
        waste: 0,
        co2: 0,
        progress: 0,
        totalPoints: activeMarkers.reduce((acc, m) => acc + m.path.length, 0),
        pointsVisited: 0,
        fleet: activeMarkers.length,
        status: "Vehicles Dispatched"
    };

    if (window.updateTelemetry) window.updateTelemetry(simStats);

    animateLoop();
}

/**
 * Main Animation Loop
 */
function animateLoop() {
    if (!simulationRunning) return;

    // If paused, just loop without updating logic (freeze frame)
    if (simulationPaused) {
        animationFrameId = requestAnimationFrame(animateLoop);
        return;
    }

    let activeCount = 0;

    activeMarkers.forEach(agent => {
        // If agent finished path, skip
        if (agent.currentIndex >= agent.path.length - 1) return;

        activeCount++;

        // Advance progress
        // A simple constant speed along segments
        // Real logic would calculate distance, but for visual effect, simple interpolation works
        agent.progress += 0.02 * agent.speed * (simulationSpeed / 10);

        if (agent.progress >= 1) {
            agent.currentIndex++;
            agent.progress = 0;
        }

        // Check if finished after update
        if (agent.currentIndex >= agent.path.length - 1) {
            // Optional: Loop animation? Or just stop.
            // Let's stop at destination (SCTP)
            return;
        }

        // Interpolate position
        const p1 = agent.path[agent.currentIndex];
        const p2 = agent.path[agent.currentIndex + 1];

        // GeoJSON is [lon, lat], Leaflet needs [lat, lon]
        const lat = p1[1] + (p2[1] - p1[1]) * agent.progress;
        const lon = p1[0] + (p2[0] - p1[0]) * agent.progress;

        agent.marker.setLatLng([lat, lon]);

        // Accumulate stats (Estimated for visual impact)
        // distance += segment distance approx
        const p1_raw = L.latLng(p1[1], p1[0]);
        const p2_raw = L.latLng(p2[1], p2[0]);
        const segmentDist = p1_raw.distanceTo(p2_raw) / 1000; // km

        // Only add delta distance
        const deltaDist = segmentDist * 0.02 * agent.speed * (simulationSpeed / 10);
        simStats.distance += deltaDist;
        simStats.co2 += deltaDist * 0.45; // Average emission factor 0.45 kg/km
    });

    // Refresh Open Popups (NEW)
    // If a user has a popup open, we want to see the values changing live
    map.eachLayer(layer => {
        if (layer.getPopup && layer.getPopup() && layer.isPopupOpen()) {
            const popup = layer.getPopup();
            // Check if we have a generator on the layer
            if (layer.popupGenerator) {
                popup.setContent(layer.popupGenerator());
            }
        }
    });

    // Calculate Waste Cleared (Progressive based on points visited)
    simStats.pointsVisited = activeMarkers.reduce((acc, m) => acc + m.currentIndex, 0);
    simStats.progress = (simStats.pointsVisited / simStats.totalPoints) * 100;
    simStats.waste = (simStats.progress / 100) * 1349; // Total network waste
    simStats.fleet = activeCount;
    simStats.status = simStats.progress > 99 ? "Collection Complete" : "Optimization in Progress...";

    if (window.updateTelemetry) window.updateTelemetry(simStats);

    if (activeCount > 0) {
        animationFrameId = requestAnimationFrame(animateLoop);
    } else {
        simStats.isComplete = true;
        simStats.status = "Shift Ended: 100% Cleared";
        if (window.updateTelemetry) window.updateTelemetry(simStats);
        stopSimulation();
    }
}

function stopSimulation() {
    simulationRunning = false;
    simulationPaused = false;
    updateSimButtonText("Play Simulation");
    updatePauseButtonText("Pause"); // Reset back to default state
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
    }
    // We can choose to leave markers at end position or clear them.
    // Clearing seems cleaner for "Reset".
    setTimeout(clearActiveMarkers, 1000); // Clear after 1s delay
}

function clearActiveMarkers() {
    activeMarkers.forEach(agent => {
        map.removeLayer(agent.marker);
    });
    activeMarkers = [];
}

function updateSimButtonText(text) {
    const btn = document.getElementById('play-sim-btn');
    if (btn) {
        btn.innerHTML = `<span class="icon">▶</span> ${text}`;
        if (text.includes("Stop")) {
            btn.classList.add('active');
            btn.innerHTML = `<span class="icon">⏹</span> Stop Simulation`;
        } else {
            btn.classList.remove('active');
        }
    }
}

// Attach to window so HTML can access it
window.startSimulation = startSimulation;
window.togglePause = togglePause;

/**
 * Toggles Pause/Resume state
 */
function togglePause() {
    if (!simulationRunning) return;

    simulationPaused = !simulationPaused;
    updatePauseButtonText(simulationPaused ? "Resume" : "Pause");
}

function updatePauseButtonText(state) {
    const btn = document.getElementById('pause-sim-btn');
    if (btn) {
        if (state === "Resume") {
            btn.innerHTML = `<span class="icon">▶</span> Resume`;
            btn.classList.add('active'); // Highlight when paused/waiting to resume
        } else {
            btn.innerHTML = `<span class="icon">⏸</span> Pause`;
            btn.classList.remove('active');
        }
    }
}
