/**
 * App Router — SPA navigation + WebSocket event wiring.
 * Updated for 5-page layout matching SAMPLE.
 */
const router = {
    _currentPage: null,
    _pages: {
        dashboard: DashboardPage,
        task: TaskPage,
        runner: TaskRunnerPage,
        history: HistoryPage,
        emulators: EmulatorsPage,
        accounts: AccountsPage,
        workflow: WorkflowPage,
        settings: SettingsPage,
    },

    _labels: {
        dashboard: 'Dashboard',
        task: 'Task Checklist',
        runner: 'Actions',
        history: 'History',
        emulators: 'Emulators',
        accounts: 'Accounts',
        workflow: 'Workflows',
        settings: 'Settings',
    },

    navigate(pageName) {
        // Destroy current page
        if (this._currentPage && this._pages[this._currentPage]?.destroy) {
            this._pages[this._currentPage].destroy();
        }

        // Update nav active state
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.getAttribute('data-page') === pageName);
        });

        // Update header title
        const headerTitle = document.getElementById('header-title');
        if (headerTitle) headerTitle.textContent = this._labels[pageName] || pageName;

        // Render new page
        const page = this._pages[pageName];
        if (!page) return;

        const root = document.getElementById('page-root');
        if (root) root.innerHTML = page.render();

        this._currentPage = pageName;

        if (page.init) page.init();
    },
};

/**
 * Wire up WebSocket events to UI + notification bell.
 */
function setupWSEvents() {
    wsClient.on('task_started', (data) => {
        DeviceCard.updateStatus(data.serial, 'BUSY');
        DeviceCard.showProgress(data.serial, data.step || 'Starting...', 15);
        NotificationManager.add('info', 'Task Started', `${data.task_type || 'Task'} on ${data.serial}`);

        if (router._currentPage === 'runner') {
            TaskRunnerPage.updateFromWS('task_started', data);
        }
    });

    wsClient.on('task_progress', (data) => {
        const stepMap = {
            'Navigating to game screen...': 30,
            'Capturing screenshot...': 55,
            'Processing OCR...': 75,
        };
        const percent = stepMap[data.step] || 50;
        DeviceCard.showProgress(data.serial, data.step || 'Processing...', percent);

        if (router._currentPage === 'runner') {
            TaskRunnerPage.updateFromWS('task_progress', data);
        }
    });

    wsClient.on('task_completed', (data) => {
        DeviceCard.updateStatus(data.serial, 'ONLINE');
        DeviceCard.hideProgress(data.serial);

        if (data.data) {
            DeviceCard.updateData(data.serial, data.task_type, data.data);
        }

        const dur = data.duration_ms ? `${(data.duration_ms / 1000).toFixed(1)}s` : '';
        NotificationManager.add('success', 'Task Complete', `${data.task_type} on ${data.serial} ${dur}`);
        Toast.success('Task Complete', `${data.task_type} on ${data.serial} ${dur}`);

        if (router._currentPage === 'runner') {
            TaskRunnerPage.updateFromWS('task_completed', data);
        }
    });

    wsClient.on('task_failed', (data) => {
        DeviceCard.updateStatus(data.serial, 'ERROR');
        DeviceCard.hideProgress(data.serial);
        NotificationManager.add('error', 'Task Failed', `${data.serial}: ${data.error || 'Unknown'}`);
        Toast.error('Task Failed', `${data.serial}: ${data.error || 'Unknown error'}`);

        if (router._currentPage === 'runner') {
            TaskRunnerPage.updateFromWS('task_failed', data);
        }
    });

    // ──────────────────────────────────────────────
    // Full Scan Events
    // ──────────────────────────────────────────────
    wsClient.on('scan_progress', (data) => {
        DeviceCard.updateStatus(data.serial, 'BUSY');

        // Map capturing steps to roughly 0-40%, parsing to 80%, etc.
        let percent = 50;
        if (data.step.includes('capturing')) percent = 20;
        else if (data.step === 'ocr_processing') percent = 60;
        else if (data.step === 'parsing') percent = 80;
        else if (data.step === 'saving') percent = 90;

        const text = data.detail || (data.step === 'starting' ? 'Starting...' : data.step);
        DeviceCard.showProgress(data.serial, text, percent);
    });

    wsClient.on('scan_completed', (data) => {
        DeviceCard.updateStatus(data.serial, 'ONLINE');
        DeviceCard.hideProgress(data.serial);

        // Format and update data
        if (data.data) {
            DeviceCard.updateData(data.serial, 'full_scan', data.data);

            // Re-render device detail if open
            if (DeviceCard._currentOpenDetail === data.serial) {
                DashboardPage.showDeviceDetail(data.serial);
            }
        }

        const dur = data.elapsed_ms ? `${(data.elapsed_ms / 1000).toFixed(1)}s` : '';
        NotificationManager.add('success', 'Full Scan Complete', `Emulator #${data.emulator_index} completed in ${dur}`);
        Toast.success('Scan Complete', `Device ${data.serial} finished OCR.`);
    });

    wsClient.on('scan_failed', (data) => {
        DeviceCard.updateStatus(data.serial, 'ERROR');
        DeviceCard.hideProgress(data.serial);
        NotificationManager.add('error', 'Scan Failed', `${data.serial}: ${data.error || 'Unknown'}`);
        Toast.error('Scan Failed', `${data.serial}: ${data.error || 'Unknown error'}`);
    });
}

/**
 * App Init
 */
document.addEventListener('DOMContentLoaded', () => {
    wsClient.connect();
    setupWSEvents();
    router.navigate('dashboard');
});
