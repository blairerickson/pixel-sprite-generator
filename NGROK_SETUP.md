# Ngrok Setup for Remote Access

## 🌐 How to Share Your Pixel Sprite Generator with Ngrok

### **Step 1: Install ngrok**
```bash
# If you don't have ngrok installed:
brew install ngrok

# Or download from: https://ngrok.com/download
```

### **Step 2: Start Your Services Locally**
```bash
# Terminal 1 - Start Stable Diffusion WebUI
cd /Users/himanshumacpro24/Development/pixel-sprite-generator
./start_webui.sh

# Terminal 2 - Start Backend
cd /Users/himanshumacpro24/Development/pixel-sprite-generator
./start_backend.sh
```

### **Step 3: Expose Backend with ngrok**
```bash
# Terminal 3 - Start ngrok
ngrok http 8010
```

You'll see output like:
```
Forwarding   https://abc123.ngrok.io -> http://localhost:8010
```

### **Step 4: Share the Link**
Send the ngrok URL to anyone: `https://abc123.ngrok.io`

They can:
- ✅ Generate pixel sprites
- ✅ Download the generated images
- ✅ Use all features (Icon mode, Character mode, etc.)
- ✅ Access from anywhere in the world

---

## ⚠️ **Important Notes**

### **1. API URL Configuration**
You might need to update the frontend to use the ngrok URL:

Edit `/frontend/app.js` line 22:
```javascript
// Change from:
const API_BASE = 'http://127.0.0.1:8010';

// To:
const API_BASE = ''; // Empty string uses same domain
```

This way the frontend will automatically use the ngrok domain.

### **2. Stable Diffusion WebUI Must Run Locally**
The ngrok tunnel only exposes the backend. The **Stable Diffusion WebUI** still runs on your Mac (port 7860), and the backend connects to it locally. This is good because:
- ✅ Your GPU does the heavy lifting
- ✅ Models stay on your machine
- ✅ Users can't access your SD WebUI directly

### **3. Performance**
- Image generation happens on **your Mac**
- Users just see the web interface through ngrok
- Generation speed depends on **your Mac's performance**, not user's internet

### **4. Free ngrok Limitations**
- URL changes every time you restart ngrok (unless you have paid plan)
- Session timeout after 2 hours on free tier
- Bandwidth limits apply

### **5. Security Considerations**
- Anyone with the link can use your generator
- It uses **your Mac's GPU/CPU** for generation
- Consider adding authentication if sharing publicly
- Monitor resource usage

---

## 🎯 **Quick Start Commands**

### **Recommended Setup:**
```bash
# Terminal 1 - WebUI
./start_webui.sh

# Terminal 2 - Backend  
./start_backend.sh

# Terminal 3 - Ngrok
ngrok http 8010
```

### **Share the ngrok URL** (looks like):
```
https://abc-123-xyz.ngrok-free.app
```

---

## 📥 **What Users Can Download**

Users will be able to download:
- ✅ Generated sprite images (PNG)
- ✅ Animation frames
- ✅ Sprite sheets
- ✅ All processed outputs

The download happens through the ngrok tunnel, so files are served from your backend.

---

## 🔒 **Optional: Add Authentication**

If you want to restrict access, you can add ngrok basic auth:
```bash
ngrok http 8010 --basic-auth="username:password"
```

Or use ngrok's dashboard to configure authentication.

---

## 💡 **Pro Tips**

1. **Keep your Mac awake** - Users can't access if your Mac sleeps
2. **Monitor GPU usage** - Multiple users = more load
3. **Use paid ngrok** - Get permanent URL and better bandwidth
4. **Test locally first** - Make sure everything works before sharing
5. **Check firewall** - Ensure ngrok can create tunnels

