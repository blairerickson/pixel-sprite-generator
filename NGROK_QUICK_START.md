# 🚀 Ngrok Quick Start - 5 Minutes Setup

## ✅ **What I Just Fixed**

Your frontend now **automatically detects** if it's running through ngrok or locally!
- ✅ Local access: Uses `http://127.0.0.1:8010`
- ✅ Ngrok access: Uses same domain automatically
- ✅ **No manual changes needed!**

---

## 📋 **Complete Setup - Copy & Paste**

### **1. Install ngrok** (One-time only)
```bash
brew install ngrok
```

### **2. Open 3 Terminals and Run:**

**Terminal 1:**
```bash
cd /Users/himanshumacpro24/Development/pixel-sprite-generator
./start_webui.sh
```
⏱️ Wait for: `Running on local URL: http://127.0.0.1:7860`

**Terminal 2:**
```bash
cd /Users/himanshumacpro24/Development/pixel-sprite-generator
./start_backend.sh
```
⏱️ Wait for: `Uvicorn running on http://0.0.0.0:8010`

**Terminal 3:**
```bash
ngrok http 8010
```

### **3. Get Your Public URL**

Look for this in Terminal 3:
```
Forwarding   https://abc-123-xyz.ngrok-free.app -> http://localhost:8010
```

**Copy that URL** → Share it with anyone!

---

## 🎯 **That's It! You're Live!**

✅ Anyone with the URL can:
- Generate pixel sprites
- Use Icon mode, Character mode, Alive mode
- Download all generated images
- Access from anywhere in the world

✅ The frontend automatically works:
- Local testing: Still works at `http://127.0.0.1:8010`
- Ngrok sharing: Automatically uses ngrok domain
- **No code changes needed!**

---

## 📱 **Share Your Link**

Send this to your friends/team:
```
https://your-actual-ngrok-url.ngrok-free.app
```

They'll see your Pixel Sprite Generator and can generate sprites immediately!

---

## ⚠️ **Important Notes**

### **Keep Everything Running:**
- Don't close any of the 3 terminal windows
- Keep your Mac awake (System Settings → Energy → Prevent sleep)
- All 3 services must stay running

### **Free Ngrok Limitations:**
- URL changes every time you restart ngrok
- 2-hour session timeout (just restart ngrok)
- Bandwidth limits (usually fine for small teams)

### **Performance:**
- Generation happens on **YOUR Mac**
- Your GPU/CPU does all the work
- Users just see the interface through ngrok

---

## 🔒 **Optional: Add Password Protection**

If you want to add a password:
```bash
# Instead of: ngrok http 8010
# Use:
ngrok http 8010 --basic-auth="username:password"
```

Example:
```bash
ngrok http 8010 --basic-auth="admin:mysecretpass123"
```

Users will need to enter username/password to access.

---

## 🛑 **To Stop Everything**

Press `Ctrl+C` in each terminal window (3 times total)

---

## 🔄 **To Restart**

Just run the 3 commands again:
1. `./start_webui.sh`
2. `./start_backend.sh`
3. `ngrok http 8010`

The ngrok URL will be different each time (unless you have a paid plan).

---

## 💡 **Pro Tips**

1. **Get a free ngrok account** at https://ngrok.com
   - Longer session times
   - Custom domains (paid plans)
   - Better bandwidth

2. **Test locally first**
   - Go to `http://127.0.0.1:8010`
   - Generate a test sprite
   - Make sure everything works
   - Then start ngrok

3. **Monitor resource usage**
   - Open Activity Monitor (Mac)
   - Watch CPU/Memory usage
   - More users = more load on your Mac

4. **For long-term sharing**
   - Consider upgrading to ngrok paid plan ($8/month)
   - Get permanent URL that doesn't change
   - Better for teams

---

## ✨ **Example Session**

```bash
# Terminal 1
$ ./start_webui.sh
Loading model...
Running on local URL: http://127.0.0.1:7860 ✅

# Terminal 2
$ ./start_backend.sh
INFO: Uvicorn running on http://0.0.0.0:8010 ✅

# Terminal 3
$ ngrok http 8010
Forwarding: https://abc-123-xyz.ngrok-free.app ✅
```

**Share**: `https://abc-123-xyz.ngrok-free.app`

**Done!** 🎉

---

## 🐛 **Troubleshooting**

### **Problem: "ngrok command not found"**
```bash
brew install ngrok
```

### **Problem: "Connection refused"**
- Make sure WebUI and Backend are running first
- Check both show "Running" messages
- Wait 30 seconds after starting before using ngrok

### **Problem: "Blank page on ngrok URL"**
- Check all 3 terminals are running
- Check browser console (F12) for errors
- Try incognito/private browsing mode
- Clear browser cache

### **Problem: "Too many requests"**
- Free ngrok has rate limits
- Upgrade to paid plan
- Or ask users to wait between generations

### **Problem: "Session timeout after 2 hours"**
- Free ngrok limitation
- Just restart ngrok (Terminal 3)
- Get new URL and share again
- Or upgrade to paid plan

---

## 📚 **More Information**

- Full guide: `NGROK_SETUP.md`
- Windows setup: `COPY_TO_NEW_PC.md`
- Model info: `MODELS_INFO.md`
- Icon mode: `ICON_MODE_ADDED.md`

---

## ✅ **Checklist Before Sharing**

- [ ] WebUI running and showing "Running on local URL"
- [ ] Backend running and showing "Uvicorn running"
- [ ] Ngrok running and showing forwarding URL
- [ ] Tested locally at http://127.0.0.1:8010
- [ ] Generated test sprite successfully
- [ ] Copied ngrok URL
- [ ] Mac won't sleep (checked Energy settings)
- [ ] Ready to share! 🚀

