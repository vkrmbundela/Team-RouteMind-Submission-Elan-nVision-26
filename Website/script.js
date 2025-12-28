if (window.log) window.log("SCRIPT.JS: Pipeline Initialized.", "info");

const initApp = () => {
    if (window.log) window.log("SCRIPT.JS: Starting initApp()...", "info");

    // --- 1. UI Utilities & Interactions ---

    // HUD Toggle Logic
    window.toggleHUD = () => {
        const hud = document.getElementById('telemetryHUD');
        const icon = document.getElementById('hudToggleIcon');
        if (hud) {
            hud.classList.toggle('minimized');
            if (icon) {
                if (hud.classList.contains('minimized')) {
                    icon.classList.replace('fa-compress-alt', 'fa-expand-alt');
                } else {
                    icon.classList.replace('fa-expand-alt', 'fa-compress-alt');
                }
            }
        }
    };

    // Back to Top Button
    const btt = document.getElementById('backToTop');
    if (btt) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 500) {
                btt.classList.add('visible');
            } else {
                btt.classList.remove('visible');
            }
        });
        btt.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Scroll Reveal Observer
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.section, .card, .content-block, .pipeline-step, .gantt-section, .math-box, .equation-block, .table-container').forEach(el => {
        el.classList.add('reveal');
        revealObserver.observe(el);
    });

    // Smooth Scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // --- 2. Data Visualizations (Chart.js) ---
    if (typeof Chart !== 'undefined') {
        Chart.defaults.font.family = "'Outfit', sans-serif";
        Chart.defaults.color = '#555';

        // Load Intensity Chart
        const loadChartEl = document.getElementById('loadChart');
        if (loadChartEl) {
            new Chart(loadChartEl.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: ['16T Heavy', '8T Medium', '4T Mini'],
                    datasets: [{
                        label: 'Capacity Usage (%)',
                        data: [93, 96, 431],
                        backgroundColor: ['#2ecc71', '#3498db', '#e74c3c'],
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: { y: { suggestedMax: 450 } }
                }
            });
        }

        // Emission Doughnut
        const emissionChartEl = document.getElementById('emissionChart');
        if (emissionChartEl) {
            new Chart(emissionChartEl.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: ['16T (Optimal)', '4T (Inefficient)', '8T'],
                    datasets: [{
                        data: [53, 282, 100],
                        backgroundColor: ['#2ecc71', '#e74c3c', '#3498db']
                    }]
                },
                options: { responsive: true, cutout: '70%' }
            });
        }

        // AI Convergence Graph
        const convergenceChartEl = document.getElementById('convergenceChart');
        if (convergenceChartEl) {
            new Chart(convergenceChartEl.getContext('2d'), {
                type: 'line',
                data: {
                    labels: Array.from({ length: 50 }, (_, i) => i + 1),
                    datasets: [{
                        label: 'Optimization Fitness',
                        data: [5200, 4800, 4100, 3600, 3200, 2900, 2800, 2750, 2740, 2738].concat(Array(40).fill(2738)),
                        borderColor: '#2ecc71',
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { x: { display: false }, y: { title: { display: true, text: 'Cost Score' } } }
                }
            });
        }
    }

    // --- 3. Modal System ---
    const modalOverlay = document.getElementById('modal-overlay');
    const modalContent = document.getElementById('modal-content');
    const closeBtn = document.querySelector('.modal-close');

    const zoneData = [
        { name: "Chacha Nehuru Park", waste: 126.4, fleet: 29, co2: 196.4 },
        { name: "IBT", waste: 221.5, fleet: 53, co2: 345.5 },
        { name: "Ziyaguda", waste: 250.5, fleet: 56, co2: 402.2 },
        { name: "Bandlaguda", waste: 42.8, fleet: 12, co2: 70.5 },
        { name: "Auto Nagar", waste: 67.9, fleet: 16, co2: 126.2 },
        { name: "Jubilee Hills Road No 51", waste: 153.2, fleet: 35, co2: 296.1 },
        { name: "Nagole", waste: 89.3, fleet: 21, co2: 158.7 },
        { name: "Devender Nagar", waste: 54.6, fleet: 14, co2: 95.3 },
        { name: "Mallapur", waste: 72.1, fleet: 18, co2: 134.8 },
        { name: "Saket", waste: 48.5, fleet: 11, co2: 82.1 },
        { name: "Hasthinapuram", waste: 63.7, fleet: 15, co2: 112.4 },
        { name: "Kattedan", waste: 58.2, fleet: 13, co2: 98.6 },
        { name: "Mir Alam Tank", waste: 45.9, fleet: 10, co2: 76.3 },
        { name: "Peoples Plaza", waste: 38.4, fleet: 9, co2: 64.2 },
        { name: "Sanath Nagar", waste: 81.6, fleet: 19, co2: 145.9 },
        { name: "Lalapet Flyover", waste: 56.3, fleet: 13, co2: 99.8 },
        { name: "Jalagam Vengal Rao Park", waste: 35.2, fleet: 8, co2: 58.7 },
        { name: "Singareni Colony", waste: 42.9, fleet: 10, co2: 73.5 }
    ];

    const openModal = (type) => {
        const tmpl = document.getElementById('tmpl-' + type);
        if (!tmpl || !modalOverlay || !modalContent) return;

        modalContent.innerHTML = '';
        modalContent.appendChild(tmpl.content.cloneNode(true));
        modalOverlay.classList.add('active');

        // Dynamic Table Injection
        if (type === 'methodology') {
            const tbody = modalContent.querySelector('#zone-table-body');
            if (tbody) {
                tbody.innerHTML = zoneData.map(z => `
                    <tr>
                        <td>${z.name}</td>
                        <td>${z.waste}</td>
                        <td>${z.fleet}</td>
                        <td>${z.co2}</td>
                    </tr>
                `).join('');
            }
        }
    };

    document.querySelectorAll('[data-modal]').forEach(btn => {
        btn.addEventListener('click', () => openModal(btn.getAttribute('data-modal')));
    });

    if (closeBtn) closeBtn.addEventListener('click', () => modalOverlay.classList.remove('active'));
    if (modalOverlay) modalOverlay.addEventListener('click', (e) => { if (e.target === modalOverlay) modalOverlay.classList.remove('active'); });

    // --- 4. Zonal Leaderboard ---
    const populateLeaderboard = () => {
        const tbody = document.querySelector('#zonalLeaderboard tbody');
        if (!tbody) return;

        const ranked = [...zoneData].sort((a, b) => (b.waste / b.co2) - (a.waste / a.co2));
        tbody.innerHTML = ranked.map((z, i) => `
            <tr class="${i === 0 ? 'top-rank' : ''}">
                <td><strong>#${i + 1}</strong></td>
                <td>${z.name}</td>
                <td>${z.waste} T</td>
                <td>${z.fleet}</td>
                <td><span class="efficiency-badge grade-${i < 2 ? 'a' : 'b'}">${i < 2 ? 'A' : 'B'}</span></td>
            </tr>
        `).join('');
    };
    populateLeaderboard();

    // --- 5. Map & Simulation Integration ---
    const mapElement = document.getElementById('map');
    if (mapElement) {
        const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        });

        const map = L.map('map', {
            center: [17.385, 78.4867],
            zoom: 11,
            layers: [osmLayer]
        });
        window.map = map;

        const routeLayer = L.layerGroup();
        const sctpLayer = L.layerGroup();
        const gvpLayer = L.layerGroup();

        // Load Routes
        let geoJsonLayer;
        if (typeof routesData !== 'undefined') {
            routesData.features.forEach((f, i) => f.properties._uid = `route_${i}`);
            geoJsonLayer = L.geoJSON(routesData, {
                style: (f) => ({ color: f.properties.color || '#3498db', weight: 4, opacity: 0.7 }),
                onEachFeature: (f, l) => {
                    l.popupGenerator = () => {
                        // 1. Resolve Vehicle ID
                        let vId = f.properties.vehicle_id;
                        if (!vId || vId === "N/A") {
                            // Fallback ID based on _uid injected earlier
                            const uid = f.properties._uid || 'route_0';
                            const idx = parseInt(uid.split('_')[1]) + 1;
                            vId = `V-${String(idx).padStart(3, '0')}`;
                        }

                        // 2. Resolve Dynamic Data
                        let load = f.properties.load;
                        let util = f.properties.utilization;
                        let status = "Scheduled";
                        let isLive = false;
                        let progress = 0;

                        if (window.activeMarkers?.length) {
                            const agent = window.activeMarkers.find(a => a._uid === f.properties._uid);
                            if (agent) {
                                isLive = true;
                                status = "In Transit";
                                // Calculate Interpolated Load
                                const ratio = (agent.currentIndex + agent.progress) / agent.path.length;
                                load = Math.round(agent.total_load * ratio);
                                util = Math.round((load / agent.capacity) * 100);
                                progress = Math.round(ratio * 100);
                            }
                        }

                        // 3. Build Aesthetic Popup HTML
                        return `
                            <div class="popup-mini">
                                <div class="popup-header">
                                    <span class="v-icon">🚛</span>
                                    <span>${vId}</span>
                                    ${isLive ? '<span class="status-badge live">LIVE</span>' : '<span class="status-badge">IDLE</span>'}
                                </div>
                                <div class="popup-body">
                                    <div class="stat-row">
                                        <span class="stat-label">Load</span>
                                        <span class="stat-val">${load} kg</span>
                                    </div>
                                    <div class="stat-row">
                                        <span class="stat-label">Utilization</span>
                                        <div class="progress-bar-mini">
                                            <div class="fill" style="width: ${util}%"></div>
                                        </div>
                                        <span class="stat-val-sm">${util}%</span>
                                    </div>
                                    </div>
                                </div>
                            </div>
                        `;
                    };
                    l.bindPopup(l.popupGenerator());
                    l.on('popupopen', (e) => e.popup.setContent(l.popupGenerator()));
                }
            }).addTo(routeLayer);
            routeLayer.addTo(map);
            map.fitBounds(geoJsonLayer.getBounds());
        }

        // Load SCTPs
        if (typeof sctpData !== 'undefined') {
            L.geoJSON(sctpData, {
                pointToLayer: (f, latlng) => L.circleMarker(latlng, {
                    radius: 8,
                    fillColor: '#f39c12',
                    color: '#000',
                    weight: 2,
                    fillOpacity: 0.9
                }),
                onEachFeature: (f, l) => {
                    l.bindPopup(`<strong>SCTP:</strong> ${f.properties.SCTP_Name}<br><strong>ID:</strong> ${f.properties.SCTP_ID}`);
                }
            }).addTo(sctpLayer);
            sctpLayer.addTo(map);
        }

        // Load GVPs
        if (typeof gvpData !== 'undefined') {
            L.geoJSON(gvpData, {
                pointToLayer: (f, latlng) => L.circleMarker(latlng, {
                    radius: 3,
                    fillColor: '#6c5ce7',
                    color: '#fff',
                    weight: 1,
                    fillOpacity: 0.8
                }),
                onEachFeature: (f, l) => {
                    l.bindPopup(`<strong>GVP:</strong> ${f.properties.name}<br><strong>Waste:</strong> ${f.properties.waste} Tonnes`);
                }
            }).addTo(gvpLayer);
            // GVP not added by default (too many points)
        }

        // Custom Layer Toggle Handlers (replaces L.control.layers)
        const toggleRoutes = document.getElementById('toggle-routes');
        const toggleSctp = document.getElementById('toggle-sctp');
        const toggleGvp = document.getElementById('toggle-gvp');

        if (toggleRoutes) {
            toggleRoutes.addEventListener('change', (e) => {
                if (e.target.checked) {
                    routeLayer.addTo(map);
                } else {
                    map.removeLayer(routeLayer);
                }
            });
        }

        if (toggleSctp) {
            toggleSctp.addEventListener('change', (e) => {
                if (e.target.checked) {
                    sctpLayer.addTo(map);
                } else {
                    map.removeLayer(sctpLayer);
                }
            });
        }

        if (toggleGvp) {
            toggleGvp.addEventListener('change', (e) => {
                if (e.target.checked) {
                    gvpLayer.addTo(map);
                } else {
                    map.removeLayer(gvpLayer);
                }
            });
        }

        // Opacity Helpers
        const updateLayerOpacity = (layerGroup, opacity) => {
            layerGroup.eachLayer(layer => {
                if (layer.eachLayer) {
                    layer.eachLayer(subLayer => {
                        if (subLayer.setStyle) {
                            subLayer.setStyle({ opacity: opacity, fillOpacity: opacity * 0.8 });
                        }
                    });
                }
            });
        };

        // Opacity Slider Listeners
        const opRoutes = document.getElementById('opacity-routes');
        const opGvp = document.getElementById('opacity-gvp');
        const opSctp = document.getElementById('opacity-sctp');
        const opBg = document.getElementById('opacity-bg');

        if (opRoutes) {
            opRoutes.addEventListener('input', (e) => {
                const val = parseFloat(e.target.value);
                routeLayer.eachLayer(layer => layer.eachLayer(l => l.setStyle({ opacity: val })));
            });
        }
        if (opGvp) {
            opGvp.addEventListener('input', (e) => updateLayerOpacity(gvpLayer, parseFloat(e.target.value)));
        }
        if (opSctp) {
            opSctp.addEventListener('input', (e) => updateLayerOpacity(sctpLayer, parseFloat(e.target.value)));
        }
        if (opBg) {
            opBg.addEventListener('input', (e) => osmLayer.setOpacity(parseFloat(e.target.value)));
        }

        // Color Picker Listeners
        const color16t = document.getElementById('color-16t');
        const color8t = document.getElementById('color-8t');
        const color4t = document.getElementById('color-4t');

        const updateRouteColor = (typeKey, color) => {
            routeLayer.eachLayer(layer => {
                layer.eachLayer(subLayer => {
                    if (subLayer.feature?.properties?.type?.includes(typeKey)) {
                        subLayer.setStyle({ color: color });
                    }
                });
            });
            const dot = document.getElementById(`legend-dot-${typeKey.toLowerCase()}`);
            if (dot) dot.style.backgroundColor = color;
        };

        if (color16t) color16t.addEventListener('input', (e) => updateRouteColor('16T', e.target.value));
        if (color8t) color8t.addEventListener('input', (e) => updateRouteColor('8T', e.target.value));
        if (color4t) color4t.addEventListener('input', (e) => updateRouteColor('4T', e.target.value));

        // HUD Updates
        window.updateTelemetry = (stats) => {
            // Element Access
            const elStatus = document.getElementById('hudStatusText');
            const elProgress = document.getElementById('hudProgressBar');
            const elDist = document.getElementById('hudDistance');
            const elWaste = document.getElementById('hudLiveLoad'); // Now represents collected waste
            const elFleet = document.getElementById('hudActiveTrucks');
            const elCO2 = document.getElementById('hudCO2');
            const pulse = document.querySelector('.pulse-icon');

            // Logic Updates
            if (elStatus) elStatus.innerText = stats.status.toUpperCase();
            if (elProgress) elProgress.style.width = stats.progress + "%";

            if (elDist) elDist.innerText = stats.distance.toFixed(1);
            if (elWaste) elWaste.innerText = Math.round(stats.waste).toLocaleString();
            if (elFleet) elFleet.innerText = stats.fleet || "0";
            if (elCO2) elCO2.innerText = Math.round(stats.co2).toLocaleString();

            if (pulse) pulse.style.background = stats.isComplete ? '#3498db' : '#2ecc71';
        };

        if (window.log) window.log("SCRIPT.JS: Map controls initialized.", "success");
    }

    if (window.log) window.log("Aesthetic Polish: Completed.", "success");
};

document.addEventListener('DOMContentLoaded', () => {
    try { initApp(); }
    catch (e) { console.error(e); if (window.log) window.log("Init Failed: " + e.message, "error"); }
});
