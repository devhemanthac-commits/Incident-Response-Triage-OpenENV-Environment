# Hugging Face Spaces Deployment Guide

Deploy **Incident Response Triage** to Hugging Face Spaces in **5 minutes**.

## Why HF Spaces?

✅ **Free** — No credit card required  
✅ **Easy** — Git-based deployment  
✅ **Reliable** — Auto-restart on failure  
✅ **Shareable** — Public URL for everyone  

## Quick Start (5 Minutes)

### Step 1: Create Your Space

Go to [huggingface.co/new-space](https://huggingface.co/new-space):

1. **Space name**: `incident-response-triage`
2. **License**: `openrail` (default)
3. **SDK**: Select **Docker**
4. **Visibility**: **Public**
5. Click **Create Space**

### Step 2: Clone & Push

```bash
# Clone your Space repository
git clone https://huggingface.co/spaces/YOUR_USERNAME/incident-response-triage
cd incident-response-triage

# Copy all files from the GitHub repository
git clone https://github.com/devhemanthac-commits/Incident-Response-Triage-OpenENV-Environment.git /tmp/source
cp -r /tmp/source/* .
rm -rf /tmp/source

# Commit and push
git add .
git commit -m "Deploy Incident Response Triage v2.1.0"
git push
```

**That's it!** HF Spaces automatically builds your Docker image and deploys it.

### Your Space URL

Once deployed, your Space is live at:

```
https://huggingface.co/spaces/YOUR_USERNAME/incident-response-triage
```

The API endpoint is:

```
https://YOUR_USERNAME-incident-response-triage.hf.space
```

## Adding API Keys (Optional)

To use GPT-4o-mini or Gemini features:

1. Go to your Space page
2. Click **Settings** (gear icon, top right)
3. Scroll to **Repository secrets**
4. Add these environment variables:

| Key | Value | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | `sk-...` | For GPT-4o-mini |
| `GEMINI_API_KEY` | `AIzaSy...` | For Gemini 2.5 Flash |

Your API keys are **encrypted** and **private**.

## Test Your Deployment

Once the Space shows **✅ Running**:

```bash
# Health check
curl https://YOUR_USERNAME-incident-response-triage.hf.space/health
# Expected: {"status":"ok"}

# Reset to easy-1 scenario
curl -X POST https://YOUR_USERNAME-incident-response-triage.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy-1"}' | jq .incident_id

# Submit triage decision
curl -X POST https://YOUR_USERNAME-incident-response-triage.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{
    "severity": "P2",
    "team": "database",
    "escalate": false,
    "confidence": 0.9,
    "reasoning": "Disk at 95% on postgres-primary, trending upward from 88%"
  }' | jq '.reward.score'
```

## Monitoring Your Space

**In the Space UI, you can:**

- **Logs tab**: View real-time server output
- **Build tab**: Monitor Docker build progress (usually < 5 min)
- **Files tab**: Edit/view any file in the repository
- **Settings tab**: Manage secrets, hardware, visibility

## Common Issues & Solutions

### Build Takes Too Long (> 10 min)

**Solution**: Check the **Build** tab for errors. Common causes:

- Missing dependencies in `requirements.txt`
- Dockerfile syntax error
- Temporary network issues (try restarting)

### "Build failed" Error

**Solution**: Check **Build logs**:

```
ERROR: Failed to install requirements
→ Verify requirements.txt has correct package names

ERROR: Python version not found
→ Ensure Dockerfile uses python:3.11-slim
```

### Space "Running" but API Returns 500 Error

**Solution**:
1. Check **Logs** tab for error messages
2. Verify `app.py` binds to `0.0.0.0:5000`
3. Ensure all Python files are copied in Dockerfile
4. Click **Restart** in Settings

### Timeout Errors

HF Spaces have a **1-hour timeout limit** per request. Our app responds in < 1 second, so this shouldn't occur.

## Updating Your Space

To push updates:

```bash
cd your-local-space-clone
git add .
git commit -m "Update: describe your changes"
git push
```

HF Spaces automatically rebuilds and restarts your application.

## Sharing Your Space

Your Space URL is shareable:

```
https://huggingface.co/spaces/YOUR_USERNAME/incident-response-triage
```

Others can:
- **View your code** in the Files tab
- **Fork it** to create their own version
- **Use your API** (if you allow public access)

## Pro Tips

| Tip | Benefit |
|---|---|
| Pin your Space | Higher visibility in your profile |
| Add to **Collections** | Organize with other projects |
| Use **Staging Space** | Test changes before deploying |
| Enable **Persistent Storage** | Save files between restarts |
| Custom **README** | Add welcome message on Space page |

## For Hackathon Judges

Your Space demonstrates **production-grade deployment**:

✅ **Containerized** — Docker with Gunicorn, health checks  
✅ **Scalable** — 4 worker processes, resource limits  
✅ **Secure** — Non-root user, no hardcoded secrets  
✅ **Maintainable** — Professional CI/CD with git  
✅ **Observable** — Real-time logs and monitoring  

## Resources

- **Main README**: Full documentation, architecture, API reference
- **Deployment Guide**: See `DEPLOYMENT.md` for other options (Docker, K8s, VPS)
- **GitHub**: https://github.com/devhemanthac-commits/Incident-Response-Triage-OpenENV-Environment
- **HF Spaces Docs**: https://huggingface.co/docs/hub/spaces

---

**Ready to deploy?** Follow the **Quick Start** section above — you'll be live in 5 minutes! 🚀
