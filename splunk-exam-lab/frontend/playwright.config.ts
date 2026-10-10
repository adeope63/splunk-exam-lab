import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',fullyParallel:false,workers:1,use:{baseURL:'http://127.0.0.1:5174',headless:true,screenshot:'only-on-failure',trace:'retain-on-failure'},reporter:[['list']],timeout:30000,webServer:[
{command:process.env.E2E_PYTHON||'../backend/.venv/bin/python ../backend/tests/run_e2e_server.py',url:'http://127.0.0.1:8001/api/health',reuseExistingServer:false},
{command:'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5174',url:'http://127.0.0.1:5174',env:{VITE_API_TARGET:'http://127.0.0.1:8001'},reuseExistingServer:false}
]});
