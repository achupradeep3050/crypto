module.exports = {
    apps: [{
        name: 'mr_backend',
        script: '/home/achu/Documents/MeanreversalRSI/venv/bin/uvicorn',
        args: 'backend.main:app --host 0.0.0.0 --port 8001',
        cwd: '/home/achu/Documents/MeanreversalRSI',
        interpreter: 'none',
        env: {
            PYTHONUNBUFFERED: '1',
            NODE_ENV: 'production'
        }
    }, {
        name: 'mr_frontend',
        script: 'manage.py',
        interpreter: '/home/achu/Documents/MeanreversalRSI/venv/bin/python',
        args: 'runserver 0.0.0.0:8000',
        cwd: '/home/achu/Documents/MeanreversalRSI/web_dashboard',
        env: {
            PYTHONUNBUFFERED: '1'
        }
    }]
};
