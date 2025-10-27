# Web Interface

Two versions available:

## 🎨 Demo Mode (No Backend Required)

**Just want to see the interface?**

1. Open `demo.html` in your browser
2. Explore the UI with mock data
3. No setup needed!

```bash
# Navigate to this folder and open:
demo.html
```

## 🚀 Full Mode (With Backend)

**Ready to generate real sprites?**

1. Make sure the backend is running:
   ```bash
   cd ../backend
   python api.py
   ```

2. Serve the frontend:
   ```bash
   python -m http.server 8080
   ```

3. Visit: **http://localhost:8080**

Or simply open `index.html` directly in your browser.

## ✨ Features

### Generation Panel
- Enter prompts for sprites
- Choose presets (Character, Animation, Icon)
- Select LoRA models
- Adjust dimensions and batch size
- Enable background removal
- Auto sprite extraction

### Upload Panel
- Drag & drop existing sprite sheets
- Process and extract sprites
- Remove backgrounds from images

### Results Panel
- View generated sprites
- Download individual files
- See sprite dimensions

### Job History
- Track all generations
- Click to view previous results
- See status (completed/failed)

## 🎯 Example Prompts

Try these in the prompt field:

**Characters:**
```
pixel art knight warrior, blue armor, sword and shield
pixel art mage wizard, purple robes, staff, casting spell
pixel art archer elf, green cloak, bow
```

**Enemies:**
```
pixel art goblin enemy, green skin, dagger
pixel art dragon, red scales, breathing fire
pixel art skeleton warrior, bones, glowing eyes
```

**Items:**
```
pixel art sword, iron blade, leather handle
pixel art health potion, red liquid, glass bottle
pixel art treasure chest, wooden, gold trim
```

## 🔧 Configuration

The UI automatically:
- ✅ Detects backend status
- ✅ Loads available models
- ✅ Populates presets
- ✅ Tracks job progress
- ✅ Displays results

## 📱 Screenshots

The interface includes:
- Dark theme for comfortable viewing
- Responsive grid layout
- Real-time progress bars
- Beautiful gradient buttons
- Transparent background preview

## 🐛 Troubleshooting

**"Connection Failed" message?**
- Make sure backend is running on port 8000
- Check `backend/api.py` is started
- Verify Stable Diffusion backend is running

**Can't select LoRAs?**
- LoRAs are auto-loaded from backend
- Check models are in correct folders
- Restart backend after adding models

**Slow generation?**
- First generation loads models (30-60s)
- Subsequent generations much faster
- Check GPU is being used

