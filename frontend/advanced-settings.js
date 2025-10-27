// Advanced Settings Module
// Handles loading, saving, and applying advanced configuration

const AdvancedSettings = {
    defaults: {
        baseModel: '',
        cfgScale: 7.0,
        steps: 25,
        sampler: 'DPM++ 2M Karras',
        bgRemovalMethod: 'rembg',
        rembgAggressiveness: 75,
        rembgModel: 'u2net',
        outlinePreservation: 3,
        pixelArtSize: 64,
        paletteSize: 16,
        forceChromakey: false,
        promptSuffix: 'high quality, sharp pixels, clean edges, vibrant colors',
        defaultNegative: 'blurry, low quality, jpeg artifacts, watermark, text, signature, realistic, photograph'
    },

    init() {
        this.loadSettings();
        this.loadAvailableModels();
        this.attachEventListeners();
    },

    loadSettings() {
        const saved = localStorage.getItem('pearlPixelSettings');
        const settings = saved ? JSON.parse(saved) : this.defaults;
        
        // Apply to UI
        document.getElementById('advCfgScale').value = settings.cfgScale;
        document.getElementById('advSteps').value = settings.steps;
        document.getElementById('advSampler').value = settings.sampler;
        document.getElementById('bgRemovalMethod').value = settings.bgRemovalMethod;
        document.getElementById('rembgAggressiveness').value = settings.rembgAggressiveness;
        document.getElementById('rembgModel').value = settings.rembgModel;
        document.getElementById('outlinePreservation').value = settings.outlinePreservation;
        document.getElementById('pixelArtSize').value = settings.pixelArtSize;
        document.getElementById('paletteSize').value = settings.paletteSize;
        document.getElementById('forceChromakey').checked = settings.forceChromakey;
        document.getElementById('promptSuffix').value = settings.promptSuffix;
        document.getElementById('defaultNegative').value = settings.defaultNegative;

        console.log('[Settings] Loaded:', settings);
    },

    async loadAvailableModels() {
        try {
            const response = await fetch(`${API_BASE}/models`);
            const data = await response.json();
            
            const samplerSelect = document.getElementById('advSampler');
            const saved = this.getCurrentSettings();

            if (Array.isArray(data.samplers) && samplerSelect) {
                samplerSelect.innerHTML = '';
                data.samplers.forEach(sampler => {
                    const option = document.createElement('option');
                    option.value = sampler;
                    option.textContent = sampler;
                    samplerSelect.appendChild(option);
                });
                samplerSelect.value = saved.sampler || 'DPM++ 2M Karras';
            }
        } catch (error) {
            console.error('[Settings] Failed to load models:', error);
        }
    },

    getCurrentSettings() {
        const saved = localStorage.getItem('pearlPixelSettings');
        return saved ? JSON.parse(saved) : this.defaults;
    },

    saveSettings() {
        const settings = {
            cfgScale: parseFloat(document.getElementById('advCfgScale').value),
            steps: parseInt(document.getElementById('advSteps').value),
            sampler: document.getElementById('advSampler').value,
            bgRemovalMethod: document.getElementById('bgRemovalMethod').value,
            rembgAggressiveness: parseInt(document.getElementById('rembgAggressiveness').value),
            rembgModel: document.getElementById('rembgModel').value,
            outlinePreservation: parseInt(document.getElementById('outlinePreservation').value),
            pixelArtSize: parseInt(document.getElementById('pixelArtSize').value),
            paletteSize: parseInt(document.getElementById('paletteSize').value),
            forceChromakey: document.getElementById('forceChromakey').checked,
            promptSuffix: document.getElementById('promptSuffix').value,
            defaultNegative: document.getElementById('defaultNegative').value
        };

        localStorage.setItem('pearlPixelSettings', JSON.stringify(settings));
        console.log('[Settings] Saved:', settings);
        
        // Show success feedback
        const btn = document.getElementById('saveSettings');
        const original = btn.textContent;
        btn.textContent = '✓ Saved!';
        btn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
        
        setTimeout(() => {
            btn.textContent = original;
            btn.style.background = '';
        }, 2000);
    },

    resetSettings() {
        if (confirm('Reset all settings to defaults?')) {
            localStorage.removeItem('pearlPixelSettings');
            this.loadSettings();
            console.log('[Settings] Reset to defaults');
            
            // Show feedback
            const btn = document.getElementById('resetSettings');
            const original = btn.textContent;
            btn.textContent = '✓ Reset!';
            
            setTimeout(() => {
                btn.textContent = original;
            }, 2000);
        }
    },

    applyToGenerationParams(params) {
        const settings = this.getCurrentSettings();
        
        // Apply generation settings
        if (settings.cfgScale) params.cfg_scale = settings.cfgScale;
        if (settings.steps) params.steps = settings.steps;
        if (settings.sampler) params.sampler = settings.sampler;
        
        // Apply background removal settings
        if (settings.bgRemovalMethod) params.bg_removal_method = settings.bgRemovalMethod;
        if (settings.rembgAggressiveness) params.rembg_aggressiveness = settings.rembgAggressiveness;
        if (settings.rembgModel) params.rembg_model = settings.rembgModel;
        if (settings.outlinePreservation) params.outline_preservation = settings.outlinePreservation;
        if (settings.pixelArtSize) params.pixel_art_size = settings.pixelArtSize;
        if (settings.paletteSize) params.palette_size = settings.paletteSize;
        if (settings.forceChromakey) params.force_chromakey = settings.forceChromakey;
        
        // Apply prompt modifications
        if (settings.promptSuffix) {
            params.prompt = `${params.prompt}, ${settings.promptSuffix}`;
        }
        
        if (!params.negative_prompt && settings.defaultNegative) {
            params.negative_prompt = settings.defaultNegative;
        }
        
        console.log('[Settings] Applied to generation:', params);
        return params;
    },

    attachEventListeners() {
        document.getElementById('saveSettings')?.addEventListener('click', () => {
            this.saveSettings();
        });

        document.getElementById('resetSettings')?.addEventListener('click', () => {
            this.resetSettings();
        });
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => AdvancedSettings.init());
} else {
    AdvancedSettings.init();
}

// Export for use in main app
window.AdvancedSettings = AdvancedSettings;

