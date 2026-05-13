# Deployment Guide

## Backend on Render (Free Tier)

1. Push code to GitHub
2. Go to [dashboard.render.com](https://dashboard.render.com)
3. Click **New +** → **Blueprint**
4. Connect your GitHub repo
5. Render will read `render.yaml` and auto-configure:
   - Gateway API (Docker)
   - Redis (free tier)
6. Add environment variables in Render dashboard:
   - `GROQ_API_KEY`
   - `ALCHEMY_URL` (use `https://rpc.ankr.com/polygon_mumbai`)
   - `CONTRACT_ADDRESS`
   - `WALLET_ADDRESS`
   - `PRIVATE_KEY`
7. Deploy

**Note:** Agents (SAGE, GUARDIAN, EMPATH, ORACLE) run as separate Docker services. For Render's free tier limitations, you may need to deploy them as separate Web Services or run locally.

## Frontend on Vercel (Free Tier)

### Option A: Vercel CLI
```bash
cd frontend
npm install
vercel --prod
```

### Option B: GitHub Integration
1. Push frontend folder to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Import project
4. Framework preset: **Vite**
5. Set environment variable:
   - `VITE_API_URL=https://your-render-gateway.onrender.com/api/v1`
6. Deploy

## Local Hardhat Blockchain (Offline Demo)

If you can't get test MATIC or RPC access:

```bash
cd blockchain
npm install

# Terminal 1: Start local node
npx hardhat node

# Terminal 2: Deploy contract
npx hardhat run scripts/start-local.js --network localhost

# Copy the printed CONTRACT_ADDRESS into your .env
# Set ALCHEMY_URL=http://host.docker.internal:8545
```

This gives you a fully functional blockchain on your laptop — perfect for hackathon judging.
