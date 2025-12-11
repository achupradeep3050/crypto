// app.js - SPA Logic for Quant Systems

document.addEventListener('DOMContentLoaded', () => {
    initPage();
    setupTilt();
});

let pollInterval = null;
const API_BASE = 'http://localhost:8001';

async function clientLog(level, message, context = {}) {
    try {
        await fetch(`${API_BASE}/api/client_log`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ level, message, context })
        });
    } catch (e) { console.error("Log failed", e); }
}

// --- Visual Effects ---
function setupTilt() {
    const cards = document.querySelectorAll('.tilt-card');
    cards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const rotateX = ((y - centerY) / centerY) * -10; // Max 10deg
            const rotateY = ((x - centerX) / centerX) * 10;

            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale(1)';
        });
    });
}

// --- Initialization Logic ---
function initPage() {
    clientLog('info', 'Page Initialized', { url: window.location.href });

    // Clear existing interval if any
    if (pollInterval) clearInterval(pollInterval);

    // Initial Fetch
    fetchStatus();

    // Start Polling
    pollInterval = setInterval(fetchStatus, 2000);
}

// --- Status & Rendering Logic ---

async function fetchStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/status`);
        const data = await res.json();

        // Render Strategies
        // Render Strategies
        // MR & TMA Removed
        if (data.gold) renderGold(data.gold);

        // Render Bitcoin Breakout (Strategy Engine Name: BTC_BREAKOUT_5M)
        if (data.btc_breakout_5m) renderBTCBreakout(data.btc_breakout_5m);

        // Update Account Info
        if (data.account) {
            const balanceStr = `$ ${data.account.balance.toFixed(2)}`;
            const equityStr = `$ ${data.account.equity.toFixed(2)}`;

            // Header Balance
            const headerBal = document.getElementById('header-balance');
            if (headerBal) headerBal.innerText = balanceStr;

            // Dashboard Cards (if any specific balance elements exist)
            const bals = document.querySelectorAll('#val-balance');
            bals.forEach(el => el.innerText = balanceStr);
        }

        if (data.config) {
            updateConfigUI(data.config);
        }

    } catch (e) {
        console.error(e);
    }
}

// ... helper renderMultiTimeframeSection not needed for Single Breakout but useful concept ...

function renderBTCBreakout(data) {
    if (!data) return;

    // Status
    const statusTxt = document.getElementById('status-btc-breakout-5m');
    const btn = document.getElementById('btn-btc-breakout-5m');
    const masterStatus = null; // No master status for single card

    if (statusTxt && btn) {
        if (data.active) {
            statusTxt.innerText = "ACTIVE";
            statusTxt.className = "text-xs uppercase text-green-500 animate-pulse";
            btn.innerText = "DEACTIVATE";
            btn.className = "text-[10px] bg-red-900/40 hover:bg-red-800 border border-red-600 px-4 py-1 rounded transition text-red-400 hover:text-white uppercase font-bold";
            btn.onclick = () => window.toggleBot('btc_breakout_5m', 'stop');
        } else {
            statusTxt.innerText = "STANDBY";
            statusTxt.className = "text-xs uppercase text-gray-500";
            btn.innerText = "ACTIVATE";
            btn.className = "text-[10px] bg-green-900/40 hover:bg-green-600 border border-green-600 px-4 py-1 rounded transition text-green-400 hover:text-white uppercase font-bold";
            btn.onclick = () => window.toggleBot('btc_breakout_5m', 'start');
        }
    }

    // Data
    // Expecting data.data['BITCOIN']
    const mdata = (data.data && data.data['BITCOIN']) ? data.data['BITCOIN'] : {};

    // Price
    const elPrice = document.getElementById('price-btc-breakout-5m');
    if (elPrice && mdata.close) elPrice.innerText = '$' + mdata.close.toFixed(2);

    // High/Low
    const elHigh = document.getElementById('high-btc-breakout-5m');
    if (elHigh && mdata.high_n) elHigh.innerText = '$' + mdata.high_n.toFixed(2);

    const elLow = document.getElementById('low-btc-breakout-5m');
    if (elLow && mdata.low_n) elLow.innerText = '$' + mdata.low_n.toFixed(2);

    // ADX
    const elAdx = document.getElementById('adx-btc-breakout-5m');
    if (elAdx && mdata.adx) {
        elAdx.innerText = mdata.adx.toFixed(1);
        elAdx.className = `text-xl font-mono ${mdata.adx > 25 ? 'text-green-500' : 'text-yellow-500'}`;
    }

    // Signal
    const elSignal = document.getElementById('signal-btc-breakout-5m');
    if (elSignal) {
        // We don't get 'signal' directly from status unless we pass it.
        // But we can infer or pass it in 'extra'?
        // For now, let's just show trend based on Price vs EMA
        if (mdata.close && mdata.ema_trend) {
            if (mdata.close > mdata.ema_trend) {
                elSignal.innerText = "BULLISH";
                elSignal.className = "text-2xl font-black text-green-500";
            } else {
                elSignal.innerText = "BEARISH";
                elSignal.className = "text-2xl font-black text-red-500";
            }
        }
    }

    // Logs
    const logDiv = document.getElementById('logs-btc-breakout-5m');
    if (logDiv && data.logs) {
        logDiv.innerHTML = data.logs.slice(0, 20).map(formatLogLine).join('');
    }
}

// Helper to format log lines with colors
function formatLogLine(l) {
    let style = "text-gray-500";
    if (l.includes("[SIGNAL]")) style = "text-green-400 font-bold";
    else if (l.includes("[TRADE]")) style = "text-blue-400 font-bold";
    else if (l.includes("[EXIT]")) style = "text-orange-400";
    else if (l.includes("[ERROR]")) style = "text-red-500 font-bold";
    else if (l.includes("[WARN]")) style = "text-yellow-500";
    else if (l.includes("[SCAN]")) style = "text-gray-600 italic"; // Hide/dim scan logs slightly
    return `<div class="${style}">${l}</div>`;
}

// Generic helper for multi-timeframe sections
function renderMultiTimeframeSection(sectionName, sectionData, fields, colorClass, masterName) {
    if (!sectionData) return;
    const timeframes = ['1h', '15m', '5m'];
    let activeCount = 0;
    let allLogs = [];

    timeframes.forEach(tf => {
        const data = sectionData[tf];
        if (!data) return;

        if (data.active) activeCount++;

        // Logs (Just collect them, formatting happens later)
        if (data.logs) {
            allLogs = allLogs.concat(data.logs.map(l => ({ tf, l })));
        }

        // UI Elements
        const ind = document.getElementById(`ind-${sectionName}-${tf}`);
        const statusTxt = document.getElementById(`status-${sectionName}-${tf}`);
        const btn = document.getElementById(`btn-${sectionName}-${tf}`);

        // Status Update
        if (ind && statusTxt && btn) {
            if (data.active) {
                ind.classList.remove('bg-gray-600');
                ind.classList.add('bg-green-500', 'shadow-[0_0_15px_#22c55e]');
                statusTxt.innerText = "ONLINE";
                statusTxt.classList.remove('text-gray-500');
                statusTxt.classList.add('text-green-500');

                btn.innerText = "Stop";
                btn.className = "text-[10px] bg-red-900 hover:bg-red-800 px-2 py-1 rounded transition text-white";
                btn.onclick = () => window.toggleBot(`${masterName}_${tf}`, 'stop');
            } else {
                ind.classList.add('bg-gray-600');
                ind.classList.remove('bg-green-500', 'shadow-[0_0_15px_#22c55e]');
                statusTxt.innerText = "OFFLINE";
                statusTxt.classList.add('text-gray-500');
                statusTxt.classList.remove('text-green-500');

                btn.innerText = "Start";
                btn.className = "text-[10px] bg-gray-800 hover:bg-gray-700 px-2 py-1 rounded transition text-gray-300";
                btn.onclick = () => window.toggleBot(`${masterName}_${tf}`, 'start');
            }
        }

        // Data Update
        // Data usually keyed by symbol, but for granular engine, it's just one symbol usually.
        // We assume 'BITCOIN' for MR/TMA and 'GOLD' for GOLD.
        const symbolKey = (sectionName === 'gold') ? 'GOLD' : 'BITCOIN';
        const mdata = (data.data && data.data[symbolKey]) ? data.data[symbolKey] : {};

        fields.forEach(field => {
            const el = document.getElementById(`${field.id}-${sectionName}-${tf}`);
            if (el) {
                let val = mdata[field.key];
                if (val !== undefined && val !== null) {
                    if (field.format) val = field.format(val);
                    el.innerText = val;
                    if (field.style) field.style(el, val, mdata);
                } else {
                    el.innerText = '--';
                }
            }
        });
    });

    // Master Indicator (if exists)
    // Could be implemented via separate status elements for the card header
    // But we are reusing IDs like 'status-mr', 'ind-mr' if they exist
    // Actually our HTML has 'status-mr' etc.
    const masterStatus = document.getElementById(`status-${sectionName}`);
    if (masterStatus) {
        if (activeCount > 0) {
            masterStatus.innerText = activeCount === 3 ? "SYSTEM ACTIVE" : "PARTIAL ACTIVE";
            masterStatus.className = "text-xs uppercase " + (activeCount === 3 ? "text-green-500 animate-pulse" : "text-yellow-500");
        } else {
            masterStatus.innerText = "STANDBY";
            masterStatus.className = "text-xs uppercase text-gray-500";
        }
    }

    // Logs Update
    const logsContainer = document.getElementById(`logs-${sectionName}`);
    if (logsContainer) {
        // Collect, sort or just merge. Since we can't easily sort by time without parsing,
        // we'll just slice the raw merged array.
        // Ideally we'd sort by parsed timestamp but 'allLogs' is just objects now.
        // Let's assume order is fine or mix is acceptable for now.

        // Since we are iterating timeframes, 1h logs come first then 15m.
        // We might want to interleave or just show them.

        // Let's format them
        const rendered = allLogs.slice(0, 20).map(item => {
            const cleanLog = item.l;
            // Add TF tag
            const finalLog = `[${item.tf}] ${cleanLog}`;
            return formatLogLine(finalLog);
        }).join('');

        logsContainer.innerHTML = rendered;
    }
}

// MR & TMA Render Functions Removed

function renderGold(data) {
    renderMultiTimeframeSection('gold', data, [
        { id: 'price', key: 'close', format: v => '$' + v.toFixed(2) },
        {
            id: 'dema', key: 'rsi', format: v => v ? v.toFixed(1) : '--', style: (el, v) => {
                el.className = `py-3 font-mono ${v > 70 ? 'text-red-400' : (v < 30 ? 'text-green-400' : 'text-cyan-400')}`;
            }
        },
        {
            id: 'super', key: 'adx', format: v => v ? v.toFixed(1) : (v === 0 ? '0.0' : '--'), style: (el, v) => {
                el.className = "py-3 font-mono text-yellow-500";
            }
        }
    ], 'text-yellow-500', 'gold');
}


// --- Global Actions & Settings (Unchanged mostly) ---

window.openSettings = function () {
    const modal = document.getElementById('settings-modal');
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        document.getElementById('settings-content').classList.remove('scale-95');
        document.getElementById('settings-content').classList.add('scale-100');
    }, 10);
}

window.closeSettings = function () {
    const modal = document.getElementById('settings-modal');
    modal.classList.add('opacity-0');
    document.getElementById('settings-content').classList.remove('scale-100');
    document.getElementById('settings-content').classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

async function updateSettings() {
    const ipInput = document.getElementById('input-agent-ip');
    const riskInput = document.getElementById('input-risk');
    const btn = document.querySelector('button[onclick="updateSettings()"]');

    const ip = ipInput.value.trim();
    const risk = parseFloat(riskInput.value);

    // Basic Validation
    if (!ip) { alert("Please enter a valid IP address."); return; }
    if (isNaN(risk) || risk <= 0) { alert("Please enter a valid Risk %."); return; }

    const agentUrl = `http://${ip}:8001`;

    try {
        const originalText = btn.innerText;
        btn.innerText = "UPDATING...";
        btn.disabled = true;

        const res = await fetch(`${API_BASE}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent_url: agentUrl, risk: risk })
        });

        const data = await res.json();

        if (data.status === "updated") {
            alert("Configuration Updated Successfully!");
            window.closeSettings();
        } else {
            alert("Update Failed.");
        }

        btn.innerText = originalText;
        btn.disabled = false;
        fetchStatus();

    } catch (e) {
        alert("Connection Error.");
        btn.innerText = "UPDATE FAILED";
        btn.disabled = false;
    }
}

let configLoaded = false;
function updateConfigUI(config) {
    if (!config || configLoaded) return;
    try {
        const url = new URL(config.agent_url);
        const ip = url.hostname;
        const ipInput = document.getElementById('input-agent-ip');
        const riskInput = document.getElementById('input-risk');
        if (ipInput && !ipInput.value) ipInput.value = ip;
        if (riskInput && !riskInput.value) riskInput.value = config.risk;
        configLoaded = true;
    } catch (e) { console.error("Error parsing config URL", e); }
}

window.toggleBot = async function (target, action) {
    try {
        await fetch(`${API_BASE}/api/control`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action, target: target })
        });
        fetchStatus();
    } catch (e) { alert("API Connection Error"); }
}

window.stopAll = async function () {
    try {
        await fetch(`${API_BASE}/api/control`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'stop', target: 'all' })
        });
        fetchStatus();
    } catch (e) { alert("API Connection Error"); }
}

// --- Global Backtest Logic ---
window.backtestTrades = {}; // Store trades globally

async function runGlobalBacktest() {
    const daysInput = document.getElementById('backtestDays');
    const capitalInput = document.getElementById('backtestCapital');
    const days = daysInput ? daysInput.value : 30;
    const capital = capitalInput ? parseFloat(capitalInput.value) : 1000;

    // Update all Day Labels
    document.querySelectorAll('.bt-label-days').forEach(el => el.innerText = days);

    const btn = document.querySelector('button[onclick="runGlobalBacktest()"]');
    if (btn) {
        btn.innerText = "Analyzing...";
        btn.disabled = true;
    }

    // Clear previous trades
    window.backtestTrades = {};

    // New Strategy Mapping
    const strategies = [
        // Bitcoin Breakout (New)
        { id: 'btc-breakout-5m', strategy: 'BitcoinBreakout', symbol: 'BITCOIN', timeframe: '5m', logId: 'logs-btc-breakout-5m' },

        // MR / TMA Removed

        // Gold Strategies (All 3)
        { id: 'gold-1h', strategy: 'GoldTrend', symbol: 'GOLD', timeframe: '1h', logId: 'logs-gold' },
        { id: 'gold-15m', strategy: 'GoldSniper', symbol: 'GOLD', timeframe: '15m', logId: 'logs-gold' },
        { id: 'gold-5m', strategy: 'GoldFlux', symbol: 'GOLD', timeframe: '5m', logId: 'logs-gold' }
    ];

    const promises = strategies.map(async (item) => {
        const resDiv = document.getElementById(`res-${item.id}`);
        // Support specific PNL spans for Breakout (naming is custom in BTC Breakout card vs generic table)
        // Table uses 'pnl-mr-1h', Breakout uses 'pnl-btc-breakout-5m'
        // Luckily I mapped id 'btc-breakout-5m' which matches ID in HTML!
        const wrSpan = document.getElementById(`wr-${item.id}`);
        const pnlSpan = document.getElementById(`pnl-${item.id}`);

        if (resDiv) {
            // ... opacity logic
            resDiv.style.opacity = "0.5";
            if (wrSpan) wrSpan.innerText = "...";
            if (pnlSpan) pnlSpan.innerText = "...";
        }

        // ... rest of logic

        try {
            const response = await fetch(`${API_BASE}/api/backtest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    strategy: item.strategy,
                    symbol: item.symbol,
                    timeframe: item.timeframe,
                    balance: capital,
                    days: parseInt(days)
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.error) {
                    if (wrSpan) wrSpan.innerText = "Err";
                    return;
                }

                const start = capital;
                const end = data.final_balance;
                const pnl = end - start;
                const color = pnl >= 0 ? "#4ade80" : "#f87171"; // Green/Red
                let winRate = (data.win_rate * 100).toFixed(0) + "%";
                if (data.total_trades === 0) winRate = "-";

                // Store Trades
                if (data.trades) {
                    window.backtestTrades[item.id] = data.trades;
                }

                // Update UI (Generic)
                if (resDiv) resDiv.style.opacity = "1";
                if (wrSpan) wrSpan.innerText = winRate;
                if (pnlSpan) {
                    pnlSpan.innerText = (pnl >= 0 ? "+" : "") + pnl.toFixed(2);
                    pnlSpan.style.color = color;
                }
            }
        } catch (e) {
            if (wrSpan) wrSpan.innerText = "Err";
        }
    });

    await Promise.all(promises);

    if (btn) {
        btn.innerText = "Run Analysis";
        btn.disabled = false;
    }
}

// --- Trade Modal Logic ---
window.showTrades = function (id) {
    const trades = window.backtestTrades[id];
    const tbody = document.getElementById('trades-table-body');
    const modal = document.getElementById('trades-modal');
    const content = document.getElementById('trades-content');

    if (!tbody || !modal) return;
    tbody.innerHTML = '';

    if (!trades || trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="p-4 text-center text-gray-500">No trades recorded for this period.</td></tr>';
    } else {
        // Sort by time descending
        const sortedTrades = [...trades].reverse();

        sortedTrades.forEach(t => {
            const row = document.createElement('tr');
            row.className = "hover:bg-gray-800/50 transition border-b border-gray-800/30";

            // Format Time (Unix Timestamp)
            const date = new Date(t.entry_time * 1000);
            const timeStr = date.toLocaleString();

            // Color for Type
            const typeColor = t.type === 'long' ? 'text-green-400' : 'text-red-400';
            const typeLabel = t.type.toUpperCase();

            // Color for PnL
            const pnlColor = t.pnl >= 0 ? 'text-green-400' : 'text-red-400';
            const pnlStr = (t.pnl >= 0 ? '+' : '') + t.pnl.toFixed(2);

            row.innerHTML = `
                <td class="p-2 text-gray-400">${timeStr}</td>
                <td class="p-2 font-bold ${typeColor}">${typeLabel}</td>
                <td class="p-2 text-gray-300">$${t.entry.toFixed(2)}</td>
                <td class="p-2 text-gray-300">$${t.exit.toFixed(2)}</td>
                <td class="p-2 text-right font-bold ${pnlColor}">${pnlStr}</td>
            `;
            tbody.appendChild(row);
        });
    }

    modal.classList.remove('hidden');
    // Animate in
    requestAnimationFrame(() => {
        modal.classList.remove('opacity-0');
        content.classList.remove('scale-95');
        content.classList.add('scale-100');
    });
}

window.closeTrades = function () {
    const modal = document.getElementById('trades-modal');
    const content = document.getElementById('trades-content');
    if (!modal) return;

    modal.classList.add('opacity-0');
    content.classList.remove('scale-100');
    content.classList.add('scale-95');

    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}
