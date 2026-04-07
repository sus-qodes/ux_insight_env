# First-Time Setup Guide: UX Insight Env

This guide walks through setting up `ux-insight-env` with Docker and Hugging Face Spaces from scratch.

Run commands from:

```powershell
cd D:\openEnv\ux_insight_env
```

## 1. Install Prerequisites

Install these first:

- Python 3.11 or 3.12. The hackathon spec supports Python 3.10-3.12; avoid Python 3.13 for final validation.
- Docker Desktop for Windows.
- Git for Windows.
- A Hugging Face account.

After installing Docker Desktop, restart PowerShell and verify:

```powershell
docker --version
docker info
```

If `docker` is not recognized, Docker Desktop is not installed correctly or its CLI is not on PATH.

## 2. Create And Activate A Virtual Environment

From `D:\openEnv`:

```powershell
cd D:\openEnv
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Then install dependencies:

```powershell
cd D:\openEnv\ux_insight_env
python -m pip install --upgrade pip
python -m pip install -r server\requirements.txt
python -m pip install huggingface_hub
```

## 3. Validate OpenEnv Locally

Run:

```powershell
openenv validate
```

If `openenv` is not recognized, try:

```powershell
python -m pip show openenv-core
```

Then either restart PowerShell or use the full Scripts path shown by Python. On this machine it was:

```powershell
& "C:\Users\shash\AppData\Roaming\Python\Python313\Scripts\openenv.exe" validate
```

Expected result:

```text
[OK] ux_insight: Ready for multi-mode deployment
```

## 4. Run The API Locally Without Docker

Start the server:

```powershell
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

In a second PowerShell window:

```powershell
curl.exe http://localhost:7860/health
curl.exe -X POST http://localhost:7860/reset
```

Expected health response:

```json
{"status":"healthy"}
```

Stop the server with `Ctrl+C`.

## 5. Build And Run Docker

Build the image:

```powershell
docker build -t ux-insight-env:latest -f server/Dockerfile .
```

Run it:

```powershell
docker run --rm -p 7860:7860 ux-insight-env:latest
```

In another PowerShell window:

```powershell
curl.exe http://localhost:7860/health
curl.exe -X POST http://localhost:7860/reset
```

If those return successfully, Docker is ready.

## 6. Run The Baseline Inference Script

You need a Hugging Face token with access to the inference endpoint/model you plan to use.

Set environment variables in PowerShell:

```powershell
$env:API_BASE_URL = "https://router.huggingface.co/v1/"
$env:MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct"
$env:HF_TOKEN = "hf_your_token_here"
$env:OPENENV_BASE_URL = "https://sushere-ux-insight-env.hf.space"
$env:OPENENV_IMAGE = "ux-insight-env:latest"
python inference.py
```

Expected output includes JSON logs like:

```json
{"type":"START","task":"easy","env":"ux-insight-env","model":"meta-llama/Llama-3.3-70B-Instruct"}
{"type":"STEP","step":1,"action":"...","reward":0.5,"done":true,"error":null}
{"type":"END","success":true,"steps":1,"score":0.5,"rewards":[0.5]}
```

After this run, update the `README.md` baseline scores with actual results.

## 7. Login To Hugging Face

Install and login:

```powershell
python -m pip install --upgrade huggingface_hub
& "C:\Users\shash\AppData\Roaming\Python\Python312\Scripts\hf.exe" auth login
```

Paste your Hugging Face token when prompted.

Verify:

```powershell
& "C:\Users\shash\AppData\Roaming\Python\Python312\Scripts\hf.exe" auth whoami
```

## 8. Deploy With OpenEnv

Your Hugging Face username is `sushere`, so use this repo ID:

```powershell
openenv push --repo-id sushere/ux-insight-env --enable-interface
```

If `openenv` is not on PATH, use the full `openenv.exe` path as in step 3.

After deployment, test:

```powershell
curl.exe https://sushere-ux-insight-env.hf.space/health
curl.exe -X POST https://sushere-ux-insight-env.hf.space/reset
```

Expected:

- `/health` returns HTTP 200.
- `/reset` returns HTTP 200 with an observation JSON payload.
- `/web` shows the OpenEnv Playground interface.

## 9. Optional Manual Hugging Face Space Setup

Use this only if `openenv push` does not work.

1. Go to Hugging Face Spaces.
2. Create a new Space named `ux-insight-env`.
3. Select SDK: Docker.
4. Add tags including `openenv`.
5. Push this repository to the Space Git remote.

Example:

```powershell
git init
git add .
git commit -m "Initial ux insight env submission"
git remote add space https://huggingface.co/spaces/sushere/ux-insight-env
git push space main
```

If the branch is named `master`, use:

```powershell
git branch -M main
git push space main
```

## 11. Final Pre-Push Checklist

Before final submission:

- `openenv validate` passes.
- `docker build -t ux-insight-env:latest -f server/Dockerfile .` succeeds.
- Docker container responds on `/health` and `/reset`.
- `python inference.py` runs for `easy`, `medium`, and `hard`.
- `README.md` has actual baseline scores, not only expected ranges.
- `README.md` deploy URLs use your real Hugging Face username.
- `/web` OpenEnv Playground loads correctly.
- Do not commit `__pycache__`, `.tmp`, `.venv`, or runtime outputs.

## Troubleshooting

If Docker says the daemon is not running:

```powershell
docker info
```

Open Docker Desktop and wait until it says the engine is running.

If Hugging Face push fails with authentication errors:

```powershell
& "C:\Users\shash\AppData\Roaming\Python\Python312\Scripts\hf.exe" auth logout
& "C:\Users\shash\AppData\Roaming\Python\Python312\Scripts\hf.exe" auth login
```

If `openenv` is not recognized:

```powershell
python -m pip show openenv-core
```

Then restart PowerShell, reactivate the virtual environment, and try again.

If `python inference.py` cannot find the local package, run it from:

```powershell
cd D:\openEnv\ux_insight_env
python inference.py
```
