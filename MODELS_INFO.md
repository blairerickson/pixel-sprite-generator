# Models Being Used in Pixel Sprite Generator

## 📦 Current Model Setup

### **Base Model (Main Model)**
**Model**: `allInOnePixelModel_v1.ckpt` (2.0 GB)
- **Location**: `stable-diffusion-webui/models/Stable-diffusion/`
- **Source**: [CivitAI - All-in-One Pixel Model](https://civitai.com/models/34/all-in-one-pixel-model)
- **Description**: Specialized model trained for pixel art generation
- **Best For**: Character sprites, pixel art items, retro game graphics

**Configured as**: `pixelArtDiffusionXL_spriteShaper.safetensors` in `config.yaml` (line 10)
- ⚠️ **Note**: The config references a different filename than what you actually have downloaded
- **Recommendation**: Either rename your model or update the config to match

### **LoRA Model (Style Enhancement)**
**Model**: `pixel-art-xl-v1.1.safetensors` (163 MB)
- **Location**: `stable-diffusion-webui/models/Lora/`
- **Source**: [CivitAI - Pixel Art XL](https://civitai.com/models/120096/pixel-art-xl)
- **Description**: LoRA model that enhances pixel art style and adds sprite-specific characteristics
- **Weight**: Applied on top of the base model for better pixel art results

---

## 🎨 How The Models Work Together

1. **Base Model** (`allInOnePixelModel_v1.ckpt`) provides the foundation for pixel art generation
2. **LoRA Model** (`pixel-art-xl-v1.1.safetensors`) refines the style and adds sprite-specific features
3. Together they create high-quality pixel art sprites optimized for games

---

## 🔧 Model Configuration in config.yaml

The backend is configured to look for these models (lines 9-11):
```yaml
models:
  base_model: "pixelArtDiffusionXL_spriteShaper.safetensors"
  alternative_models: []
```

### ⚠️ **Important Note**
There's a **filename mismatch**:
- **Config expects**: `pixelArtDiffusionXL_spriteShaper.safetensors`
- **You actually have**: `allInOnePixelModel_v1.ckpt`

**To Fix This**, you have two options:

### Option 1: Update the Config (Recommended)
```bash
# Edit backend/config.yaml line 10 to:
base_model: "allInOnePixelModel_v1.ckpt"
```

### Option 2: Rename the Model File
```bash
cd stable-diffusion-webui/models/Stable-diffusion/
mv allInOnePixelModel_v1.ckpt pixelArtDiffusionXL_spriteShaper.safetensors
```

---

## 📊 Model Presets

The system uses different presets for different types of generation:

### 1. **Character Sprite** (512x512)
- For full character sprites
- Prompt template: `"{description}, pixel art, sprite, full body, clean linework, vibrant colors, solid color background"`

### 2. **Icon Sprite** (256x256) ✨ NEW!
- For game items, UI icons
- Prompt template: `"{description}, pixel art icon, game item, centered, clean design, detailed, vibrant colors, solid color background"`
- **Smaller size** = Faster generation
- **Optimized** for items, not characters

### 3. **Animation Frames** (768x256)
- For sprite animations
- Multiple poses and frames

---

## 🚀 Model Capabilities

With these models, you can generate:
- ✅ Character sprites (heroes, NPCs, enemies)
- ✅ Game items and icons (weapons, potions, treasures)
- ✅ Pixel art UI elements
- ✅ Animation frames and sprite sheets
- ✅ Retro game-style graphics
- ✅ 8-bit and 16-bit style artwork

---

## 🔗 Additional LoRA Models (Configured but Not Downloaded)

The config.yaml also references these LoRA models (lines 14-30):
- `pixel_character_sprite_illustrious.safetensors`
- `2DPixelToolkit.safetensors`
- `ragnarok_online_sprite_illustrious.safetensors`

These are **optional enhancements** you can download from CivitAI if you want more style variations.

---

## 💡 Current Status

✅ **Base Model**: Downloaded and ready (allInOnePixelModel_v1.ckpt)
✅ **LoRA Model**: Downloaded and ready (pixel-art-xl-v1.1.safetensors)
⚠️ **Config Mismatch**: Needs to be fixed (see options above)
✅ **System**: Ready to generate pixel art!

