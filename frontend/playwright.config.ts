import {defineConfig} from '@playwright/test';
import {existsSync} from 'node:fs';
const python=process.env.BB_PYTHON || (existsSync('../.venv/Scripts/python.exe')?'../.venv/Scripts/python.exe':existsSync('../.venv/bin/python')?'../.venv/bin/python':'python');
export default defineConfig({
  testDir:'./e2e',fullyParallel:false,workers:1,timeout:45000,retries:0,
  outputDir:'../output/playwright/ci-results',
  reporter:[['list'],['html',{outputFolder:'../output/playwright/ci-report',open:'never'}]],
  use:{baseURL:'http://127.0.0.1:5179',browserName:'chromium',trace:'retain-on-failure',screenshot:'only-on-failure'},
  webServer:[
    {command:`"${python}" ../scripts/serve_e2e.py`,url:'http://127.0.0.1:18082/api/health',reuseExistingServer:false,timeout:120000},
    {command:'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5179 --strictPort',url:'http://127.0.0.1:5179',reuseExistingServer:false,
     env:{BACKEND_URL:'http://127.0.0.1:18082'},timeout:30000},
  ],
});
