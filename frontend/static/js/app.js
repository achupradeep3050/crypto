document.addEventListener('DOMContentLoaded', () => {
    // const btnStart = document.getElementById('btn-start'); // Deprecated
    const btnStop = document.getElementById('btn-stop');
    const logsContainer = document.getElementById('logs-container');
    const settingsForm = document.getElementById('settings-form');

    async function fetchStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();

            // Update Global Status
            const statusEl = document.getElementById('global-status');
            if (data.active) {
                statusEl.innerText = `SYSTEM ONLINE // MODE: ${data.config.active_mode || data.mode || "UNKNOWN"}`;
                statusEl.classList.add('text-green-500');
                statusEl.classList.remove('text-red-500');

                // Show Stop Button
                if (btnStop) btnStop.classList.remove('hidden');

                // Highlight Active Mode
                document.querySelectorAll('.mode-card').forEach(el => el.classList.remove('active'));
                const activeMode = data.config.active_mode || "4H1H";
                const modeEl = document.getElementById(activeMode === "4H1H" ? "mode-4h" : "mode-15m");
                if (modeEl) modeEl.classList.add('active');

            } else {
                statusEl.innerText = "SYSTEM OFFLINE";
                statusEl.classList.remove('text-green-500');
                statusEl.classList.add('text-red-500');
                if (btnStop) btnStop.classList.add('hidden');
                document.querySelectorAll('.mode-card').forEach(el => el.classList.remove('active'));
            }

            // Update Market Table
            const tbody = document.getElementById('market-table-body');
            tbody.innerHTML = '';

            for (const [symbol, status] of Object.entries(data.statuses)) {
                const mdata = data.market_data[symbol] || {};
                const price = mdata.price || '--';
                const rsi = mdata.rsi || '--';
                const trend = mdata.trend || '--';
                const adx = mdata.adx || '--';

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="py-3 font-bold text-gray-300">${symbol}</td>
                    <td class="py-3 font-mono text-white">$${price}</td>
                    <td class="py-3 ${rsi > 70 ? 'text-red-400' : (rsi < 30 ? 'text-green-400' : '')}">${rsi}</td>
                    <td class="py-3 ${trend === 'UP' ? 'text-green-500' : 'text-red-500'}">${trend}</td>
                    <td class="py-3">${adx}</td>
                    <td class="py-3 text-right font-bold ${status.includes('Signal') ? 'text-white animate-pulse' : 'text-gray-600'}">${status}</td>
                `;
                tbody.appendChild(tr);
            }

            // Update Logs
            if (logsContainer) {
                logsContainer.innerHTML = data.logs.map(log => `<div class="log-entry">${log}</div>`).join('');
            }

            // Update Account Info
            if (data.account) {
                const bal = document.getElementById('val-balance');
                if (bal) bal.innerText = `$ ${data.account.balance.toFixed(2)}`;
            }

        } catch (e) {
            console.error(e);
        }
    }

    window.startBot = async function (mode) {
        try {
            await fetch('/api/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'start', mode: mode })
            });
            fetchStatus();
        } catch (e) { alert(e); }
    }

    window.stopBot = async function () {
        try {
            await fetch('/api/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'stop' })
            });
            fetchStatus();
        } catch (e) { alert(e); }
    }

    window.saveSettings = async function () {
        const agent = document.getElementById('inp-agent').value;
        // const risk = document.getElementById('inp-risk').value; 
        // Note: Risk input removed from HTML in last edit to simplify UI, but if needed can add back using old ID

        await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ agent_url: agent, risk: 5.0 }) # Default risk
        });
        alert("Configuration saved.");
    }

    // Auto-poll
    setInterval(fetchStatus, 2000);
    fetchStatus();
});
