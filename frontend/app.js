window.triggerFrameExtraction = async function(jobId, imageIndex) {
    try {
        showStatus('Extracting frames...', 'info');
        const response = await fetch(`${API_BASE}/process-image-from-job`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: jobId, image_index: imageIndex })
        });
        const data = await response.json();
        if (data.result) {
            handleResults(data.result, jobId);
            showStatus('Frames extracted!', 'success');
        } else {
            showStatus('Frame extraction failed', 'error');
        }
    } catch (error) {
        console.error('Failed to extract frames:', error);
        showStatus('Failed to extract frames', 'error');
    }
};
// Pearl's Pixel Studio - Main Application
const API_BASE = 'http://127.0.0.1:8010';

// State
const state = {
    jobId: null,
    pollInterval: null,
    frames: [],
    currentFrame: 0,
    playing: false,
    fps: 12,
    playTimer: null,
    currentMode: 'character',
    qaRecords: []
};

const backgroundState = {
    current: '/assets/background.png',
    currentPalette: [],
    gallery: []
};

async function setGalleryBackground(imageUrl, filename) {
    try {
        const payload = {
            url: imageUrl,
            name: filename,
            source: 'gallery',
        };

        const response = await fetch(`${API_BASE}/backgrounds/from-gallery`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error('Failed to set background');

        const data = await response.json();
        backgroundState.current = data.url;
        backgroundState.currentPalette = data.palette || [];
        updateBackgroundImage(data.url);
        applyPaletteToDocument(data.palette);

        showStatus('Background updated', 'success');
    } catch (error) {
        console.error('Failed to set gallery background:', error);
        showStatus('Background update failed', 'error');
    }
}

const ambientState = {
    enabled: false,
    audio: null
};

const mascotState = {
    elements: [],
    lastX: 0,
    lastY: 0
};

function applyPaletteToDocument(palette = []) {
    const root = document.documentElement;
    if (!palette.length) {
        root.style.removeProperty('--accent-1');
        root.style.removeProperty('--accent-2');
        root.style.removeProperty('--accent-3');
        root.style.removeProperty('--accent-4');
        root.style.removeProperty('--amber');
        return;
    }
    const [accent1, accent2, accent3, accent4, amber] = palette;
    if (accent1) root.style.setProperty('--accent-1', accent1);
    if (accent2) root.style.setProperty('--accent-2', accent2);
    if (accent3) root.style.setProperty('--accent-3', accent3);
    if (accent4) root.style.setProperty('--accent-4', accent4);
    if (amber) root.style.setProperty('--amber', amber);
}

let hasInitializedBackground = false;

// Elements
const el = {};

// Mode presets mapping
const MODE_PRESETS = {
    character: 'character_sprite',
    alive: 'character_sprite',
    background: 'character_sprite'
};

// ============================================================
// Prompt Management
// ============================================================

function loadRandomPrompt() {
    if (!el.prompt) return;
    // Always load random prompt on fresh page load
    if (!el.prompt.value.trim() || el.prompt.value === el.prompt.getAttribute('placeholder')) {
        if (window.StarterPrompts && window.StarterPrompts.getRandomPrompt) {
            const randomPrompt = window.StarterPrompts.getRandomPrompt();
            el.prompt.value = randomPrompt;
            el.prompt.setAttribute('data-loaded-random', 'true');
        }
    }
}

window.refreshRandomPrompt = function() {
    if (el.prompt && window.StarterPrompts) {
        el.prompt.value = window.StarterPrompts.getRandomPrompt();
        el.prompt.focus();
    }
}

// ============================================================
// Initialization
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    cacheElements();
    setupEventListeners();
    checkHealth();
    loadModels();
    loadHistory();
    initCanvas();
    observeScroll();
    fetchBackgroundGallery();
    createPixelSnowflakes();
    restoreGalleryState();
    loadRandomPrompt();
});

function cacheElements() {
    // Core
    el.hero = document.getElementById('hero');
    el.statusBadge = document.getElementById('statusBadge');
    el.statusText = document.getElementById('statusText');
    
    // Canvas
    el.canvas = document.getElementById('mainCanvas');
    el.canvasOverlay = document.getElementById('canvasOverlay');
    el.canvasStage = document.getElementById('canvasStage');
    el.playbackControls = document.getElementById('playbackControls');
    el.playBtn = document.getElementById('playBtn');
    el.frameSlider = document.getElementById('frameSlider');
    el.frameLabel = document.getElementById('frameLabel');
    el.fpsSlider = document.getElementById('fpsSlider');
    el.fpsLabel = document.getElementById('fpsLabel');
    
    // Form
    el.form = document.getElementById('generateForm');
    el.prompt = document.getElementById('prompt');
    el.negative = document.getElementById('negativePrompt');
    el.lora = document.getElementById('lora');
    el.width = document.getElementById('width');
    el.height = document.getElementById('height');
    el.batchSize = document.getElementById('batchSize');
    el.seed = document.getElementById('seed');
    el.removeBg = document.getElementById('removeBackground');
    el.extractSprites = document.getElementById('extractSprites');
    el.generateBtn = document.getElementById('generateBtn');
    el.progressBar = document.getElementById('progressBar');
    el.progressFill = document.getElementById('progressFill');
    el.progressText = document.getElementById('progressText');
    el.preset = document.getElementById('preset');
    
    // Animation Controls
    el.animationControls = document.getElementById('animationControls');
    el.animationType = document.getElementById('animationType');
    el.directions = document.getElementById('directions');
    el.guidanceMethod = document.getElementById('guidanceMethod');
    el.generateReference = document.getElementById('generateReference');
    
    // Tabs & Gallery
    el.tabs = document.querySelectorAll('.tab');
    el.tabContents = document.querySelectorAll('.tab-content');
    el.gallery = document.getElementById('gallery');
    el.galleryViewerClose = document.getElementById('galleryViewerClose');
    el.galleryViewer = document.getElementById('galleryViewer');
    el.galleryViewerImage = document.getElementById('galleryViewerImage');
    el.galleryViewerMeta = document.getElementById('galleryViewerMeta');
    el.galleryViewerVariants = document.getElementById('galleryViewerVariants');
    el.galleryViewerFilmstrip = document.getElementById('galleryViewerFilmstrip');
    el.galleryViewerPrev = document.getElementById('galleryViewerPrev');
    el.galleryViewerNext = document.getElementById('galleryViewerNext');
    el.galleryViewerCounter = document.getElementById('galleryViewerCounter');
    el.galleryViewerFps = document.getElementById('galleryViewerFps');
    el.galleryViewerFpsValue = document.getElementById('galleryViewerFpsValue');
    el.galleryViewerPlayToggle = document.getElementById('galleryViewerPlay');
    el.galleryViewerZoomButtons = document.querySelectorAll('.gallery-viewer__zoom-btn');
    el.qaPanel = document.getElementById('qaPanel');
    el.qaList = document.getElementById('qaList');
    el.filmstrip = document.getElementById('filmstrip');
    el.toggleViewBtn = document.getElementById('toggleViewBtn');
    
    // Import
    el.dropzone = document.getElementById('dropzone');
    el.fileInput = document.getElementById('fileInput');
    el.uploadRemoveBg = document.getElementById('uploadRemoveBg');
    el.uploadExtract = document.getElementById('uploadExtract');
    
    // History
    el.historyList = document.getElementById('historyList');
    el.refreshHistory = document.getElementById('refreshHistory');
    
    el.ctx = el.canvas.getContext('2d');

    // Background modal controls
    el.backgroundStage = document.getElementById('backgroundStage');
    el.backgroundImage = document.getElementById('backgroundImage');
    el.newBackgroundBtn = document.getElementById('newBackgroundBtn');
    el.backgroundModal = document.getElementById('backgroundModal');
    el.backgroundModalClose = document.getElementById('backgroundModalClose');
    el.backgroundModalCancel = document.getElementById('backgroundModalCancel');
    el.backgroundModalCreate = document.getElementById('backgroundModalCreate');
    el.backgroundModalStatus = document.getElementById('backgroundModalStatus');
    el.backgroundPrompt = document.getElementById('backgroundPrompt');
    el.backgroundGallery = document.getElementById('backgroundGallery');
    el.backgroundGalleryList = document.getElementById('backgroundGalleryList');
    el.backgroundGalleryClose = document.getElementById('backgroundGalleryClose');
    el.openBackgroundGallery = document.getElementById('openBackgroundGallery');
    el.resetBackgroundBtn = document.getElementById('resetBackgroundBtn');

    // Accessibility controls
    el.accessibilityBtn = document.getElementById('accessibilityBtn');
    el.accessibilityPanel = document.getElementById('accessibilityPanel');
    el.accessibilityClose = document.getElementById('accessibilityClose');
    el.largeTextToggle = document.getElementById('largeTextToggle');
    el.reduceMotionToggle = document.getElementById('reduceMotionToggle');

    // Stage controls
    el.gridToggle = document.getElementById('gridToggle');
    el.onionToggle = document.getElementById('onionToggle');
    el.transparencyToggle = document.getElementById('transparencyToggle');
    el.prevFrameBtn = document.getElementById('prevFrameBtn');
    el.nextFrameBtn = document.getElementById('nextFrameBtn');
    el.loopToggle = document.getElementById('loopToggle');
    el.stageFilmstrip = document.getElementById('stageFilmstrip');
    el.filmstripScroll = document.getElementById('filmstripScroll');
    el.zoomLevelLabel = document.getElementById('zoomLevelLabel');
    el.zoomInBtn = document.getElementById('zoomInBtn');
    el.zoomOutBtn = document.getElementById('zoomOutBtn');

    // Prompt helpers
    el.promptTemplates = document.querySelectorAll('.prompt-chip');
    el.assistantCues = document.getElementById('assistantCues');
    el.ambientSoundBtn = document.getElementById('ambientSoundBtn');
    mascotState.elements = Array.from(document.querySelectorAll('.mascot'));
}

// ============================================================
// Core Functions (Defined Early)
// ============================================================

function updatePlaybackControls() {
    if (!el.playbackControls) return;
    
    const hasFrames = state.frames.length > 0;
    el.playbackControls.style.display = hasFrames ? 'grid' : 'none';
    
    if (hasFrames) {
        el.frameSlider.max = state.frames.length - 1;
        el.frameSlider.value = state.currentFrame;
        updateFrameDisplay();
    }
}

function showStatus(message, type = 'info') {
    if (!el.statusText) return;
    
    el.statusText.textContent = message;
    
    // Update status badge color based on type
    if (el.statusBadge) {
        el.statusBadge.className = 'hero__status';
        if (type === 'success') {
            el.statusBadge.classList.add('success');
        } else if (type === 'error') {
            el.statusBadge.classList.add('error');
        } else if (type === 'warning') {
            el.statusBadge.classList.add('warning');
        }
    }
    
    // Auto-hide after 3 seconds for non-error messages
    if (type !== 'error') {
        setTimeout(() => {
            if (el.statusText) {
                el.statusText.textContent = 'Ready';
                if (el.statusBadge) {
                    el.statusBadge.className = 'hero__status';
                }
            }
        }, 3000);
    }
}

function updateFrameDisplay() {
    if (!el.frameLabel) return;
    
    const current = state.currentFrame + 1;
    const total = state.frames.length;
    el.frameLabel.textContent = `${current} / ${total}`;
}

async function drawFrame() {
    if (!el.canvas || !el.ctx) return;
    const ctx = el.ctx;
    ctx.clearRect(0, 0, el.canvas.width, el.canvas.height);

    if (!state.frames.length) {
        drawStageBackground();
        return;
    }

    const frame = state.frames[state.currentFrame];
    if (!frame || !frame.url) {
        drawStageBackground();
        return;
    }

    try {
        const img = await loadImage(frame.url);
        const scale = Math.min(
            el.canvas.width / img.width,
            el.canvas.height / img.height
        ) * stageState.zoom;
        const w = img.width * scale;
        const h = img.height * scale;
        const x = (el.canvas.width - w) / 2;
        const y = (el.canvas.height - h) / 2;

        // Draw background based on mode
        drawStageBackground();

        ctx.save();
        ctx.globalCompositeOperation = 'source-over';
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(img, x, y, w, h);
        ctx.restore();

        if (stageState.onionSkin && stageCache.onionFrame) {
            ctx.drawImage(stageCache.onionFrame, 0, 0);
        }

        el.canvasOverlay?.classList.add('hidden');
        if (renderStageFilmstrip) renderStageFilmstrip();
        if (refreshAssistantCues) refreshAssistantCues();
    } catch (error) {
        console.error('Failed to draw frame:', error);
    }
}

function drawStageBackground() {
    if (!el.canvas || !el.ctx) return;
    const ctx = el.ctx;
    
    // ALWAYS clear first to ensure transparency
    ctx.clearRect(0, 0, el.canvas.width, el.canvas.height);
    
    // Only draw background if NOT in clear mode
    switch (stageState.backgroundMode) {
        case 'clear':
            // Fully transparent - nothing drawn (platform shows through)
            // This is the default and preferred state
            break;
        case 'grid':
            // Checkerboard pattern for transparency preview
            drawCheckerboard();
            break;
        case 'paper':
            // Solid white background for export preview
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, el.canvas.width, el.canvas.height);
            break;
        default:
            // Fallback to clear
            break;
    }
}

function loadImage(src) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = src;
    });
}

// ============================================================
// Playback Controls
// ============================================================

function togglePlayback() {
    state.playing ? stopPlayback() : startPlayback();
    refreshAssistantCues();
}

function startPlayback() {
    if (!state.frames.length) return;
    state.playing = true;
    updatePlayButton();
    
    state.playTimer = setInterval(() => {
        if (!stageState.loop && state.currentFrame === state.frames.length - 1) {
            stopPlayback();
            return;
        }
        state.currentFrame = (state.currentFrame + 1) % state.frames.length;
        el.frameSlider.value = state.currentFrame;
        updateFrameDisplay();
        drawFrame();
    }, 1000 / state.fps);
}

function stopPlayback() {
    state.playing = false;
    updatePlayButton();
    if (state.playTimer) {
        clearInterval(state.playTimer);
        state.playTimer = null;
    }
}

function updatePlayButton() {
    if (!el.playBtn) return;
    el.playBtn.classList.add('control-btn--play');
    el.playBtn.classList.toggle('control-btn--pause', state.playing);
}

function updateFrameDisplay() {
    const total = state.frames.length;
    el.frameLabel.textContent = total ? `Frame ${state.currentFrame + 1} / ${total}` : 'No frames';
}

// ============================================================
// Generation
// ============================================================

// FIXED #21: Clear sprite display for new generation
function clearSpriteDisplay() {
    if (!el.canvas || !el.ctx) return;
    
    // Clear canvas
    el.ctx.clearRect(0, 0, el.canvas.width, el.canvas.height);
    
    // FIXED #27: Hide overlay completely during generation (let swirling pixels show)
    if (el.canvasOverlay) {
        el.canvasOverlay.classList.add('hidden'); // Hide it, don't show gray box
    }
    
    // Clear frames
    state.frames = [];
    state.currentFrame = 0;
    updatePlaybackControls();
}

async function handleGenerate(e) {
    e.preventDefault();
    
    // FIXED #21: Clear sprite box and show assembly animation
    clearSpriteDisplay();
    
    const isAnimationMode = state.currentMode === 'animation';
    const isAliveMode = state.currentMode === 'alive';
    
    let payload;
    let endpoint;
    
    if (isAnimationMode) {
        // Animation generation
        const directions = el.directions.value === '4dir' ? 
            ['south', 'west', 'east', 'north'] : 
            ['south', 'southwest', 'west', 'northwest', 'north', 'northeast', 'east', 'southeast'];
        
        const storyboardSettings = {
            use_previous_seed: document.getElementById('usePrevSeedToggle')?.checked || false,
            motion_preset: document.getElementById('motionPreset')?.value || 'auto',
            reference_preview: document.getElementById('referencePreviewToggle')?.checked || false,
            requested_frame_count: parseInt(el.frameSlider?.max, 10) + 1 || null,
            pipeline_mode: document.getElementById('motionPipelineMode')?.value || 'disabled'
        };

        payload = {
            character_description: el.prompt.value,
            directions: directions,
            animation_type: el.animationType.value,
            guidance_method: el.guidanceMethod.value,
            frame_count: null, // Auto
            generate_reference_first: el.generateReference.checked,
            style_lora: el.lora.value || null,
            lora_weight: null,
            width: parseInt(el.width.value) || null,
            height: parseInt(el.height.value) || null,
            steps: null,
            cfg_scale: null,
            seed: parseInt(el.seed.value),
            batch_size: 1,
            remove_background: el.removeBg.checked, // FIX: Add background removal for animations
            process_sprites: el.extractSprites.checked, // FIX: Add sprite processing
            storyboard_settings: storyboardSettings
        };
        endpoint = '/generate-animation';
    } else if (isAliveMode) {
        payload = {
            prompt: el.prompt.value,
            negative_prompt: el.negative.value || null,
            preset: el.preset.value,
            lora: el.lora.value || null,
            width: parseInt(el.width.value) || null,
            height: parseInt(el.height.value) || null,
            seed: parseInt(el.seed.value),
            remove_background: true,
            process_sprites: true,
            batch_size: 1
        };
        endpoint = '/generate-alive-sequence';
    } else {
        // Regular generation
        payload = {
            prompt: el.prompt.value,
            negative_prompt: el.negative.value || null,
            preset: el.preset.value,
            lora: el.lora.value || null,
            width: parseInt(el.width.value) || null,
            height: parseInt(el.height.value) || null,
            batch_size: parseInt(el.batchSize.value),
            seed: parseInt(el.seed.value),
            remove_background: el.removeBg.checked,
            process_sprites: el.extractSprites.checked
        };
        endpoint = '/generate';
    }
    
    // Apply advanced settings if available
    if (window.AdvancedSettings) {
        payload = window.AdvancedSettings.applyToGenerationParams(payload);
        if (isAliveMode) {
            payload.remove_background = true;
            payload.process_sprites = true;
        }
    }
    
    lockGenerate(true);
    const progressMessage = isAnimationMode
        ? 'Queuing animation generation...'
        : isAliveMode
            ? 'Preparing Alive sequence...'
            : 'Queuing generation...';
    showProgress(progressMessage);
    
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) throw new Error('Generation request failed');
        
        const data = await response.json();
        state.jobId = data.job_id;
        startPolling();
    } catch (error) {
        console.error(error);
        alert(`Generation failed: ${error.message}`);
        lockGenerate(false);
        hideProgress();
    }
}

function lockGenerate(locked) {
    el.generateBtn.disabled = locked;
    const label = el.generateBtn.querySelector('.btn-label');
    if (label) {
        label.textContent = locked ? label.dataset.loading : label.dataset.idle;
    }
}

function showProgress(message) {
    if (!el.progressBar || !el.progressFill || !el.progressText) return;
    el.progressBar.style.display = 'block';
    el.progressFill.style.width = '10%';
    el.progressText.textContent = message;
    startSummoningEffect();
}

function updateProgress(percent, message) {
    if (!el.progressFill || !el.progressText) return;
    el.progressFill.style.width = `${Math.max(10, percent)}%`;
    el.progressText.textContent = message;
}

function hideProgress() {
    if (!el.progressBar) return;
    el.progressBar.style.display = 'none';
    stopSummoningEffect();
}

function startPolling() {
    if (state.pollInterval) clearInterval(state.pollInterval);
    
    state.pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/jobs/${state.jobId}`);
            const job = await response.json();
            
            updateProgress(job.progress * 100, job.message);
            
            if (job.status === 'completed') {
                clearInterval(state.pollInterval);
                lockGenerate(false);
                hideProgress();
                handleResults(job.result);
                loadHistory();
                minimizeHero();
            } else if (job.status === 'failed') {
                clearInterval(state.pollInterval);
                lockGenerate(false);
                hideProgress();
                alert(`Generation failed: ${job.error}`);
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 1000);
}

// ============================================================
// Results Handling
// ============================================================

function handleResults(result, jobId = state.jobId) {
    // Handle animation results
    if (result.animation_sequence) {
        handleAnimationResults(result);
        return;
    }

    if (result.alive_sequence) {
        handleAliveSequence(result.alive_sequence, jobId);
        return;
    }
    
    // Handle regular generation results
    if (!result || !result.images) return;

    // Switch to gallery tab
    switchTab('gallery');

    const newFrames = [];
    const qaRecords = result.qa ? [...result.qa] : [];

    // FIXED #1: Consolidate all images into single gallery entry
    let mainImagePath = null;
    let mainImageLabel = 'Generation';
    let allSpritesForFilmstrip = [];
    let childImagesForMenu = [];
    let mainQc = null;
    let firstImageIndex = 0;

    result.images.forEach((img, idx) => {
        // Build URLs for before/after comparison
        const originalUrl = img.original ? `${API_BASE}/download/${jobId}/${img.original.split(/[/\\]/).pop()}` : null;
        const processedUrl = img.processed ? `${API_BASE}/download/${jobId}/${img.processed.split(/[/\\]/).pop()}` : null;
        
        if (img.sprites && img.sprites.length > 0) {
            img.sprites.forEach((sprite, spriteIdx) => {
                const spriteVariants = sprite.variants?.map(variant => ({
                    ...variant,
                    url: variant.url?.startsWith('http') ? variant.url : `${API_BASE}${variant.url || ''}`,
                    preview_url: variant.preview_url?.startsWith('http') ? variant.preview_url : (variant.preview_url ? `${API_BASE}${variant.preview_url}` : null)
                })) || [];
                
                const spriteUrl = `${API_BASE}/download/${jobId}/${sprite.path.split(/[/\\]/).pop()}`;
                
                // First sprite is main, rest are children
                if (!mainImagePath) {
                    mainImagePath = sprite.path;
                    mainImageLabel = `Sprite ${new Date().toLocaleTimeString()}`;
                    mainQc = sprite.qc;
                    firstImageIndex = idx;
                }
                
                // Add to filmstrip
                allSpritesForFilmstrip.push({
                    url: spriteUrl,
                    label: `Sprite ${spriteIdx + 1}`,
                    size: sprite.size,
                    metadata: sprite
                });
                
                // Add to children (all except first)
                if (spriteIdx > 0 || idx > 0) {
                    childImagesForMenu.push({
                        url: spriteUrl,
                        label: `Sprite ${spriteIdx + 1}`,
                        size: sprite.size
                    });
                }

                newFrames.push({
                    url: spriteUrl,
                    size: sprite.size,
                    variants: spriteVariants
                });
                qaRecords.push({
                    type: 'sprite',
                    label: `Sprite ${spriteIdx + 1}`,
                    qc: sprite.qc || {},
                    originalUrl: originalUrl,
                    processedUrl: spriteUrl
                });
            });
        } else {
            const path = img.processed || img.original;
            if (path) {
                const baseVariants = img.variants?.map(variant => ({
                    ...variant,
                    url: variant.url?.startsWith('http') ? variant.url : `${API_BASE}${variant.url || ''}`,
                    preview_url: variant.preview_url?.startsWith('http') ? variant.preview_url : (variant.preview_url ? `${API_BASE}${variant.preview_url}` : null)
                })) || [];
                
                const sheetUrl = `${API_BASE}/download/${jobId}/${path.split(/[/\\]/).pop()}`;
                
                if (!mainImagePath) {
                    mainImagePath = path;
                    mainImageLabel = `Sheet ${new Date().toLocaleTimeString()}`;
                    mainQc = img.background_qc;
                    firstImageIndex = idx;
                }
                
                allSpritesForFilmstrip.push({
                    url: sheetUrl,
                    label: `Sheet ${idx + 1}`,
                    size: [512, 512]
                });

                newFrames.push({
                    url: sheetUrl,
                    size: [512, 512],
                    variants: baseVariants
                });
                qaRecords.push({
                    type: 'sheet',
                    label: `Sheet ${idx + 1}`,
                    qc: img.background_qc || {},
                    originalUrl: originalUrl,
                    processedUrl: processedUrl
                });
            }
        }
        if (img.sprite_qc) {
            qaRecords.push({
                type: 'extraction',
                label: `Sprite extraction ${idx + 1}`,
                qc: img.sprite_qc,
                originalUrl: originalUrl,
                processedUrl: processedUrl
            });
        }

        if (img.pixel_art) {
            // Add pixel art to filmstrip but not as separate entry
            const pixelUrl = `${API_BASE}/download/${jobId}/${img.pixel_art.path.split(/[/\\]/).pop()}`;
            allSpritesForFilmstrip.push({
                url: pixelUrl,
                label: `Pixel Art ${idx + 1}`,
                size: [512, 512]
            });
        }
    });
    
    // FIXED #1: Create ONLY ONE gallery entry with all images
    if (mainImagePath) {
        addToGallery(mainImagePath, mainImageLabel, jobId, mainQc, {
            imageIndex: firstImageIndex,
            filmstrip: allSpritesForFilmstrip,
            childImages: childImagesForMenu
        });
        
        // FIXED #22: Auto-display newly generated sprite in sprite box
        const firstSpriteUrl = allSpritesForFilmstrip[0]?.url || 
                               `${API_BASE}/download/${jobId}/${mainImagePath.split(/[/\\]/).pop()}`;
        setTimeout(() => {
            displayInStage(firstSpriteUrl);
        }, 300); // Small delay for dramatic reveal
    }

    state.frames = newFrames;
    state.qaRecords = qaRecords;
    renderQaPanel();

    if (state.frames.length > 0) {
        state.currentFrame = 0;
        el.frameSlider.max = state.frames.length - 1;
        el.frameSlider.value = 0;
        cacheOnionFrame(state.currentFrame);
        updateFrameDisplay();
        drawFrame();
        el.playbackControls.style.display = 'grid';
        renderStageFilmstrip();
        refreshAssistantCues();
    }
}

function handleAnimationResults(result) {
    const animation = result.animation_sequence;
    if (!animation || !animation.frames || animation.frames.length === 0) return;

    // Switch to gallery tab
    switchTab('gallery');

    const jobId = state.jobId;
    
    // FIX: Group frames by direction for stacked filmstrip display
    const framesByDirection = {};
    const allFrames = [];
    
    animation.frames.forEach((frame) => {
        // FIX: Proper URL construction - handle /output/ paths
        let frameUrl;
        if (frame.image_url?.startsWith('http')) {
            frameUrl = frame.image_url;
        } else if (frame.image_url) {
            // Backend returns /output/frame_xxx.png
            // Extract filename and serve from root
            const filename = frame.image_url.split('/').pop();
            frameUrl = `${API_BASE}/${filename}`;
        } else if (frame.path) {
            const filename = frame.path.split(/[/\\]/).pop();
            frameUrl = `${API_BASE}/${filename}`;
        } else {
            frameUrl = `${API_BASE}/frame_${frame.direction}_${frame.frame_index}.png`;
        }
        
        const frameData = {
            url: frameUrl,
            size: [512, 512],
            direction: frame.direction,
            frame_index: frame.frame_index,
            animation_type: animation.animation_type
        };
        
        // Group by direction
        if (!framesByDirection[frame.direction]) {
            framesByDirection[frame.direction] = [];
        }
        framesByDirection[frame.direction].push(frameData);
        allFrames.push(frameData);
    });

    // FIX: Only add to gallery if we have valid frames
    if (allFrames.length > 0 && allFrames[0].url) {
        // Create single gallery entry for the animation
        const firstFrame = allFrames[0];
        const filmstripFrames = allFrames.map((f, idx) => ({
            url: f.url,
            label: `${f.direction} ${f.frame_index + 1}`,
            metadata: f
        }));
        
        addToGallery(
            firstFrame.url,
            `${animation.animation_type || 'Animation'} - ${Object.keys(framesByDirection).length} directions`,
            jobId,
            null,
            {
                isAnimation: true,
                animationType: animation.animation_type,
                framesByDirection: framesByDirection,
                filmstrip: filmstripFrames,
                allFrames: allFrames
            }
        );
        
        // DEBUG: Log what we're passing to addToGallery
        console.log('Animation data:', {
            framesByDirection: Object.keys(framesByDirection),
            filmstripCount: filmstripFrames.length,
            totalFrames: allFrames.length
        });
        
        // Auto-display first frame
        setTimeout(() => {
            displayInStage(firstFrame.url);
        }, 300);
    }

    state.frames = allFrames;
    state.currentFrame = 0;
    updatePlaybackControls();

    if (allFrames.length > 0) {
        drawFrame();
    }

    // Show success message
    const frameCount = animation.frames.length;
    const directionCount = Object.keys(framesByDirection).length;
    showStatus(`Animation completed! ${frameCount} frames across ${directionCount} directions`, 'success');
}

function handleAliveSequence(sequence, jobId = null) {
    if (!sequence || !sequence.frames) return;

    switchTab('gallery');

    jobId = jobId || sequence.job_id;
    const spriteSheet = sequence.sprite_sheet;
    const newFrames = sequence.frames.map((frame, idx) => {
        const filename = frame.filename || frame.path || `frame_${idx}.png`;
        const resolvedFilename = filename.split(/[/\\]/).pop();
        const frameSize = frame.size || [frame.width || frame.frame_width || 128, frame.height || frame.frame_height || 128];
        const url = frame.url
            ? (frame.url.startsWith('http') ? frame.url : `${API_BASE}${frame.url}`)
            : `${API_BASE}/download/${jobId}/${resolvedFilename}`;
        return {
            url,
            size: frameSize,
            filename: resolvedFilename,
            index: idx
        };
    });

    state.frames = newFrames;
    state.currentFrame = 0;
    state.playing = false;
    updatePlaybackControls();
    drawFrame();

    const existingSection = document.querySelector('.alive-sequence');
    if (existingSection) existingSection.remove();

    const section = document.createElement('div');
    section.className = 'gallery-item alive-sequence';
    section.innerHTML = `
        <div class="alive-sequence__header">
            <h4>Alive! Sequence</h4>
            <span>${sequence.frames.length} frame${sequence.frames.length === 1 ? '' : 's'}</span>
        </div>
        <div class="alive-sequence__list"></div>
        <div class="alive-sequence__actions">
            <button type="button" class="alive-sequence__view-btn" data-sequence-id="${jobId}">View Options</button>
        </div>
        <div class="alive-sequence__menu" style="display: none;">
            ${spriteSheet ? '<button type="button" class="alive-sequence__download" data-type="sheet">Save Sprite Sheet</button>' : ''}
            <button type="button" class="alive-sequence__download" data-type="frames">Save Individual Frames</button>
        </div>
    `;

    const list = section.querySelector('.alive-sequence__list');
    newFrames.forEach((frame, idx) => {
        const item = document.createElement('button');
        item.className = 'alive-sequence__thumb';
        item.innerHTML = `<img src="${frame.url}" alt="Alive frame ${idx + 1}" loading="lazy">`;
        item.addEventListener('click', (event) => {
            event.stopPropagation();
            state.currentFrame = idx;
            el.frameSlider.value = idx;
            updateFrameDisplay();
            viewInCanvas(frame.url);
        });
        list.appendChild(item);
    });

    // FIXED #28: View Options button toggles menu
    const viewBtn = section.querySelector('.alive-sequence__view-btn');
    const menu = section.querySelector('.alive-sequence__menu');
    if (viewBtn && menu) {
        viewBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            const isHidden = menu.style.display === 'none';
            menu.style.display = isHidden ? 'flex' : 'none';
            viewBtn.textContent = isHidden ? 'Hide Options' : 'View Options';
        });
    }

    section.querySelectorAll('.alive-sequence__download').forEach(button => {
        button.addEventListener('click', (event) => {
            event.stopPropagation();
            const type = button.dataset.type;
            if (type === 'sheet' && spriteSheet) {
                const sheetFilename = spriteSheet.filename || spriteSheet.path || 'alive_sheet.png';
                const sheetUrl = spriteSheet.url
                    ? (spriteSheet.url.startsWith('http') ? spriteSheet.url : `${API_BASE}${spriteSheet.url}`)
                    : `${API_BASE}/download/${jobId}/${sheetFilename.split(/[/\\]/).pop()}`;
                downloadFile(sheetUrl, 'alive_sheet.png');
            } else if (type === 'frames') {
                newFrames.forEach(frame => {
                    downloadFile(frame.url, frame.filename);
                });
            }
        });
    });

    el.gallery.prepend(section);
    showStatus('Alive sequence ready!', 'success');
    renderStageFilmstrip();
    refreshAssistantCues();
    cacheOnionFrame(state.currentFrame);
}

function addToGallery(imagePath, label, jobId, qcInfo = null, options = {}) {
    const extractIndex = options.imageIndex ?? 0;
    const variantSet = options.variants ?? [];
    const filmstripEntries = options.filmstrip ?? [];
    const childImages = options.childImages ?? []; // FIXED #9: Get child images from options
    const filename = imagePath.split(/[/\\]/).pop();
    const isAbsolute = imagePath.startsWith('http://') || imagePath.startsWith('https://');
    const url = isAbsolute ? imagePath : `${API_BASE}/download/${jobId}/${filename}`;
    
    // Generate better name if label is generic
    const betterLabel = generateBetterLabel(label, options);
    
    const item = document.createElement('div');
    item.className = 'gallery-item';
    item.dataset.jobId = jobId;
    item.dataset.imageIndex = extractIndex;
    item.dataset.url = url;
    item.dataset.label = betterLabel;
    item.dataset.variants = JSON.stringify(variantSet);
    item.dataset.filmstrip = JSON.stringify(filmstripEntries);
    const qcBadge = buildQcBadge(qcInfo);
    const qaPayload = qcInfo ? btoa(encodeURIComponent(JSON.stringify(qcInfo))) : '';
    const resolutionLabel = options.variants?.[0]?.size
        ? `${options.variants[0].size[0]}×${options.variants[0].size[1]}`
        : '';
    item.innerHTML = `
        <img src="${url}" alt="${betterLabel}" loading="lazy">
        ${qcBadge}
        <div class="gallery-item__actions">
            <button onclick="event.stopPropagation(); openGalleryViewer(this.closest('.gallery-item'))">View</button>
            <button onclick="event.stopPropagation(); downloadFile('${url}', '${filename}')">Save</button>
            <button class="gallery__alive-btn" onclick="event.stopPropagation(); generateAliveAnimation('${jobId}', 0)">Alive!</button>
            <button class="gallery__background-btn" onclick="event.stopPropagation(); setGalleryBackground('${url}', '${filename}')">Background</button>
            ${qcInfo ? `<button onclick="event.stopPropagation(); showQaDetails('${label.replace(/'/g, "\'")}', '${qaPayload}')">QA</button>` : ''}
        </div>
        <div class="gallery-item__label">
            <span>${label}</span>
            <span>${resolutionLabel}</span>
        </div>
    `;
    // Clicking a gallery item should display it in the center stage immediately
    item.addEventListener('click', () => {
        const urlToShow = filmstripEntries?.[0]?.url || url;
        displayInStage(urlToShow);
    });
    el.gallery.appendChild(item);
    
    // Save gallery state after adding new item
    saveGalleryState();
}

function generateBetterLabel(originalLabel, options = {}) {
    // If already a good name, keep it
    if (!originalLabel.match(/^(Pixel|Sprite|Sheet|Frame)\s+\d+$/i)) {
        return originalLabel;
    }
    
    // Try to extract meaningful name from context
    const prompt = el.promptInput?.value || '';
    if (prompt) {
        const words = prompt.toLowerCase()
            .replace(/[^\w\s]/g, '') // Remove special chars
            .split(/\s+/)
            .filter(word => word.length > 2) // Filter short words
            .slice(0, 3); // Take first 3 meaningful words
        
        if (words.length > 0) {
            const baseName = words.map(word => 
                word.charAt(0).toUpperCase() + word.slice(1)
            ).join(' ');
            
            // Add direction if it's an animation frame
            if (originalLabel.includes('Frame')) {
                const direction = originalLabel.match(/(north|south|east|west|north-east|north-west|south-east|south-west)/i)?.[0];
                if (direction) {
                    return `${baseName} (${direction.charAt(0).toUpperCase() + direction.slice(1)})`;
                }
            }
            
            return baseName;
        }
    }
    
    // Fallback to original
    return originalLabel;
}

function addToGallery(imagePath, label, jobId, qcInfo = null, options = {}) {
    const extractIndex = options.imageIndex ?? 0;
    const variantSet = options.variants ?? [];
    const filmstripEntries = options.filmstrip ?? [];
    const childImages = options.childImages ?? []; // FIXED #9: Get child images from options
    const filename = imagePath.split(/[/\\]/).pop();
    const isAbsolute = imagePath.startsWith('http://') || imagePath.startsWith('https://');
    const url = isAbsolute ? imagePath : `${API_BASE}/download/${jobId}/${filename}`;
    
    // Generate better name if label is generic
    const betterLabel = generateBetterLabel(label, options);
    
    const item = document.createElement('div');
    item.className = 'gallery-item';
    item.dataset.jobId = jobId;
    item.dataset.imageIndex = extractIndex;
    item.dataset.url = url;
    item.dataset.label = betterLabel;
    item.dataset.variants = JSON.stringify(variantSet);
    item.dataset.filmstrip = JSON.stringify(filmstripEntries);
    const qcBadge = buildQcBadge(qcInfo);
    const qaPayload = qcInfo ? btoa(encodeURIComponent(JSON.stringify(qcInfo))) : '';
    const resolutionLabel = options.variants?.[0]?.size
        ? `${options.variants[0].size[0]}×${options.variants[0].size[1]}`
        : '';
    item.innerHTML = `
        <img src="${url}" alt="${betterLabel}" loading="lazy">
        ${qcBadge}
        <div class="gallery-item__actions">
            <button onclick="event.stopPropagation(); openGalleryViewer(this.closest('.gallery-item'))">View</button>
            <button onclick="event.stopPropagation(); downloadFile('${url}', '${filename}')">Save</button>
            <button class="gallery__alive-btn" onclick="event.stopPropagation(); generateAliveAnimation('${jobId}', ${extractIndex})">Alive!</button>
            <button class="gallery__background-btn" onclick="event.stopPropagation(); setGalleryBackground('${url}', '${filename}')">Background</button>
        </div>
        <div class="gallery-item__label">
            <span>${betterLabel}</span>
            <span>${resolutionLabel}</span>
        </div>
    `;
    
    // FIXED #2: Click to display in sprite box (not just open viewer)
    item.addEventListener('click', (e) => {
        // Don't trigger if clicking action buttons
        if (e.target.closest('.gallery-item__actions')) return;
        
        // Display main image in sprite box
        const urlToDisplay = filmstripEntries?.[0]?.url || url;
        displayInStage(urlToDisplay);
        
        // Highlight this item as active
        document.querySelectorAll('.gallery-item').forEach(gi => 
            gi.classList.remove('active')
        );
        item.classList.add('active');
    });
    
    // FIX: Always show stacked filmstrip if animation frames exist
    if ((options.isAnimation && options.framesByDirection) || options.filmstrip?.length > 8) {
        const animSection = document.createElement('div');
        animSection.className = 'animation-directions';
        
        const framesByDir = options.framesByDirection || {};
        
        // If no explicit direction grouping, try to group by filmstrip data
        if (!options.framesByDirection && options.filmstrip?.length > 0) {
            options.filmstrip.forEach(frame => {
                if (frame.metadata?.direction) {
                    const dir = frame.metadata.direction;
                    if (!framesByDir[dir]) framesByDir[dir] = [];
                    framesByDir[dir].push(frame);
                }
            });
        }
        
        const directions = ['south', 'west', 'east', 'north'];
        let hasAnyFrames = false;
        
        directions.forEach(dir => {
            const dirFrames = framesByDir[dir] || [];
            if (dirFrames.length === 0) return;
            
            hasAnyFrames = true;
            
            const dirStrip = document.createElement('div');
            dirStrip.className = 'direction-strip';
            
            const dirTitle = document.createElement('h4');
            dirTitle.textContent = dir.charAt(0).toUpperCase() + dir.slice(1);
            dirTitle.className = 'direction-title';
            dirStrip.appendChild(dirTitle);
            
            const framesContainer = document.createElement('div');
            framesContainer.className = 'direction-frames';
            
            dirFrames.forEach((frame, idx) => {
                const frameThumb = document.createElement('button');
                frameThumb.className = 'direction-frame-thumb';
                frameThumb.type = 'button';
                frameThumb.title = `${dir} frame ${idx + 1}`;
                
                const img = document.createElement('img');
                img.src = frame.url;
                img.alt = `${dir} ${idx}`;
                img.loading = 'lazy';
                frameThumb.appendChild(img);
                
                frameThumb.addEventListener('click', (e) => {
                    e.stopPropagation();
                    displayInStage(frame.url);
                    
                    // Highlight active frame
                    animSection.querySelectorAll('.direction-frame-thumb').forEach(t => 
                        t.classList.remove('active')
                    );
                    frameThumb.classList.add('active');
                });
                
                framesContainer.appendChild(frameThumb);
            });
            
            dirStrip.appendChild(framesContainer);
            animSection.appendChild(dirStrip);
        });
        
        if (hasAnyFrames) {
            item.appendChild(animSection);
        }
    }
    
    // FIXED #9: Add child images menu below main image
    if (childImages.length > 0) {
        const childrenSection = document.createElement('div');
        childrenSection.className = 'gallery-item__children';
        
        const childLabel = document.createElement('div');
        childLabel.className = 'children-label';
        childLabel.textContent = 'Variants';
        childrenSection.appendChild(childLabel);
        
        const childList = document.createElement('div');
        childList.className = 'children-list';
        
        childImages.forEach((child, idx) => {
            const thumb = document.createElement('button');
            thumb.className = 'child-thumb';
            thumb.title = child.label || `Variant ${idx + 1}`;
            thumb.type = 'button';
            
            const img = document.createElement('img');
            img.src = child.url;
            img.alt = child.label || `Variant ${idx + 1}`;
            img.loading = 'lazy';
            thumb.appendChild(img);
            
            thumb.addEventListener('click', (e) => {
                e.stopPropagation();
                displayInStage(child.url);
                
                // Highlight active child
                childList.querySelectorAll('.child-thumb').forEach(t => 
                    t.classList.remove('active')
                );
                thumb.classList.add('active');
            });
            
            childList.appendChild(thumb);
        });
        
        childrenSection.appendChild(childList);
        item.appendChild(childrenSection);
    }
    
    // FIXED #10: Add new items to TOP of gallery (prepend, not append)
    el.gallery.prepend(item);
    
    // Save gallery state after adding new item
    saveGalleryState();
    
    // Also add to filmstrip if provided
    if (filmstripEntries.length) {
        filmstripEntries.forEach(entry => {
            const filmImg = document.createElement('img');
            filmImg.src = entry.url;
            filmImg.alt = entry.label || label;
            filmImg.loading = 'lazy';
            filmImg.addEventListener('click', (event) => {
                event.stopPropagation();
                openGalleryViewer(item, entry.url);
            });
            el.filmstrip.appendChild(filmImg);
        });
    } else {
        const filmImg = document.createElement('img');
        filmImg.src = url;
        filmImg.alt = label;
        filmImg.loading = 'lazy';
        filmImg.addEventListener('click', (event) => {
            event.stopPropagation();
            openGalleryViewer(item);
        });
        el.filmstrip.appendChild(filmImg);
    }
}

// Display a given image URL on the main stage (center canvas)
function displayInStage(url) {
    if (!url || !el.canvas || !el.ctx) return;
    state.frames = [{ url }];
    state.currentFrame = 0;
    updateFrameDisplay();
    drawFrame();
}

// FIXED #23: Clean sprite creates child variant (doesn't replace original)
async function cleanSprite(jobId, imageIndex, buttonElement) {
    try {
        const galleryItem = buttonElement.closest('.gallery-item');
        
        galleryItem.classList.add('cleaning');
        showStatus('Cleaning sprite...', 'info');
        
        const response = await fetch(`${API_BASE}/clean-sprite`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: jobId, image_index: imageIndex })
        });
        
        const result = await response.json();
        
        if (result.success) {
            galleryItem.classList.remove('cleaning');
            galleryItem.classList.add('cleaned');
            
            // FIXED #23: Add cleaned version as child variant
            const cleanedUrl = `${API_BASE}${result.cleaned_image.url}`;
            
            // Find or create children section
            let childrenSection = galleryItem.querySelector('.gallery-item__children');
            if (!childrenSection) {
                childrenSection = document.createElement('div');
                childrenSection.className = 'gallery-item__children';
                
                const childLabel = document.createElement('div');
                childLabel.className = 'children-label';
                childLabel.textContent = 'Variants';
                childrenSection.appendChild(childLabel);
                
                const childList = document.createElement('div');
                childList.className = 'children-list';
                childrenSection.appendChild(childList);
                
                galleryItem.appendChild(childrenSection);
            }
            
            const childList = childrenSection.querySelector('.children-list');
            
            // Add cleaned sprite as child thumbnail
            const thumb = document.createElement('button');
            thumb.className = 'child-thumb';
            thumb.title = 'Cleaned (BG Removed)';
            thumb.type = 'button';
            
            const img = document.createElement('img');
            img.src = cleanedUrl;
            img.alt = 'Cleaned version';
            img.loading = 'lazy';
            thumb.appendChild(img);
            
            thumb.addEventListener('click', (e) => {
                e.stopPropagation();
                displayInStage(cleanedUrl);
                
                childList.querySelectorAll('.child-thumb').forEach(t => 
                    t.classList.remove('active')
                );
                thumb.classList.add('active');
            });
            
            childList.appendChild(thumb);
            showStatus('Cleaned version added to variants!', 'success');
        } else {
            throw new Error('Cleaning failed');
        }
    } catch (error) {
        console.error('Failed to clean sprite:', error);
        const galleryItem = buttonElement.closest('.gallery-item');
        galleryItem.classList.remove('cleaning');
        showStatus('Failed to clean sprite', 'error');
    }
}

async function generateAliveAnimation(jobId, imageIndex) {
    try {
        showStatus('Generating breathing animation...', 'info');
        
        const response = await fetch(`${API_BASE}/generate-alive-animation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_id: jobId,
                image_index: imageIndex,
                use_cleaned: false
            })
        });
        
        const data = await response.json();
        
        if (data.job_id) {
            showStatus('Animation started! Check job status...', 'success');
            
            // Poll for completion
            const pollInterval = setInterval(async () => {
                const statusResponse = await fetch(`${API_BASE}/jobs/${data.job_id}`);
                const statusData = await statusResponse.json();
                
            if (statusData.status === 'completed') {
                    clearInterval(pollInterval);
                    showStatus('Animation completed!', 'success');
                    
                    // Display animation frames
                if (statusData.result && statusData.result.frames) {
                    displayAnimationFrames(statusData.result.frames, statusData.result.sprite_sheet);
                }

                if (statusData.result) {
                    addAliveResultToGallery(jobId, statusData.result);
                }
                
                // Refresh gallery
                await loadHistory();
                } else if (statusData.status === 'failed') {
                    clearInterval(pollInterval);
                    showStatus('Animation failed', 'error');
                }
            }, 2000);
        }
    } catch (error) {
        console.error('Failed to generate alive animation:', error);
        showStatus('Failed to start animation', 'error');
    }
}

function displayAnimationFrames(frames, spriteSheet = null) {
    // Load frames into the preview canvas with playback controls
    state.frames = frames.map(f => ({
        url: `${API_BASE}${f.url}`,
        size: f.size || [128, 128]
    }));
    state.currentFrame = 0;
    updatePlaybackControls();
    drawFrame();

    if (spriteSheet) {
        state.latestSpriteSheet = {
            url: `${API_BASE}${spriteSheet.url}`,
            frameSize: spriteSheet.frame_size,
            frameCount: frames.length
        };
    }
}

function addAliveResultToGallery(jobId, result) {
    const gallerySection = document.createElement('div');
    gallerySection.className = 'gallery-item alive-result';
    gallerySection.innerHTML = `
        <div class="alive-preview">
            <canvas class="alive-preview__canvas" width="${state.frames[0]?.size?.[0] || 128}" height="${state.frames[0]?.size?.[1] || 128}"></canvas>
            <div class="alive-preview__info">
                <h4>Breathing Animation</h4>
                <p>${result.frame_count} frames</p>
                ${result.metadata?.source?.source ? `<p class="alive-preview__source">Source: ${result.metadata.source.source}</p>` : ''}
                <div class="alive-preview__actions">
                    <button onclick="downloadFile('${API_BASE}${result.sprite_sheet.url}', 'breathing_sheet.png')">Download Sheet</button>
                    <button onclick="downloadAliveFrames('${jobId}', ${JSON.stringify(result.frames)})">Download Frames</button>
                </div>
            </div>
        </div>
    `;

    el.gallery.prepend(gallerySection);

    const previewCanvas = gallerySection.querySelector('.alive-preview__canvas');
    if (previewCanvas) {
        playAlivePreview(previewCanvas, result.frames);
    }
}

window.downloadAliveFrames = function(jobId, frames) {
    frames.forEach(frame => {
        const filename = frame.path.split(/[\\/]/).pop();
        downloadFile(`${API_BASE}${frame.url}`, filename);
    });
};

function playAlivePreview(canvas, frames) {
    if (!canvas || !frames?.length) return;
    const ctx = canvas.getContext('2d');
    let current = 0;

    const render = async () => {
        const frame = frames[current];
        const img = await loadImage(`${API_BASE}${frame.url}`);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        current = (current + 1) % frames.length;
        setTimeout(render, 1000 / (state.fps || 8));
    };

    render();
}

function buildQcBadge(qcInfo) {
    if (!qcInfo) return '';
    const status = qcInfo.passed ? 'pass' : 'fail';
    const label = qcInfo.passed ? 'PASS' : 'CHECK';
    return `
        <div class="qa-badge ${status}">
            <span>${label}</span>
        </div>
    `;
}

function renderQaPanel() {
    if (!el.qaPanel || !el.qaList) return; // FIX: Check both elements exist
    el.qaList.innerHTML = '';
    if (!state.qaRecords || state.qaRecords.length === 0) {
        el.qaPanel.style.display = 'none';
        return;
    }

    el.qaPanel.style.display = 'block';
    state.qaRecords.forEach(record => {
        const item = document.createElement('div');
        item.className = 'qa-item';

        const statusClass = record.qc?.passed ? 'pass' : 'fail';
        const statusLabel = record.qc?.passed ? 'PASS' : 'CHECK';

        const backgroundPercent = record.qc?.background_percent;
        const spritePercent = record.qc?.sprite_percent;
        const compCount = record.qc?.component_count;

        const qaPayload = btoa(encodeURIComponent(JSON.stringify(record.qc)));
        const originalUrlEncoded = record.originalUrl ? encodeURIComponent(record.originalUrl) : 'null';
        const processedUrlEncoded = record.processedUrl ? encodeURIComponent(record.processedUrl) : 'null';
        
        item.innerHTML = `
            <div class="qa-item__header">
                <span class="qa-item__label">${record.label}</span>
                <span class="qa-status ${statusClass}">${statusLabel}</span>
            </div>
            <div class="qa-metrics">
                ${backgroundPercent != null ? `<div class="qa-metric"><strong>BG Removed</strong><br>${backgroundPercent}%</div>` : ''}
                ${spritePercent != null ? `<div class="qa-metric"><strong>Sprite Coverage</strong><br>${spritePercent}%</div>` : ''}
                ${compCount != null ? `<div class="qa-metric"><strong>Components</strong><br>${compCount}</div>` : ''}
                ${record.qc?.solidity ? `<div class="qa-metric"><strong>Solidity</strong><br>${record.qc.solidity}</div>` : ''}
            </div>
            ${record.qc?.notes?.length ? `<div class="qa-notes">${record.qc.notes.join('<br>')}</div>` : ''}
            <button class="qa-compare-btn" onclick="showQaDetails('${record.label.replace(/'/g, "\\'")}', '${qaPayload}', decodeURIComponent('${originalUrlEncoded}'), decodeURIComponent('${processedUrlEncoded}'))">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M21 6H3c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 10H3V8h18v8zM5 10h4v4H5zm6 0h8v1h-8zm0 3h8v1h-8z"/>
                </svg>
                Compare Before/After
            </button>
        `;

        el.qaList.appendChild(item);
    });
}

window.showQaDetails = function(label, encodedQc, originalUrl = null, processedUrl = null) {
    try {
        const qcInfo = JSON.parse(decodeURIComponent(atob(encodedQc)));
        
        // Create modal HTML
        const modal = document.createElement('div');
        modal.className = 'qa-modal-overlay';
        modal.innerHTML = `
            <div class="qa-modal">
                <div class="qa-modal-header">
                    <h3>${label}</h3>
                    <button class="qa-modal-close" onclick="this.closest('.qa-modal-overlay').remove()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                        </svg>
                    </button>
                </div>
                
                ${originalUrl && processedUrl ? `
                <div class="qa-comparison">
                    <div class="qa-comparison-side">
                        <h4>Before (Original)</h4>
                        <img src="${originalUrl}" alt="Original" class="qa-comparison-img">
                    </div>
                    <div class="qa-comparison-arrow">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M16.01 11H4v2h12.01v3L20 12l-3.99-4v3z"/>
                        </svg>
                    </div>
                    <div class="qa-comparison-side">
                        <h4>After (Processed)</h4>
                        <img src="${processedUrl}" alt="Processed" class="qa-comparison-img">
                    </div>
                </div>
                ` : ''}
                
                <div class="qa-modal-details">
                    ${Object.entries(qcInfo).map(([key, value]) => `
                        <div class="qa-detail-row">
                            <span class="qa-detail-key">${key}:</span>
                            <span class="qa-detail-value">${typeof value === 'object' ? JSON.stringify(value, null, 2) : value}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
        
    } catch (error) {
        console.error('Failed to decode QC payload', error);
    }
};


window.viewInCanvas = async function(url) {
    const img = await loadImage(url);
    drawCheckerboard();
    const scale = Math.min(el.canvas.width / img.width, el.canvas.height / img.height);
    const w = img.width * scale;
    const h = img.height * scale;
    const x = (el.canvas.width - w) / 2;
    const y = (el.canvas.height - h) / 2;
    el.ctx.drawImage(img, x, y, w, h);
    el.canvasOverlay.classList.add('hidden');
    minimizeHero();
}

window.downloadFile = function(url, filename) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
}

// ============================================================
// Mode Switching
// ============================================================

function switchMode(mode) {
    state.currentMode = mode;
    document.querySelectorAll('.mode-pill').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    el.preset.value = MODE_PRESETS[mode];

    const animationTab = document.getElementById('animationTab');

    if (animationTab) {
        animationTab.toggleAttribute('hidden', mode !== 'animation');
    }

    if (mode === 'animation' || mode === 'alive') {
        state.frames = [];
        state.currentFrame = 0;
        state.playing = false;
        updatePlaybackControls();
        drawCheckerboard();
        if (el.canvasOverlay) {
            el.canvasOverlay.classList.remove('hidden');
        }
    }

    if (mode === 'alive') {
        if (el.removeBg) el.removeBg.checked = true;
        if (el.extractSprites) el.extractSprites.checked = true;
        if (el.removeBg) el.removeBg.disabled = true;
        if (el.extractSprites) el.extractSprites.disabled = true;
    } else if (mode === 'character') {
        if (el.removeBg) {
            el.removeBg.checked = true;
            el.removeBg.disabled = false;
        }
        if (el.extractSprites) {
            el.extractSprites.disabled = false;
        }
    } else if (mode === 'background') {
        if (el.removeBg) {
            el.removeBg.checked = false;
            el.removeBg.disabled = true;
        }
        if (el.extractSprites) {
            el.extractSprites.checked = false;
            el.extractSprites.disabled = true;
        }
        if (el.width) el.width.value = 2048;
        if (el.height) el.height.value = 1024;
    } else {
        if (el.removeBg) el.removeBg.disabled = false;
        if (el.extractSprites) el.extractSprites.disabled = false;
    }
}

// ============================================================
// Tab Switching
// ============================================================

function switchTab(tabName) {
    if (!el.tabs || !el.tabContents) return;
    el.tabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    el.tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}Tab`);
    });
}

function toggleGalleryView() {
    const isFilmstrip = el.filmstrip.style.display !== 'none';
    el.gallery.style.display = isFilmstrip ? 'grid' : 'none';
    el.filmstrip.style.display = isFilmstrip ? 'none' : 'flex';
}

function clearGallery() {
    if (confirm('Clear all gallery items?')) {
        el.gallery.innerHTML = '';
        el.filmstrip.innerHTML = '';
        state.frames = [];
        state.currentFrame = 0;
        drawCheckerboard();
        el.canvasOverlay.classList.remove('hidden');
        el.playbackControls.style.display = 'none';
    }
}

// ============================================================
// Backend Communication
// ============================================================

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        const isHealthy = data.status === 'healthy';
        
        el.statusBadge.classList.toggle('connected', isHealthy);
        el.statusText.textContent = isHealthy 
            ? `Connected · ${data.backend}` 
            : 'Backend offline';
    } catch (error) {
        el.statusBadge.classList.remove('connected');
        el.statusText.textContent = 'Disconnected';
    }
}

async function loadModels() {
    try {
        const response = await fetch(`${API_BASE}/models`);
        const data = await response.json();
        
        if (el.lora) {
            el.lora.innerHTML = '<option value="">Style: Base model</option>';
            (data.loras || []).forEach(lora => {
                const option = document.createElement('option');
                option.value = lora.name;
                option.textContent = `Style: ${lora.name.replace(/_/g, ' ')}`;
                el.lora.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load models:', error);
    }
}

async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/jobs?limit=100`);
        const data = await response.json();
        
        el.historyList.innerHTML = '';
        const jobs = data.jobs || [];  // Already sorted by backend
        
        if (jobs.length === 0) {
            el.historyList.innerHTML = '<p style="text-align: center; color: #64748b; padding: 2rem;">No history yet</p>';
            return;
        }
        
        jobs.forEach(job => {
            const item = document.createElement('div');
            item.className = 'history-item';
            item.innerHTML = `
                <div class="history-item__info">
                    <div class="history-item__id">${job.job_id.slice(0, 8)}...</div>
                    <div class="history-item__msg">${job.message || ''}</div>
                </div>
                <div class="history-item__status ${job.status}">${job.status}</div>
            `;
            
            if (job.status === 'completed') {
                item.addEventListener('click', async () => {
                    const detail = await fetch(`${API_BASE}/jobs/${job.job_id}`).then(r => r.json());
                    if (detail.result) handleResults(detail.result, job.job_id);
                });
            }
            
            el.historyList.appendChild(item);
        });
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

// ============================================================
// Import/Upload
// ============================================================

function handleDragOver(e) {
    e.preventDefault();
    el.dropzone.classList.add('drag-over');
}

function handleDragLeave(e) {
    el.dropzone.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    el.dropzone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) {
        processFile(e.dataTransfer.files[0]);
    }
}

function handleFileSelect(e) {
    if (e.target.files[0]) {
        processFile(e.target.files[0]);
    }
}

async function processFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    showProgress('Processing upload...');
    
    try {
        const removeBg = el.uploadRemoveBg.checked;
        const extract = el.uploadExtract.checked;
        
        const response = await fetch(
            `${API_BASE}/process-image?remove_background=${removeBg}&extract_sprites=${extract}`,
            { method: 'POST', body: formData }
        );
        
        if (!response.ok) throw new Error('Processing failed');
        
        const data = await response.json();
        hideProgress();
        handleResults(data.result);
        loadHistory();
        switchTab('gallery');
    } catch (error) {
        hideProgress();
        alert(`Upload failed: ${error.message}`);
    }
}

// ============================================================
// UI Effects
// ============================================================

function minimizeHero() {
    if (el.hero) { // FIX: Check element exists
        el.hero.classList.add('minimized');
    }
}

function observeScroll() {
    let lastScroll = 0;
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        if (currentScroll > 100 && currentScroll > lastScroll) {
            minimizeHero();
        }
        lastScroll = currentScroll;
    });
}

// ============================================================
// Pixel Snowflakes Background
// ============================================================

function createPixelSnowflakes() {
    const container = document.querySelector('.pixel-snowflakes');
    if (!container) return;
    const colors = ['#3b82f6', '#8b5cf6', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#f472b6'];
    
    function createPixel() {
        if (accessibilityState.reduceMotion) return;
        const pixel = document.createElement('div');
        pixel.className = 'pixel-flake';
        pixel.style.left = Math.random() * 100 + '%';
        pixel.style.animationDuration = (Math.random() * 15 + 10) + 's';
        pixel.style.animationDelay = Math.random() * 5 + 's';
        pixel.style.opacity = Math.random() * 0.5 + 0.3;
        pixel.style.setProperty('--drift', `${Math.random() * 40 - 20}px`);

        const size = Math.random() > 0.7 ? 8 : 6;
        pixel.style.width = size + 'px';
        pixel.style.height = size + 'px';
        pixel.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];

        container.appendChild(pixel);

        setTimeout(() => {
            pixel.remove();
            createPixel();
        }, (parseFloat(pixel.style.animationDuration) + parseFloat(pixel.style.animationDelay)) * 1000);
    }
    
    // Create initial pixels
    for (let i = 0; i < 30; i++) {
        setTimeout(() => createPixel(), i * 200);
    }
}

// Start snowflakes (initialized in DOMContentLoaded)

function restoreGalleryState() {
    try {
        const savedGallery = localStorage.getItem('pearlPixelGallery');
        if (!savedGallery) return;
        
        const galleryData = JSON.parse(savedGallery);
        if (!galleryData || !galleryData.items || galleryData.items.length === 0) return;
        
        console.log(`Checking ${galleryData.items.length} cached gallery items...`);
        
        // FIX: Only restore non-animation items (avoid 404s from old frames)
        galleryData.items.forEach(item => {
            if (item.url && item.label && item.jobId) {
                // Skip animation items that might have expired frame URLs
                if (!item.url.includes('frame_') && !item.options?.isAnimation) {
                    addToGallery(item.url, item.label, item.jobId, item.qc, item.options);
                } else {
                    console.log(`Skipping cached animation: ${item.label} (frames may be expired)`);
                }
            }
        });
        
    } catch (e) {
        console.warn('Failed to restore gallery state:', e);
        // Clear corrupted cache
        localStorage.removeItem('pearlPixelGallery');
    }
}

function saveGalleryState() {
    if (!el.gallery) return;
    try {
        const galleryItems = Array.from(el.gallery.querySelectorAll('.gallery-item')).map(item => ({
            url: item.dataset.url,
            label: item.dataset.label,
            jobId: item.dataset.jobId,
            imageIndex: parseInt(item.dataset.imageIndex, 10) || 0,
            qc: null,  // Don't cache QC data (too large)
            options: {
                imageIndex: parseInt(item.dataset.imageIndex, 10) || 0
            }
        }));
        
        localStorage.setItem('pearlPixelGallery', JSON.stringify({
            items: galleryItems.slice(0, 50),  // Keep last 50 items
            savedAt: new Date().toISOString()
        }));
    } catch (e) {
        console.warn('Failed to save gallery state:', e);
    }
}

let viewerState = {
    variants: [],
    filmstrip: [],
    currentVariant: 0,
    currentFilmIndex: 0,
    jobId: null,
    baseLabel: '',
    playbackTimer: null,
    fps: 12,
    playing: false,
    zoom: 4
};

function openGalleryViewer(itemElement, overrideUrl = null) {
    if (!el.galleryViewer) return;
    const dataset = itemElement.dataset || {};

    viewerState.jobId = dataset.jobId || state.jobId;
    viewerState.baseLabel = dataset.label || 'Sprite';

    try {
        viewerState.variants = JSON.parse(dataset.variants || '[]');
    } catch {
        viewerState.variants = [];
    }

    try {
        viewerState.filmstrip = JSON.parse(dataset.filmstrip || '[]');
    } catch {
        viewerState.filmstrip = [];
    }

    if (!viewerState.variants.length) {
        viewerState.variants = [
            {
                key: 'raw',
                label: 'Raw',
                url: dataset.url,
                size: null
            }
        ];
    }

    viewerState.currentVariant = 0;
    viewerState.currentFilmIndex = 0;
    viewerState.playing = false;
    stopViewerPlayback();

    el.galleryViewer.classList.remove('hidden');
    const initialVariant = viewerState.variants[0];
    const initialUrl = overrideUrl || initialVariant?.url || dataset.url;
    if (el.galleryViewerFps) el.galleryViewerFps.value = viewerState.fps;
    applyViewerZoom(initialVariant);
    renderGalleryViewer(initialUrl);
}

function renderGalleryViewer(url) {
    if (!el.galleryViewerImage) return;

    el.galleryViewerImage.src = url;
    const currentVariant = viewerState.variants[viewerState.currentVariant] || { label: viewerState.baseLabel, url };
    el.galleryViewerMeta.innerHTML = buildVariantMeta(currentVariant);
    applyViewerZoom(currentVariant);

    renderViewerVariants();
    renderViewerFilmstrip();
    updateViewerCounter();
    updateViewerPlaybackUI();
}

function buildVariantMeta(variant) {
    if (!variant) return '';
    const size = Array.isArray(variant.size) ? `${variant.size[0]} × ${variant.size[1]}` : '—';
    const rows = [
        `<div><strong>Variant:</strong> ${variant.label || variant.key || 'Untitled'}</div>`,
        `<div><strong>Resolution:</strong> ${size}</div>`
    ];

    if (variant.meta && typeof variant.meta === 'object') {
        Object.entries(variant.meta).forEach(([key, value]) => {
            if (value == null) return;
            const rendered = typeof value === 'object' ? JSON.stringify(value) : value;
            rows.push(`<div><strong>${key}</strong>: ${rendered}</div>`);
        });
    }

    return rows.join('');
}

function renderViewerVariants() {
    if (!el.galleryViewerVariants) return;
    el.galleryViewerVariants.innerHTML = '';

    viewerState.variants.forEach((variant, index) => {
        if (!variant?.url) return;
        const button = document.createElement('button');
        button.className = 'gallery-viewer__variant';
        if (index === viewerState.currentVariant) button.classList.add('active');
        button.textContent = variant.label || variant.key || `Variant ${index + 1}`;
        button.addEventListener('click', () => {
            viewerState.currentVariant = index;
            viewerState.currentFilmIndex = index;
            stopViewerPlayback();
            applyViewerZoom(variant);
            renderGalleryViewer(variant.url);
        });
        el.galleryViewerVariants.appendChild(button);
    });
}

function renderViewerFilmstrip() {
    if (!el.galleryViewerFilmstrip) return;
    el.galleryViewerFilmstrip.innerHTML = '';

    const entries = viewerState.filmstrip.length
        ? viewerState.filmstrip
        : viewerState.variants.map((variant, index) => ({
            url: variant.preview_url || variant.url,
            label: variant.label || variant.key || `Variant ${index + 1}`
        }));

    entries.forEach((entry, index) => {
        if (!entry?.url) return;
        const thumb = document.createElement('img');
        thumb.src = entry.url;
        thumb.alt = entry.label || `Frame ${index + 1}`;
        thumb.classList.toggle('active', index === viewerState.currentFilmIndex);
        thumb.addEventListener('click', () => {
            viewerState.currentFilmIndex = index;
            viewerState.currentVariant = Math.min(index, viewerState.variants.length - 1);
            if (!viewerState.playing) stopViewerPlayback();
            renderGalleryViewer(viewerState.variants[viewerState.currentVariant]?.url || entry.url);
        });
        el.galleryViewerFilmstrip.appendChild(thumb);
    });
}

function updateViewerCounter() {
    if (!el.galleryViewerCounter) return;
    const total = Math.max(viewerState.variants.length, viewerState.filmstrip.length) || 1;
    el.galleryViewerCounter.textContent = `${viewerState.currentFilmIndex + 1} / ${total}`;
}

function closeGalleryViewer() {
    if (!el.galleryViewer) return;
    stopViewerPlayback();
    el.galleryViewer.classList.add('hidden');
    el.galleryViewerImage.src = '';
    viewerState = {
        variants: [],
        filmstrip: [],
        currentVariant: 0,
        currentFilmIndex: 0,
        jobId: null,
        baseLabel: '',
        playbackTimer: null,
        fps: 12,
        playing: false
    };
}

function navigateViewerFrame(direction, { fromPlayback = false } = {}) {
    const total = Math.max(viewerState.variants.length, viewerState.filmstrip.length);
    if (!total) return;

    viewerState.currentFilmIndex = (viewerState.currentFilmIndex + direction + total) % total;
    viewerState.currentVariant = Math.min(viewerState.currentFilmIndex, viewerState.variants.length - 1);

    if (!fromPlayback) stopViewerPlayback();
    const variant = viewerState.variants[viewerState.currentVariant];
    renderGalleryViewer(variant?.url || viewerState.filmstrip[viewerState.currentFilmIndex]?.url);
}

function startViewerPlayback() {
    stopViewerPlayback();
    viewerState.playing = true;
    viewerState.playbackTimer = setInterval(() => navigateViewerFrame(1, { fromPlayback: true }), Math.max(80, 1000 / Math.max(viewerState.fps, 1)));
    updateViewerPlaybackUI();
}

function stopViewerPlayback() {
    if (viewerState.playbackTimer) {
        clearInterval(viewerState.playbackTimer);
        viewerState.playbackTimer = null;
    }
    viewerState.playing = false;
    updateViewerPlaybackUI();
}

function toggleViewerPlayback() {
    viewerState.playing ? stopViewerPlayback() : startViewerPlayback();
}

function updateViewerPlaybackUI() {
    if (el.galleryViewerPlayToggle) {
        el.galleryViewerPlayToggle.textContent = viewerState.playing ? 'Pause' : 'Play';
    }
    if (el.galleryViewerFpsValue) {
        el.galleryViewerFpsValue.textContent = viewerState.fps;
    }
    if (el.galleryViewerFps && Number(el.galleryViewerFps.value) !== viewerState.fps) {
        el.galleryViewerFps.value = viewerState.fps;
    }
    if (el.galleryViewerZoomButtons?.length) {
        el.galleryViewerZoomButtons.forEach(button => {
            const level = Number(button.dataset.zoomLevel) || 1;
            button.classList.toggle('active', level === viewerState.zoom);
        });
    }
}

function applyViewerZoom(variant) {
    if (!el.galleryViewerImage) return;
    const width = (variant?.size?.[0] || el.galleryViewerImage.naturalWidth || 256) * viewerState.zoom;
    el.galleryViewerImage.style.width = `${width}px`;
    el.galleryViewerImage.style.imageRendering = 'pixelated';
}

// ============================================================
// Background Generation
// ============================================================

async function handleBackgroundGeneration() {
    const prompt = (el.backgroundPrompt?.value || '').trim();
    if (!prompt) {
        if (el.backgroundModalStatus) {
            el.backgroundModalStatus.textContent = 'Please describe the new backdrop first.';
        }
        return;
    }

    if (el.backgroundModalStatus) {
        el.backgroundModalStatus.textContent = 'Dreaming up your studio backdrop...';
    }
    if (el.backgroundModalCreate) {
        el.backgroundModalCreate.disabled = true;
    }

    try {
        const response = await fetch(`${API_BASE}/generate_background`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });

        if (!response.ok) {
            throw new Error('Background generation failed');
        }

        const data = await response.json();
        if (data?.url) {
            backgroundState.gallery = [data, ...backgroundState.gallery];
            backgroundState.current = data.url;
            backgroundState.currentPalette = data.palette || [];
            updateBackgroundImage(data.url);
            applyPaletteToDocument(data.palette);
            renderBackgroundGallery();
            launchConfetti('Backdrop created!');
            if (el.backgroundModalStatus) {
                el.backgroundModalStatus.textContent = 'Backdrop ready!';
            }
            setTimeout(closeBackgroundModal, 1200);
        } else {
            throw new Error('No background returned');
        }
    } catch (error) {
        console.error('Background generation failed:', error);
        if (el.backgroundModalStatus) {
            el.backgroundModalStatus.textContent = 'Could not generate background. Please try again.';
        }
    } finally {
        if (el.backgroundModalCreate) {
            el.backgroundModalCreate.disabled = false;
        }
    }
}

function openBackgroundModal() {
    el.backgroundModal?.classList.remove('hidden');
    el.backgroundPrompt?.focus();
}

function closeBackgroundModal() {
    el.backgroundModal?.classList.add('hidden');
    if (el.backgroundModalStatus) el.backgroundModalStatus.textContent = '';
    if (el.backgroundPrompt) el.backgroundPrompt.value = '';
}

async function fetchBackgroundGallery() {
    if (hasInitializedBackground) return;
    hasInitializedBackground = true;
    
    // Try to restore from localStorage first
    const cachedBackground = localStorage.getItem('pearlPixelBackground');
    if (cachedBackground) {
        try {
            const cached = JSON.parse(cachedBackground);
            backgroundState.current = cached.url || backgroundState.current;
            backgroundState.currentPalette = cached.palette || [];
            updateBackgroundImage(backgroundState.current);
            applyPaletteToDocument(backgroundState.currentPalette);
        } catch (e) {
            console.warn('Failed to restore cached background:', e);
        }
    }
    
    try {
        const response = await fetch(`${API_BASE}/backgrounds`);
        if (!response.ok) throw new Error('Failed to load backgrounds');
        const data = await response.json();
        backgroundState.gallery = data?.backgrounds || [];
        const latest = backgroundState.gallery.find(item => item.is_active) || backgroundState.gallery[0];
        if (latest?.url) {
            backgroundState.current = latest.url;
            backgroundState.currentPalette = latest.palette || [];
            updateBackgroundImage(latest.url);
            applyPaletteToDocument(latest.palette);
            
            // Cache active background
            localStorage.setItem('pearlPixelBackground', JSON.stringify({
                url: latest.url,
                palette: latest.palette
            }));
        } else if (backgroundState.current) {
            updateBackgroundImage(backgroundState.current);
        }
        renderBackgroundGallery();
    } catch (error) {
        console.warn('Failed to load background gallery:', error);
        updateBackgroundImage(backgroundState.current);
    } finally {
        renderBackgroundGallery();
    }
}

async function markBackgroundFavorite(backgroundId, favorite = true) {
    try {
        const response = await fetch(`${API_BASE}/backgrounds/${backgroundId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ favorite })
        });
        if (response.ok) {
            const updated = await response.json();
            backgroundState.gallery = backgroundState.gallery.map(bg => bg.id === updated.id ? updated : bg);
            renderBackgroundGallery();
            launchConfetti(favorite ? 'Favorited!' : 'Removed favorite');
        }
    } catch (error) {
        console.warn('Failed to update favorite', error);
    }
}

async function activateBackground(backgroundId) {
    try {
        const response = await fetch(`${API_BASE}/backgrounds/${backgroundId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: true })
        });
        if (!response.ok) throw new Error('Failed to activate background');
        const updated = await response.json();
        backgroundState.gallery = backgroundState.gallery.map(bg => {
            if (bg.id === updated.id) {
                return updated;
            }
            return { ...bg, is_active: false };
        });
        backgroundState.current = updated.url;
        backgroundState.currentPalette = updated.palette || [];
        updateBackgroundImage(updated.url);
        applyPaletteToDocument(updated.palette);
        
        // Cache updated background
        localStorage.setItem('pearlPixelBackground', JSON.stringify({
            url: updated.url,
            palette: updated.palette
        }));
        
        renderBackgroundGallery();
        launchConfetti('Background updated!');
    } catch (error) {
        console.warn('Failed to activate background:', error);
    }
}

async function resetBackground() {
    try {
        const response = await fetch(`${API_BASE}/backgrounds/reset`, { method: 'POST' });
        if (!response.ok) throw new Error('Reset failed');
        const data = await response.json();
        backgroundState.current = data.url;
        backgroundState.currentPalette = data.palette || [];
        updateBackgroundImage(backgroundState.current);
        applyPaletteToDocument(data.palette);
        backgroundState.gallery = backgroundState.gallery.map(bg => ({ ...bg, is_active: false }));
        renderBackgroundGallery();
    } catch (error) {
        console.warn('Failed to reset background:', error);
    }
}

function updateBackgroundImage(url) {
    if (!el.backgroundImage) return;

    const img = el.backgroundImage;
    const stageBg = document.getElementById('stageBackground');

    const handleLoad = () => {
        img.style.opacity = '1';
        img.classList.remove('background-loading');
        img.removeEventListener('load', handleLoad);
        img.removeEventListener('error', handleError);
    };

    const handleError = () => {
        console.warn('Unable to load background image preview:', url);
        img.classList.remove('background-loading');
        img.style.opacity = '1';
        img.removeEventListener('load', handleLoad);
        img.removeEventListener('error', handleError);
        showStatus('Background image preview unavailable', 'warning');
    };

    img.addEventListener('load', handleLoad);
    img.addEventListener('error', handleError);

    img.classList.add('background-loading');
    img.style.opacity = '0';
    img.src = url;

    if (stageBg) {
        stageBg.style.backgroundImage = `url(${url})`;
    }
}

function renderBackgroundGallery() {
    if (!el.backgroundGalleryList) return;
    el.backgroundGalleryList.innerHTML = '';
    backgroundState.gallery.forEach((background) => {
        const card = document.createElement('div');
        card.className = 'background-card';
        if (background.is_active) card.classList.add('background-card--active');

        card.innerHTML = `
            <div class="background-card__preview">
                <img src="${background.url}" alt="${background.name || 'Background'}" loading="lazy">
            </div>
            <div class="background-card__meta">
                <strong>${background.name || 'Untitled backdrop'}</strong>
                <span class="background-card__prompt">${background.prompt || ''}</span>
                <div class="background-card__palette">
                    ${(background.palette || []).map(color => `<span style="background:${color}"></span>`).join('')}
                </div>
            </div>
            <div class="background-card__actions">
                <button data-action="activate">Use</button>
                <button data-action="favorite">${background.favorite ? 'Unfavorite' : 'Favorite'}</button>
            </div>
        `;

        card.querySelector('[data-action="activate"]').addEventListener('click', async () => {
            await activateBackground(background.id);
            renderBackgroundGallery();
        });

        card.querySelector('[data-action="favorite"]').addEventListener('click', async () => {
            await markBackgroundFavorite(background.id, !background.favorite);
            renderBackgroundGallery();
        });

        el.backgroundGalleryList.appendChild(card);
    });
}

function openBackgroundGalleryDrawer() {
    el.backgroundGallery?.classList.remove('hidden');
}

function closeBackgroundGalleryDrawer() {
    el.backgroundGallery?.classList.add('hidden');
}

// ============================================================
// Stage Controls
// ============================================================

const stageState = {
    grid: false,
    onionSkin: false,
    onionOpacity: 0.35,
    transparency: true,  // Default to clear/transparent
    backgroundMode: 'clear',  // clear, grid, paper
    loop: true,
    zoom: 1.0
};

const stageCache = {
    onionCanvas: null,
    onionCtx: null,
    onionFrame: null
};

function setStageBackgroundMode(mode) {
    stageState.backgroundMode = mode;
    
    // Update button states
    document.querySelectorAll('.stage-controls .stage-btn[data-mode]').forEach(btn => {
        const isActive = btn.dataset.mode === mode;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-pressed', String(isActive));
    });
    
    // Set flags based on mode
    switch (mode) {
        case 'clear':
            stageState.transparency = true;
            stageState.grid = false;
            break;
        case 'grid':
            stageState.transparency = false;
            stageState.grid = true;
            break;
        case 'paper':
            stageState.transparency = false;
            stageState.grid = false;
            break;
    }
    
    // Redraw canvas
    drawFrame();
}

function toggleStageMode(mode) {
    switch (mode) {
        case 'onion':
            stageState.onionSkin = !stageState.onionSkin;
            if (el.onionToggle) {
                el.onionToggle.classList.toggle('active', stageState.onionSkin);
                el.onionToggle.setAttribute('aria-pressed', String(stageState.onionSkin));
            }
            if (!stageState.onionSkin) {
                stageCache.onionFrame = null;
            }
            drawFrame();
            break;
        default:
            break;
    }
}

function toggleLooping() {
    stageState.loop = !stageState.loop;
    el.loopToggle.classList.toggle('active', stageState.loop);
}

function stepFrame(step) {
    if (!state.frames.length) return;
    const previous = state.currentFrame;
    state.currentFrame = (state.currentFrame + step + state.frames.length) % state.frames.length;
    el.frameSlider.value = state.currentFrame;
    updateFrameDisplay();
    cacheOnionFrame(previous);
    drawFrame();
}

function cacheOnionFrame(index) {
    if (!stageState.onionSkin || !el.canvas) return;
    if (!stageCache.onionCanvas) {
        stageCache.onionCanvas = document.createElement('canvas');
        stageCache.onionCanvas.width = el.canvas.width;
        stageCache.onionCanvas.height = el.canvas.height;
        stageCache.onionCtx = stageCache.onionCanvas.getContext('2d');
        stageCache.onionCtx.imageSmoothingEnabled = false;
    }
    stageCache.onionCtx.clearRect(0, 0, stageCache.onionCanvas.width, stageCache.onionCanvas.height);
    const frame = state.frames[index];
    if (!frame) return;
    loadImage(frame.url).then((img) => {
        const scale = Math.min(el.canvas.width / img.width, el.canvas.height / img.height) * stageState.zoom;
        const w = img.width * scale;
        const h = img.height * scale;
        const x = (el.canvas.width - w) / 2;
        const y = (el.canvas.height - h) / 2;
        stageCache.onionCtx.globalAlpha = stageState.onionOpacity;
        stageCache.onionCtx.drawImage(img, x, y, w, h);
        stageCache.onionCtx.globalAlpha = 1;
        stageCache.onionFrame = stageCache.onionCanvas;
    }).catch(() => {
        stageCache.onionFrame = null;
    });
}

function applyStageZoom(factor) {
    const nextZoom = Math.min(6, Math.max(0.25, stageState.zoom * factor));
    stageState.zoom = nextZoom;
    if (el.zoomLevelLabel) {
        el.zoomLevelLabel.textContent = `${Math.round(stageState.zoom * 100)}%`;
    }
    drawFrame();
}

function setStageZoom(value) {
    stageState.zoom = Math.min(6, Math.max(0.25, value));
    if (el.zoomLevelLabel) {
        el.zoomLevelLabel.textContent = `${Math.round(stageState.zoom * 100)}%`;
    }
    drawFrame();
}

function stepZoom(direction) {
    const increments = [0.25, 0.5, 1, 2, 3, 4, 6];
    const currentIndex = increments.findIndex(val => Math.abs(val - stageState.zoom) < 0.001);
    let nextIndex = currentIndex;
    if (direction > 0 && currentIndex < increments.length - 1) {
        nextIndex++;
    } else if (direction < 0 && currentIndex > 0) {
        nextIndex--;
    }
    setStageZoom(increments[nextIndex]);
}

function handleStageShortcuts(event) {
    if (event.target && ['INPUT', 'TEXTAREA'].includes(event.target.tagName)) {
        return;
    }
    switch (event.key.toLowerCase()) {
        case 'g':
            toggleStageMode('grid');
            break;
        case 'o':
            toggleStageMode('onion');
            break;
        case 't':
            toggleStageMode('transparency');
            break;
        case '+':
        case '=':
            stepZoom(1);
            break;
        case '-':
        case '_':
            stepZoom(-1);
            break;
        case 'arrowleft':
            stepFrame(-1);
            break;
        case 'arrowright':
            stepFrame(1);
            break;
        default:
            break;
    }
}

// ============================================================
// Prompt Templates & Assistant Cues
// ============================================================

function applyPromptTemplate(template) {
    if (!template || !el.prompt) return;
    const existing = el.prompt.value.trim();
    if (!existing) {
        el.prompt.value = template;
    } else if (!existing.includes(template)) {
        el.prompt.value = `${existing}\n${template}`;
    }
    el.prompt.focus();
}

function refreshAssistantCues() {
    if (!el.assistantCues) return;
    const cues = [];

    if (state.frames.length > 8) {
        cues.push('Tip: Use loop playback to spot flow issues.');
    }
    if (stageState.onionSkin) {
        cues.push('Onion-skin is active. Fine-tune offsets by nudging frames.');
    }
    if (!cues.length) {
        cues.push('Try a prompt template to jumpstart ideas.');
    }

    const list = el.assistantCues.querySelector('ul');
    if (list) {
        list.innerHTML = cues.map(cue => `<li>${cue}</li>`).join('');
    }
}

// ============================================================
// Filmstrip Rendering
// ============================================================

function renderStageFilmstrip() {
    if (!el.filmstripScroll) return;
    el.filmstripScroll.innerHTML = '';

    state.frames.forEach((frame, index) => {
        const thumb = document.createElement('img');
        thumb.src = frame.url;
        thumb.alt = `Frame ${index + 1}`;
        thumb.classList.toggle('active', index === state.currentFrame);
        thumb.addEventListener('click', () => {
            state.currentFrame = index;
            el.frameSlider.value = index;
            updateFrameDisplay();
            drawFrame();
            renderStageFilmstrip();
        });
        el.filmstripScroll.appendChild(thumb);
    });
}

function setupEventListeners() {
    // Form
    el.form?.addEventListener('submit', handleGenerate);

    // Mode pills
    document.querySelectorAll('.mode-pill').forEach(btn => {
        btn.addEventListener('click', () => switchMode(btn.dataset.mode));
    });

    // Set initial mode
    switchMode('character');
    if (el.removeBg) {
        el.removeBg.checked = true;
    }

    // Playback controls
    el.playBtn?.addEventListener('click', togglePlayback);
    el.prevFrameBtn?.addEventListener('click', () => stepFrame(-1));
    el.nextFrameBtn?.addEventListener('click', () => stepFrame(1));
    el.loopToggle?.addEventListener('click', toggleLooping);
    el.zoomInBtn?.addEventListener('click', () => stepZoom(1));
    el.zoomOutBtn?.addEventListener('click', () => stepZoom(-1));

    // Stage background mode controls
    document.getElementById('clearModeBtn')?.addEventListener('click', () => setStageBackgroundMode('clear'));
    document.getElementById('gridToggle')?.addEventListener('click', () => setStageBackgroundMode('grid'));
    document.getElementById('paperModeBtn')?.addEventListener('click', () => setStageBackgroundMode('paper'));

    // Options ribbon toggle
    const ribbon = document.getElementById('optionsRibbon');
    const ribbonToggle = document.getElementById('galleryOptionsToggle');
    ribbonToggle?.addEventListener('click', () => {
        if (!ribbon) return;
        const isHidden = ribbon.style.display === 'none' || ribbon.style.display === '';
        ribbon.style.display = isHidden ? 'flex' : 'none';
    });

    el.frameSlider?.addEventListener('input', () => {
        state.currentFrame = parseInt(el.frameSlider.value, 10) || 0;
        updateFrameDisplay();
        cacheOnionFrame(state.currentFrame);
        drawFrame();
    });

    el.fpsSlider?.addEventListener('input', () => {
        state.fps = parseInt(el.fpsSlider.value, 10) || 12;
        if (el.fpsLabel) {
            el.fpsLabel.textContent = `${state.fps}`;
        }
        if (state.playing) {
            stopPlayback();
            startPlayback();
        }
    });

    // Tabs
    el.tabs?.forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Gallery toggles
    el.toggleViewBtn?.addEventListener('click', toggleGalleryView);
    el.clearGalleryBtn?.addEventListener('click', clearGallery);

    // Import
    el.dropzone?.addEventListener('click', () => el.fileInput?.click());
    el.dropzone?.addEventListener('dragover', handleDragOver);
    el.dropzone?.addEventListener('dragleave', handleDragLeave);
    el.dropzone?.addEventListener('drop', handleDrop);
    el.fileInput?.addEventListener('change', handleFileSelect);

    // History
    el.refreshHistory?.addEventListener('click', loadHistory);

    // Gallery viewer
    el.galleryViewerClose?.addEventListener('click', closeGalleryViewer);
    el.galleryViewer?.addEventListener('click', (e) => {
        if (e.target === el.galleryViewer || e.target.classList.contains('gallery-viewer__backdrop')) {
            closeGalleryViewer();
        }
    });
    el.galleryViewerPrev?.addEventListener('click', () => navigateViewerFrame(-1));
    el.galleryViewerNext?.addEventListener('click', () => navigateViewerFrame(1));
    el.galleryViewerFps?.addEventListener('input', (event) => {
        viewerState.fps = Number(event.target.value) || 12;
        updateViewerPlaybackUI();
    });
    el.galleryViewerPlayToggle?.addEventListener('click', toggleViewerPlayback);
    el.galleryViewerZoomButtons?.forEach(button => {
        button.addEventListener('click', () => {
            const level = Number(button.dataset.zoomLevel) || 1;
            viewerState.zoom = level;
            el.galleryViewerZoomButtons.forEach(btn => btn.classList.toggle('active', btn === button));
            applyViewerZoom(viewerState.variants[viewerState.currentVariant]);
        });
    });

    // Background controls
    el.newBackgroundBtn?.addEventListener('click', openBackgroundModal);
    el.backgroundModalClose?.addEventListener('click', closeBackgroundModal);
    el.backgroundModalCancel?.addEventListener('click', closeBackgroundModal);
    el.backgroundModalCreate?.addEventListener('click', handleBackgroundGeneration);
    el.backgroundModal?.addEventListener('click', (event) => {
        if (event.target === el.backgroundModal) {
            closeBackgroundModal();
        }
    });
    el.openBackgroundGallery?.addEventListener('click', openBackgroundGalleryDrawer);
    el.backgroundGalleryClose?.addEventListener('click', closeBackgroundGalleryDrawer);
    el.resetBackgroundBtn?.addEventListener('click', async () => {
        await resetBackground();
        renderBackgroundGallery();
    });
    el.backgroundGallery?.addEventListener('click', (event) => {
        if (event.target === el.backgroundGallery) {
            closeBackgroundGalleryDrawer();
        }
    });

    // Accessibility controls
    el.accessibilityBtn?.addEventListener('click', toggleAccessibilityPanel);
    el.accessibilityClose?.addEventListener('click', closeAccessibilityPanel);
    el.largeTextToggle?.addEventListener('change', handleLargeTextToggle);
    el.reduceMotionToggle?.addEventListener('change', handleReduceMotionToggle);

    // Ambient sound & mascots
    el.ambientSoundBtn?.addEventListener('click', toggleAmbientSound);
    window.addEventListener('mousemove', handleMascotParallax);

    // Prompt templates
    if (el.promptTemplates?.length) {
        el.promptTemplates.forEach(chip => {
            chip.addEventListener('click', () => applyPromptTemplate(chip.dataset.template));
        });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeAccessibilityPanel();
            closeBackgroundModal();
            closeBackgroundGalleryDrawer();
        }
        handleStageShortcuts(event);
    });

    // Stage zoom gesture support
    el.canvas?.addEventListener('wheel', (event) => {
        if (!event.ctrlKey) return;
        event.preventDefault();
        const factor = event.deltaY < 0 ? 1.1 : 0.9;
        applyStageZoom(factor);
    }, { passive: false });

    el.canvas?.addEventListener('pointerdown', (event) => {
        if (!event.altKey) return;
        event.preventDefault();
        const startY = event.clientY;
        const initialZoom = stageState.zoom;
        const onMove = (moveEvent) => {
            const delta = (moveEvent.clientY - startY) * -0.005;
            setStageZoom(initialZoom * (1 + delta));
        };
        const onUp = () => {
            window.removeEventListener('pointermove', onMove);
            window.removeEventListener('pointerup', onUp);
        };
        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', onUp);
    });
}

function drawCheckerboard() {
    if (!el.canvas || !el.ctx) return;
    const ctx = el.ctx;
    const size = 32;
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, el.canvas.width, el.canvas.height);

    ctx.fillStyle = '#334155';
    for (let y = 0; y < el.canvas.height; y += size) {
        for (let x = 0; x < el.canvas.width; x += size) {
            if ((x / size + y / size) % 2 === 0) {
                ctx.fillRect(x, y, size, size);
            }
        }
    }
}

// ============================================================
// Helper Functions
// ============================================================

function initCanvas() {
    if (!el.canvas || !el.ctx) return;
    el.canvas.width = 512;
    el.canvas.height = 512;
    
    // FIXED #8: Default to 100% zoom
    stageState.zoom = 1.0;
    if (el.zoomLevelLabel) {
        el.zoomLevelLabel.textContent = '100%';
    }
    
    // ALWAYS default to clear/transparent background
    stageState.backgroundMode = 'clear';
    stageState.transparency = true;
    
    // Set button states correctly
    if (typeof setStageBackgroundMode === 'function') {
        setStageBackgroundMode('clear');
    }
    
    // Clear canvas to transparent
    el.ctx.clearRect(0, 0, el.canvas.width, el.canvas.height);
}

function launchConfetti(message) {
    console.log('🎉', message);
    // Placeholder for confetti animation
}

const accessibilityState = {
    largeText: false,
    reduceMotion: false
};

function toggleAccessibilityPanel() {
    if (!el.accessibilityPanel) return;
    const isHidden = el.accessibilityPanel.classList.contains('hidden');
    el.accessibilityPanel.classList.toggle('hidden');
    if (el.accessibilityBtn) {
        el.accessibilityBtn.setAttribute('aria-expanded', String(!isHidden));
    }
}

function closeAccessibilityPanel() {
    el.accessibilityPanel?.classList.add('hidden');
    if (el.accessibilityBtn) {
        el.accessibilityBtn.setAttribute('aria-expanded', 'false');
    }
}

function handleLargeTextToggle(e) {
    accessibilityState.largeText = e.target.checked;
    document.body.classList.toggle('accessibility-large-text', e.target.checked);
    localStorage.setItem('accessibility-large-text', e.target.checked);
}

function handleReduceMotionToggle(e) {
    accessibilityState.reduceMotion = e.target.checked;
    document.body.classList.toggle('accessibility-reduce-motion', e.target.checked);
    localStorage.setItem('accessibility-reduce-motion', e.target.checked);
}

function toggleAmbientSound() {
    if (!ambientState.enabled) {
        ambientState.enabled = true;
        el.ambientSoundBtn?.setAttribute('aria-pressed', 'true');
        console.log('Ambient sound enabled (placeholder)');
    } else {
        ambientState.enabled = false;
        el.ambientSoundBtn?.setAttribute('aria-pressed', 'false');
        console.log('Ambient sound disabled');
    }
}

function handleMascotParallax(event) {
    if (accessibilityState.reduceMotion) return;
    const centerX = window.innerWidth / 2;
    const centerY = window.innerHeight / 2;
    const offsetX = (event.clientX - centerX) / centerX;
    const offsetY = (event.clientY - centerY) / centerY;
    
    mascotState.elements.forEach(mascot => {
        const depth = parseFloat(mascot.dataset.depth) || 0.5;
        const moveX = offsetX * depth * 20;
        const moveY = offsetY * depth * 20;
        mascot.style.transform = `translate(${moveX}px, ${moveY}px)`;
    });
}

// ============================================================
// Summoning Effect (Generation Animation)
// ============================================================

let summoningState = {
    active: false,
    particles: [],
    animationFrame: null
};

function startSummoningEffect() {
    if (accessibilityState.reduceMotion) return;
    if (summoningState.active) return;
    
    summoningState.active = true;
    const teleporterPlatform = document.querySelector('.teleporter-platform');
    if (!teleporterPlatform) return;
    
    // Add summoning class for enhanced glow
    teleporterPlatform.classList.add('summoning');
    
    // Create particle container
    let particleContainer = document.getElementById('summoningParticles');
    if (!particleContainer) {
        particleContainer = document.createElement('div');
        particleContainer.id = 'summoningParticles';
        particleContainer.className = 'summoning-particles';
        const stage = document.querySelector('.teleporter-stage');
        if (stage) stage.appendChild(particleContainer);
    }
    
    // FIXED #20: Create SD preview container in center
    let previewContainer = document.getElementById('summoningPreview');
    if (!previewContainer && el.canvas) {
        previewContainer = document.createElement('div');
        previewContainer.id = 'summoningPreview';
        previewContainer.className = 'summoning-preview';
        previewContainer.innerHTML = '<div class="summoning-preview__spinner"></div>';
        el.canvasStage?.appendChild(previewContainer);
    }
    
    // FIXED #20: Spawn particles more frequently for dramatic swirl
    summoningState.interval = setInterval(() => {
        if (!summoningState.active) return;
        createSummoningParticle(particleContainer);
    }, 50); // Increased frequency from 100ms to 50ms
}

function stopSummoningEffect() {
    summoningState.active = false;
    if (summoningState.interval) {
        clearInterval(summoningState.interval);
        summoningState.interval = null;
    }
    
    const teleporterPlatform = document.querySelector('.teleporter-platform');
    if (teleporterPlatform) {
        teleporterPlatform.classList.remove('summoning');
    }
    
    const particleContainer = document.getElementById('summoningParticles');
    if (particleContainer) {
        setTimeout(() => {
            particleContainer.remove();
        }, 2000);  // Let existing particles finish
    }
    
    // FIXED #20: Remove preview container
    const previewContainer = document.getElementById('summoningPreview');
    if (previewContainer) {
        setTimeout(() => {
            previewContainer.remove();
        }, 500);
    }
}

function createSummoningParticle(container) {
    const particle = document.createElement('div');
    particle.className = 'summoning-particle';
    
    // FIXED #20: Swirling spiral effect - spawn in wider circle, spiral inward
    const angle = Math.random() * Math.PI * 2;
    const radius = 50 + Math.random() * 10;  // Start further out: 50-60% from center
    const startX = 50 + Math.cos(angle) * radius;
    const startY = 50 + Math.sin(angle) * radius;
    
    particle.style.left = `${startX}%`;
    particle.style.top = `${startY}%`;
    
    // FIXED #20: Enhanced color palette with more vibrant options
    const colors = ['#68a4ff', '#b08bff', '#ff76b6', '#77f0c5', '#ffc86b', '#ff6b9d', '#6bffff'];
    particle.style.background = colors[Math.floor(Math.random() * colors.length)];
    
    // FIXED #20: Larger, more visible particles
    const size = Math.random() * 6 + 6;  // 6-12px (was 4-8px)
    particle.style.width = `${size}px`;
    particle.style.height = `${size}px`;
    
    // FIXED #20: Spiral animation with rotation
    const duration = Math.random() * 2 + 1.5;  // 1.5-3.5s for smoother swirl
    const rotation = Math.random() * 360;
    particle.style.animationDuration = `${duration}s`;
    particle.style.setProperty('--rotation', `${rotation}deg`);
    particle.style.setProperty('--start-angle', `${angle}rad`);
    
    container.appendChild(particle);
    
    // Remove after animation
    setTimeout(() => {
        particle.remove();
    }, duration * 1000);
}
