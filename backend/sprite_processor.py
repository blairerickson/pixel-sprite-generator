"""
Sprite sheet processor with background removal and extraction
"""
import asyncio
import csv
import os
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageFilter, ImageOps
import cv2
import logging

logger = logging.getLogger(__name__)

class SpriteProcessor:
    """Process sprite sheets - remove backgrounds and extract individual sprites"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bg_config = config['sprite_processing']['background_removal']
        self.extract_config = config['sprite_processing']['sprite_extraction']
        self.output_config = config['sprite_processing'].get('output', {})
        self.qc_config = config['sprite_processing'].get('quality_control', {})
        self.pixel_config = self.bg_config.get('preprocess', {})

    def finalize_pixel_art(self, image: Image.Image) -> Tuple[Image.Image, Optional[Image.Image], Dict[str, Any]]:
        """Quantize/downscale while keeping pixel structure. Returns (base, preview, meta)."""
        base = image.convert('RGBA') if image.mode != 'RGBA' else image.copy()

        cfg = self.pixel_config
        target_size = max(1, int(cfg.get('target_size', 64)))
        palette_size = max(8, min(256, int(cfg.get('palette_size', 16))))
        upscale_factor = max(1, int(cfg.get('export_upscale', 4)))

        width, height = base.size
        max_dim = max(width, height)
        scale = max(max_dim / target_size, 1)
        new_width = max(1, int(round(width / scale)))
        new_height = max(1, int(round(height / scale)))

        quantize_kwargs = {
            'colors': palette_size,
            'dither': Image.Dither.NONE
        }

        try:
            quantize_kwargs['method'] = 2  # Fast octree works for RGBA
            paletted = base.quantize(**quantize_kwargs).convert('RGBA')
        except ValueError:
            quantize_kwargs['method'] = 3  # libimagequant fallback
            paletted = base.quantize(**quantize_kwargs).convert('RGBA')

        small = paletted.resize((new_width, new_height), Image.Resampling.NEAREST)

        # Harden alpha channel to eliminate halo artifacts from partial transparency
        alpha_threshold = max(0, min(255, int(cfg.get('alpha_threshold', 160))))
        data = np.array(small)
        alpha_channel = data[:, :, 3]
        transparent_mask = alpha_channel < alpha_threshold
        if np.any(transparent_mask):
            data[transparent_mask, 3] = 0
            # Clear RGB for transparent pixels to avoid white bleed
            data[transparent_mask, :3] = 0
            small = Image.fromarray(data, 'RGBA')

        preview = None
        if upscale_factor > 1:
            preview = small.resize(
                (new_width * upscale_factor, new_height * upscale_factor),
                Image.Resampling.NEAREST
            )

        metadata = {
            'target_size': target_size,
            'palette_size': palette_size,
            'alpha_threshold': alpha_threshold,
            'scaled_width': new_width,
            'scaled_height': new_height,
            'upscale_factor': upscale_factor
        }

        return small, preview, metadata
    
    async def remove_background(
        self,
        image: Image.Image,
        output_dir: Optional[Path] = None,
        prefix: str = "image"
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """Remove background from image and return QC metadata."""
        method = self.bg_config['method']

        preprocess_enabled = self.pixel_config.get('enabled', False)
        preprocessed_for_mask = self._preprocess_image(image) if preprocess_enabled else image

        if method == 'chromakey':
            # First, preprocess to create true pixel art (resize + palette)
            working_image = preprocessed_for_mask

            # Check if image already has magenta edges (from inpainting)
            has_magenta_edges = self._check_for_magenta_edges(working_image)

            if not has_magenta_edges:
                # Inject magenta background for consistent chromakey removal
                logger.info("[Background Removal] No magenta edges detected, injecting background")
                working_image = self._inject_magenta_background(working_image)
            else:
                logger.info("[Background Removal] Pure magenta edges detected (inpaint mode), skipping injection")

            return await self._remove_chromakey(working_image, output_dir=output_dir, prefix=prefix)
        elif method == 'rembg':
            # Try rembg with safety checks. If preprocessing is enabled, use the simplified
            # version for mask estimation while retaining the original for outline restoration.
            processed, qc_info = await self._remove_rembg_safe(preprocessed_for_mask, original_image=image)
            return processed, qc_info
        elif method == 'transparent-background':
            processed = await self._remove_transparent_background(preprocessed_for_mask)
            return processed, self._default_qc_info(passed=True, method_used='transparent-background')
        else:
            raise ValueError(f"Unsupported background removal method: {method}")
    
    def _check_for_magenta_edges(self, image: Image.Image) -> bool:
        """Check if image already has pure magenta (#FF00FF) edges (from inpainting)"""
        import numpy as np
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        data = np.array(image)
        height, width = data.shape[:2]
        
        # Sample edge pixels (top, bottom, left, right rows)
        edge_size = min(20, width // 10, height // 10)
        edge_pixels = np.concatenate([
            data[0:edge_size, :].reshape(-1, 3),  # Top edge
            data[-edge_size:, :].reshape(-1, 3),  # Bottom edge
            data[:, 0:edge_size].reshape(-1, 3),  # Left edge
            data[:, -edge_size:].reshape(-1, 3),  # Right edge
        ])
        
        # Check if majority of edge pixels are pure magenta (255, 0, 255)
        magenta = np.array([255, 0, 255])
        distances = np.linalg.norm(edge_pixels - magenta, axis=1)
        magenta_pixels = np.sum(distances < 5)  # Very tight tolerance for pure magenta
        
        magenta_percentage = (magenta_pixels / len(edge_pixels)) * 100
        
        logger.info(f"[Background Check] Edge magenta coverage: {magenta_percentage:.1f}%")
        
        # If >80% of edges are pure magenta, assume inpainting was used
        return magenta_percentage > 80
    
    def _inject_magenta_background(self, image: Image.Image) -> Image.Image:
        """Flood-fill from image edges to replace background with magenta."""
        import numpy as np
        from collections import deque

        # Ensure RGB processing
        if image.mode != 'RGB':
            image = image.convert('RGB')

        data = np.array(image)
        height, width = data.shape[:2]

        corner_size = min(20, width // 4, height // 4)
        corner_regions = [
            data[0:corner_size, 0:corner_size],
            data[0:corner_size, width - corner_size:width],
            data[height - corner_size:height, 0:corner_size],
            data[height - corner_size:height, width - corner_size:width]
        ]

        corner_colors = [region.mean(axis=(0, 1)).astype(int) for region in corner_regions]
        from collections import Counter
        color_counts = Counter([tuple(color) for color in corner_colors])
        background_color = np.array(color_counts.most_common(1)[0][0])

        tolerance = 25  # Conservative tolerance - avoid character edge bleeding

        logger.info(
            f"[Background Injection] Flood filling from edges with tolerance {tolerance} (bg RGB{tuple(background_color)})"
        )

        # Flood-fill mask from edges
        mask = np.zeros((height, width), dtype=bool)
        visited = np.zeros((height, width), dtype=bool)
        queue = deque()

        # Seed queue with multiple edge points to handle bands
        seed_margin = max(3, corner_size // 2)
        edge_points = []
        for x in range(0, width, max(1, width // 32)):
            edge_points.append((0, x))
            edge_points.append((height - 1, x))
        for y in range(0, height, max(1, height // 32)):
            edge_points.append((y, 0))
            edge_points.append((y, width - 1))

        # Also seed from sampled corner region to protect against quantization noise
        for y in range(seed_margin):
            for x in range(seed_margin):
                edge_points.append((y, x))
                edge_points.append((y, width - 1 - x))
                edge_points.append((height - 1 - y, x))
                edge_points.append((height - 1 - y, width - 1 - x))

        def within_tolerance(pixel: np.ndarray) -> bool:
            return np.linalg.norm(pixel.astype(int) - background_color.astype(int)) <= tolerance

        for point in edge_points:
            queue.append(point)

        while queue:
            y, x = queue.popleft()
            if y < 0 or y >= height or x < 0 or x >= width:
                continue
            if visited[y, x]:
                continue
            visited[y, x] = True

            if within_tolerance(data[y, x]):
                mask[y, x] = True
                queue.extend([(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)])

        magenta = np.array([255, 0, 255])
        if np.sum(mask) > 0:
            from scipy.ndimage import binary_erosion
            # Apply 3px erosion to keep magenta further from sprite edges
            eroded_mask = binary_erosion(mask, structure=np.ones((3, 3)), iterations=3)

            eroded_count = np.count_nonzero(eroded_mask)
            logger.info(
                f"[Background Injection] Flood fill covered {np.count_nonzero(mask)} pixels; after 3px erosion: {eroded_count}"
            )

            data[eroded_mask] = magenta
        else:
            logger.info("[Background Injection] Flood fill found no pixels to replace")

        return Image.fromarray(data, 'RGB')
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Apply preprocessing to simplify colors (like converting to GIF palette)"""
        preprocess_cfg = self.bg_config.get('preprocess', {})
        if not preprocess_cfg.get('enabled', False):
            return image
        
        working = image.convert('RGB')  # Start with RGB (no alpha)
        original_size = working.size
        logger.info("[Preprocess] Starting palette simplification (GIF-like)")
        
        # Optional: Resize to smaller size for cleaner pixel art
        resize_enabled = preprocess_cfg.get('resize_for_quality', False)
        if resize_enabled:
            target_size = preprocess_cfg.get('target_size', 64)
            logger.info(f"[Preprocess] Resizing from {original_size} to {target_size}x{target_size} (NEAREST neighbor)")
            working = working.resize((target_size, target_size), Image.Resampling.NEAREST)
        
        # Get palette size
        palette_size = max(8, min(256, preprocess_cfg.get('palette_size', 24)))
        
        # Convert to indexed color (P mode) - this is what GIF does
        logger.info(f"[Preprocess] Converting to {palette_size}-color palette (no dithering)")
        
        # Use adaptive palette with NO dithering for clean pixel art
        paletted = working.quantize(colors=palette_size, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        
        logger.info(f"[Preprocess] Palette mode: {paletted.mode}, unique colors: {len(paletted.getcolors())}")
        
        # Convert back to RGB to get solid colors
        simplified = paletted.convert('RGB')
        
        # Resize back to original if we downscaled (CRITICAL: Use NEAREST for pixel-perfect scaling)
        if resize_enabled and simplified.size != original_size:
            logger.info(f"[Preprocess] Upscaling back to {original_size} (NEAREST neighbor - preserves chunky pixels)")
            simplified = simplified.resize(original_size, Image.Resampling.NEAREST)
        
        # Now convert to RGBA for further processing
        result = simplified.convert('RGBA')
        
        logger.info(f"[Preprocess] Palette reduction complete - {palette_size} colors, solid backgrounds")
        
        return result

    def _default_qc_info(self, **overrides) -> Dict[str, Any]:
        info = {
            "passed": False,
            "method_used": self.bg_config.get('method', 'chromakey'),
            "background_percent": None,
            "sprite_percent": None,
            "component_count": None,
            "fallback_used": False,
            "notes": []
        }
        info.update(overrides)
        return info

    def _save_debug_image(self, image: Image.Image, output_dir: Optional[Path], filename: str) -> Optional[str]:
        if not output_dir or not self.qc_config.get('export_debug', False):
            return None
        output_dir.mkdir(parents=True, exist_ok=True)
        debug_path = output_dir / filename
        image.save(debug_path)
        return str(debug_path)
    
    def _sample_corners(self, image: Image.Image, sample_size: int = 20) -> list:
        """Sample all 4 corners of the image."""
        # Convert to numpy for processing
        data = np.array(image.convert('RGBA'))
        
        # Sample all 4 corners
        corner_size = max(5, min(sample_size, image.width // 20, image.height // 20))
        
        corners = [
            data[0:corner_size, 0:corner_size, :3],  # Top-left
            data[0:corner_size, -corner_size:, :3],  # Top-right
            data[-corner_size:, 0:corner_size, :3],  # Bottom-left
            data[-corner_size:, -corner_size:, :3],  # Bottom-right
        ]
        
        return corners
    
    def _get_average_color(self, corner_data: np.ndarray) -> tuple:
        """Get the average color of a corner region."""
        return tuple(corner_data.mean(axis=(0,1)).astype(int))

    def _ensure_solid_background(self, image: Image.Image, output_dir: Optional[Path] = None, prefix: str = "image") -> Tuple[Image.Image, Dict[str, Any]]:
        """Ensure the image has a solid background by adding white if corners are inconsistent."""
        # Sample all 4 corners
        corners = self._sample_corners(image, sample_size=20)
        
        # Check if all corners are similar (solid background)
        corner_colors = [self._get_average_color(corner) for corner in corners]
        max_distance = 0
        
        for i in range(len(corner_colors)):
            for j in range(i+1, len(corner_colors)):
                distance = np.sqrt(sum((a-b)**2 for a, b in zip(corner_colors[i], corner_colors[j])))
                max_distance = max(max_distance, distance)
        
        # If corners are too different (not solid background), add white background
        qc = {
            "corner_max_distance": round(max_distance, 2),
            "corner_colors": corner_colors,
            "white_background_added": False
        }

        if max_distance > 30:  # Lower threshold for more aggressive white background enforcement
            logger.info(f"[Background Removal] Corners too different (max distance: {max_distance:.1f}), adding solid white background")
            
            # Create a white background
            white_bg = Image.new('RGBA', image.size, (255, 255, 255, 255))
            
            # Composite the original image over white background
            # This ensures any transparent areas become white
            result = Image.alpha_composite(white_bg, image.convert('RGBA'))
            qc["white_background_added"] = True

            if self.bg_config.get('save_debug_mask', False) and output_dir:
                self._save_debug_image(image, output_dir, f"{prefix}_pre_white.png")
                self._save_debug_image(result, output_dir, f"{prefix}_post_white.png")

            return result, qc
        
        return image, qc

    async def _remove_chromakey(
        self,
        image: Image.Image,
        output_dir: Optional[Path] = None,
        prefix: str = "image"
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """Remove background using smart corner sampling"""
        # Preprocess
        image = self._preprocess_image(image)

        # Ensure we have a solid background first
        image, bg_qc = self._ensure_solid_background(image, output_dir=output_dir, prefix=prefix)
        
        # Convert to RGBA if needed
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Convert to numpy for processing
        data = np.array(image)

        qc_info = self._default_qc_info()

        debug_mask_path = None
        
        # Sample all 4 corners to find the most likely background color
        corner_size = max(5, min(20, image.width // 20, image.height // 20))
        
        corners = [
            data[0:corner_size, 0:corner_size, :3],  # Top-left
            data[0:corner_size, -corner_size:, :3],  # Top-right
            data[-corner_size:, 0:corner_size, :3],  # Bottom-left
            data[-corner_size:, -corner_size:, :3],  # Bottom-right
        ]
        
        corner_colors = [corner.mean(axis=(0,1)).astype(int) for corner in corners]
        
        print(f"[Background Removal] Sampled {corner_size}x{corner_size} from each corner:")
        for i, color in enumerate(corner_colors):
            corner_names = ['Top-Left', 'Top-Right', 'Bottom-Left', 'Bottom-Right']
            print(f"  {corner_names[i]}: RGB{tuple(color)}")
        
        # Find the most common corner color (likely the background)
        # Strategy: Pick the color that appears in the most corners with similar values
        def colors_similar(c1, c2, threshold=30):
            return np.sqrt(np.sum((np.array(c1) - np.array(c2))**2)) < threshold
        
        # Count how many corners match each color
        color_votes = []
        for i, color in enumerate(corner_colors):
            votes = sum(1 for c in corner_colors if colors_similar(color, c, 30))
            color_votes.append((votes, i, color))
        
        # Pick the color with most votes
        color_votes.sort(reverse=True)
        target_color = tuple(color_votes[0][2])
        votes = color_votes[0][0]
        
        print(f"[Background Removal] Selected background color: RGB{target_color} ({votes}/4 corners agree)")
        
        # If corners don't agree well (less than 3/4), use default magenta background
        if votes < 3:
            default_bg = self.bg_config.get('default_background_color', '#FF00FF')
            # Convert hex to RGB
            if default_bg.startswith('#'):
                hex_color = default_bg.lstrip('#')
                target_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                print(f"[Background Removal] Corners don't agree ({votes}/4), using default: RGB{target_color}")
            else:
                print(f"[Background Removal] Using default background: {default_bg}")
        
        # Get chromakey settings with better defaults for pixel art
        chromakey_config = self.bg_config.get('chromakey', {})
        base_tolerance = chromakey_config.get('tolerance', 15)  # Increased for better edge handling
        preserve_outlines = chromakey_config.get('preserve_outlines', True)
        outline_strength = chromakey_config.get('outline_preservation_strength', 3)
        
        # Calculate color distance in RGB space
        red, green, blue, alpha = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
        
        color_distance = np.sqrt(
            (red - target_color[0])**2 +
            (green - target_color[1])**2 +
            (blue - target_color[2])**2
        )
        
        # Analyze the color distribution
        unique_distances = np.unique(color_distance[color_distance > 0])
        if len(unique_distances) > 0:
            min_distance = unique_distances.min()
            max_distance = unique_distances.max()
            median_distance = np.median(unique_distances)
            print(f"[Background Removal] Color distances - Min: {min_distance:.1f}, Median: {median_distance:.1f}, Max: {max_distance:.1f}")
        
        # Try with the specified tolerance first
        tolerance = base_tolerance
        first_stage_mask = color_distance <= tolerance
        mask = first_stage_mask.copy()
        test_removal = (np.sum(mask) / mask.size) * 100
        
        print(f"[Background Removal] Tolerance {tolerance}: Would remove {test_removal:.1f}%")
        
        # If that removes everything, try adaptive tolerance
        if test_removal > 95:
            # Find a better tolerance - use the gap between background and sprite
            if len(unique_distances) > 10:
                # Find the smallest non-zero distance (likely the sprite edge)
                sprite_edge_distance = unique_distances[unique_distances > 2][0] if len(unique_distances[unique_distances > 2]) > 0 else 10
                tolerance = max(3, sprite_edge_distance * 0.5)  # Use half the sprite edge distance
                print(f"[Background Removal] Auto-adjusting tolerance to {tolerance:.1f} (sprite detected at distance {sprite_edge_distance:.1f})")
                mask = color_distance <= tolerance
            else:
                print(f"[Background Removal] WARNING: Image appears monochromatic - skipping removal")
                return image
        
        # Calculate what we're about to remove
        pixels_to_remove = np.sum(mask)
        total_pixels = mask.size
        removal_percent = (pixels_to_remove / total_pixels) * 100
        
        print(f"[Background Removal] Would remove {pixels_to_remove}/{total_pixels} pixels ({removal_percent:.1f}%)")
        
        # Safety check: if removing >95% or <3%, likely detection error
        if removal_percent > 95:
            print(f"[Background Removal] WARNING: Would remove >95% of image!")
            print(f"[Background Removal] WARNING: The sprite likely matches the background color.")
            print(f"[Background Removal] Returning original image unchanged.")
            return image  # Return original
        
        if removal_percent < 3:
            print(f"[Background Removal] WARNING: Would remove <3% of image!")
            print(f"[Background Removal] Background may not be solid or prompt missing 'background' keyword.")
            print(f"[Background Removal] Continuing anyway...")
        
        if 40 <= removal_percent <= 80:
            print(f"[Background Removal] OK: Removal percentage looks good - background detected")
        
        # Save initial mask for debugging
        if self.bg_config.get('save_debug_mask', False) and output_dir:
            debug_mask_img = Image.fromarray((mask * 255).astype(np.uint8), mode='L')
            debug_mask_filename = f"{prefix}_mask_stage1.png"
            debug_mask_path = self._save_debug_image(debug_mask_img, output_dir, debug_mask_filename)

        # Set alpha to 0 where mask is True
        data[mask, 3] = 0
        
        # Optional: clean up stray pixels (noise reduction)
        # If a transparent pixel has mostly opaque neighbors, make it opaque
        # If an opaque pixel has mostly transparent neighbors, make it transparent
        if self.bg_config.get('noise_reduction', True):
            from scipy.ndimage import binary_closing, binary_opening
            
            alpha_mask = data[:,:,3] > 0
            # Clean up small holes
            alpha_mask = binary_closing(alpha_mask, structure=np.ones((3,3)))
            # Remove small islands
            alpha_mask = binary_opening(alpha_mask, structure=np.ones((2,2)))
            
            data[:,:,3] = np.where(alpha_mask, data[:,:,3], 0)
        
        # Preserve black outlines if enabled
        if preserve_outlines and outline_strength > 0:
            logger.info(f"[Background Removal] Preserving black outlines (strength: {outline_strength})")
            
            # Find dark pixels (potential black outlines)
            rgb = data[:, :, :3]
            darkness = np.mean(rgb, axis=2)
            
            # Dark pixels are those with low brightness (potential outlines)
            dark_threshold = 80 - (outline_strength * 10)  # Lower threshold = more aggressive outline detection
            dark_pixels = darkness < dark_threshold
            
            # Find pixels that are dark AND have some transparency (outlines that got partially removed)
            outline_candidates = dark_pixels & (data[:, :, 3] < 255) & (data[:, :, 3] > 0)
            
            if np.any(outline_candidates):
                # Restore these pixels to full opacity
                data[outline_candidates, 3] = 255
                
                # Also restore pixels around outlines (dilate outline mask)
                if outline_strength >= 2:
                    from scipy.ndimage import binary_dilation
                    outline_mask = outline_candidates
                    dilated_outlines = binary_dilation(outline_mask, structure=np.ones((3, 3)))
                    
                    # Restore dilated outline areas to full opacity
                    restore_mask = dilated_outlines & (data[:, :, 3] > 0) & (data[:, :, 3] < 255)
                    data[restore_mask, 3] = 255
                
                logger.info(f"[Background Removal] Restored {np.sum(outline_candidates)} outline pixels")
            else:
                logger.info("[Background Removal] No outline pixels found to restore")

        # Histogram-based refinement: DISABLED for now to diagnose artifacts
        # This was removing sprite pixels that matched the dominant background color
        # histogram_bins = self.bg_config.get('histogram_bins', 16)
        # alpha_channel = data[:,:,3]
        # flat_pixels = data[:,:,:3].reshape(-1, 3)
        # hist, edges = np.histogramdd(flat_pixels, bins=histogram_bins, range=((0,255),(0,255),(0,255)))
        # dominant_bin_idx = np.unravel_index(np.argmax(hist), hist.shape)
        # dominant_color = [
        #     int((edges[i][idx] + edges[i][idx+1]) / 2)
        #     for i, idx in enumerate(dominant_bin_idx)
        # ]
        # dominant_color = np.array(dominant_color)
        # hist_mask = np.linalg.norm(flat_pixels - dominant_color, axis=1).reshape(alpha_channel.shape) <= max(5, tolerance)
        # combined_mask = np.logical_or(mask, hist_mask)
        # data[combined_mask, 3] = 0
        # mask = combined_mask
        
        alpha_channel = data[:,:,3]
        
        # Mask refinement (morphological operations)
        mask_refine = self.bg_config.get('mask_refine', {})
        if mask_refine.get('enabled', False):
            kernel_size = max(1, int(mask_refine.get('kernel', 3)))
            iterations = max(1, int(mask_refine.get('iterations', 1)))
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            refined_mask = cv2.dilate(mask.astype(np.uint8), kernel, iterations=iterations)
            refined_mask = cv2.erode(refined_mask, kernel, iterations=iterations)
            data[refined_mask.astype(bool), 3] = 0

        # Quality metrics
        alpha_channel = data[:,:,3]
        transparent_pixels = np.sum(alpha_channel == 0)
        opaque_pixels = np.sum(alpha_channel > 0)
        total_pixels = alpha_channel.size
        background_percent = (transparent_pixels / total_pixels) * 100
        sprite_percent = (opaque_pixels / total_pixels) * 100

        qc_info.update({
            "passed": True,
            "background_percent": round(background_percent, 2),
            "sprite_percent": round(sprite_percent, 2),
            "method_used": "chromakey",
            "component_count": None,
            "debug_mask": debug_mask_path
        })
        qc_info['notes'].append(f"Corner max distance: {bg_qc.get('corner_max_distance')}")
        if bg_qc.get('white_background_added'):
            qc_info['notes'].append('White background enforced pre-removal')
        print(f"[Background Removal] Complete - transparent background applied (background {background_percent:.1f}%)")
        
        processed_image = Image.fromarray(data, 'RGBA')
        
        if debug_mask_path:
            qc_info["debug_mask"] = debug_mask_path
        
        return processed_image, qc_info
    
    async def _remove_rembg_safe(
        self,
        image: Image.Image,
        original_image: Optional[Image.Image] = None
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """Remove background using rembg with pixel art optimizations and safety checks"""
        try:
            from rembg import remove, new_session
            
            rembg_config = self.bg_config.get('rembg', {})
            chromakey_config = self.bg_config.get('chromakey', {})
            
            # Check if we should skip rembg for pixel art
            if rembg_config.get('force_chromakey_for_pixel_art', False):
                logger.info("[Background Removal] Pixel art mode - skipping rembg, using chromakey")
                return await self._remove_chromakey(original_image or image)
            
            logger.info("[Background Removal] Trying rembg (AI-based removal)...")
            
            # Get rembg model (some models work better for different content)
            model = rembg_config.get('model', 'u2net')
            logger.info(f"[Background Removal] Using rembg model: {model}")
            
            # Create rembg session with specific model
            loop = asyncio.get_event_loop()
            session = await loop.run_in_executor(None, new_session, model)
            
            # Run rembg removal
            output = await loop.run_in_executor(None, lambda: remove(image, session=session))
            
            # Safety check: Calculate transparency percentage
            if output.mode == 'RGBA':
                import numpy as np
                data = np.array(output)
                alpha = data[:, :, 3]
                total_pixels = alpha.size
                transparent_pixels = np.sum(alpha < 128)  # Count mostly-transparent pixels
                transparency_percent = (transparent_pixels / total_pixels) * 100
                
                logger.info(f"[Background Removal] Rembg removed {transparency_percent:.1f}% of image")
                
                # Check aggressiveness threshold (lowered from 90% to 75%)
                aggressiveness_threshold = rembg_config.get('aggressiveness_threshold', 75)
                if transparency_percent > aggressiveness_threshold:
                    logger.warning(f"[Background Removal] Rembg too aggressive ({transparency_percent:.1f}% > {aggressiveness_threshold}%), falling back to chromakey")
                    
                    # Fallback to chromakey method
                    return await self._remove_chromakey(original_image or image)
                
                # Apply pixel art optimizations if enabled
                if rembg_config.get('pixel_art_mode', True):
                    output = await self._post_process_rembg_for_pixel_art(output, rembg_config)
                
                # If removal looks reasonable, use rembg result
                qc_info = self._default_qc_info(
                    passed=True,
                    method_used='rembg',
                    background_percent=transparency_percent,
                    sprite_percent=100 - transparency_percent,
                    notes=[f'AI removal successful - {transparency_percent:.1f}% background removed', f'Model: {model}']
                )
                
                return output, qc_info
            else:
                # No alpha channel - rembg failed
                logger.warning("[Background Removal] Rembg produced no alpha channel, falling back to chromakey")
                return await self._remove_chromakey(original_image or image)
                
        except ImportError:
            logger.error("[Background Removal] rembg not installed, falling back to chromakey")
            return await self._remove_chromakey(original_image or image)
        except Exception as e:
            logger.error(f"[Background Removal] Rembg error: {e}, falling back to chromakey")
            return await self._remove_chromakey(image)
    
    async def _post_process_rembg_for_pixel_art(self, image: Image.Image, config: dict) -> Image.Image:
        """Post-process rembg output to better preserve pixel art characteristics"""
        import numpy as np
        from scipy.ndimage import binary_dilation, binary_erosion
        
        if image.mode != 'RGBA':
            return image
        
        logger.info("[Background Removal] Applying pixel art post-processing...")
        
        data = np.array(image)
        alpha = data[:, :, 3]
        
        # Create binary mask (non-transparent pixels)
        mask = alpha > 128
        
        # Dilate mask to preserve edges (prevents outline erosion)
        if config.get('post_process_mask', True):
            dilation_pixels = config.get('mask_dilation', 2)
            if dilation_pixels > 0:
                # Create structuring element for dilation
                structure = np.ones((dilation_pixels * 2 + 1, dilation_pixels * 2 + 1), dtype=bool)
                mask_dilated = binary_dilation(mask, structure=structure)
                
                # Apply dilation to alpha channel
                alpha_dilated = alpha.copy()
                alpha_dilated[mask_dilated] = 255  # Make dilated areas fully opaque
                
                # Preserve original sprite areas but expand slightly
                data[:, :, 3] = alpha_dilated
                
                logger.info(f"[Background Removal] Applied {dilation_pixels}px mask dilation to preserve edges")
        
        # Preserve black outlines if enabled
        if config.get('preserve_outlines', True):
            outline_threshold = config.get('outline_threshold', 50)
            
            # Find dark pixels (potential outlines)
            rgb = data[:, :, :3]
            darkness = np.mean(rgb, axis=2)
            dark_pixels = darkness < outline_threshold
            
            # Make dark pixels (outlines) more opaque
            outline_mask = dark_pixels & (alpha > 0)  # Only dark pixels that aren't fully transparent
            data[outline_mask, 3] = np.maximum(data[outline_mask, 3], 200)  # Ensure outlines are visible
            
            logger.info(f"[Background Removal] Preserved dark outlines (threshold: {outline_threshold})")
        
        return Image.fromarray(data, 'RGBA')
    
    async def _remove_rembg(self, image: Image.Image) -> Image.Image:
        """Remove background using rembg library (legacy, use _remove_rembg_safe instead)"""
        try:
            from rembg import remove
            
            loop = asyncio.get_event_loop()
            output = await loop.run_in_executor(None, remove, image)
            return output
        except ImportError:
            raise ImportError("rembg not installed. Install with: pip install rembg")
    
    async def _remove_transparent_background(self, image: Image.Image) -> Image.Image:
        """Remove background using transparent-background library"""
        try:
            from transparent_background import Remover
            
            # Initialize remover (cached)
            if not hasattr(self, '_tb_remover'):
                self._tb_remover = Remover()
            
            loop = asyncio.get_event_loop()
            output = await loop.run_in_executor(None, self._tb_remover.process, image)
            return output
        except ImportError:
            raise ImportError("transparent-background not installed. Install with: pip install transparent-background")
    
    async def extract_sprites(self, image: Image.Image) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Extract individual sprites from a sprite sheet and return QC info"""
        if not self.extract_config['enabled']:
            return [], {"passed": True, "component_count": 0, "notes": ["Extraction disabled"]}
        
        # Convert to RGBA
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Try auto-detection first
        if self.extract_config['auto_detect']:
            return await self._extract_sprites_auto(image)
        else:
            # Use grid-based extraction
            grid_size = self.extract_config['grid_size']
            if grid_size:
                sprites, qc = await self._extract_sprites_grid_qc(image, grid_size)
                return sprites, qc
            else:
                return await self._extract_sprites_auto(image)
    
    async def _extract_sprites_auto(self, image: Image.Image) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Auto-detect and extract sprites using connected components"""
        
        # Convert to numpy
        data = np.array(image)
        
        # Get alpha channel
        if data.shape[2] == 4:
            alpha = data[:,:,3]
        else:
            # If no alpha, use brightness
            gray = cv2.cvtColor(data, cv2.COLOR_RGB2GRAY)
            _, alpha = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
        
        # Morphological closing to merge nearby components before contouring
        kernel_size = max(1, int(self.extract_config.get('morphology_kernel', 3)))
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        closed_alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(closed_alpha, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"[Sprite Extraction] Found {len(contours)} contours in image")
        
        min_size = self.extract_config.get('min_sprite_size', 16)
        padding = self.extract_config.get('padding', 2)
        
        sprites = []
        solidity_threshold = self.extract_config.get('solidity_threshold', 0.2)
        
        filtered_size = 0
        filtered_aspect = 0
        filtered_transparency = 0
        filtered_solidity = 0
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter out too small sprites and weird artifacts
            if w < min_size or h < min_size:
                filtered_size += 1
                continue
            
            # Filter out very thin or very wide sprites (likely artifacts)
            aspect_ratio = w / h
            if aspect_ratio > 5 or aspect_ratio < 0.2:
                filtered_aspect += 1
                continue
            
            # Filter out sprites that are mostly transparent
            sprite_region = alpha[y:y+h, x:x+w]
            non_transparent_pixels = np.sum(sprite_region > 0)
            total_pixels = w * h
            if non_transparent_pixels / total_pixels < 0.3:  # Less than 30% visible pixels
                filtered_transparency += 1
                continue
            
            # Add padding
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(image.width, x + w + padding)
            y2 = min(image.height, y + h + padding)
            
            # Crop sprite
            sprite_img = image.crop((x1, y1, x2, y2))
            
            sprite_mask = alpha[y1:y2, x1:x2] > 0
            solidity = np.sum(sprite_mask) / ((x2 - x1) * (y2 - y1))
            if solidity < solidity_threshold:
                filtered_solidity += 1
                continue

            sprite_img = image.crop((x1, y1, x2, y2))
            sprites.append({
                'image': sprite_img,
                'bounds': (x1, y1, x2, y2),
                'size': (x2 - x1, y2 - y1),
                'original_bounds': (x, y, x + w, y + h),
                'qc': {
                    'solidity': round(solidity, 3),
                    'source_bounds': (x, y, x + w, y + h)
                }
            })
        
        # Sort sprites by position (left to right, top to bottom)
        sprites.sort(key=lambda s: (s['bounds'][1] // 50, s['bounds'][0]))
        
        print(f"[Sprite Extraction] Filtering summary:")
        print(f"  - Too small: {filtered_size}")
        print(f"  - Bad aspect ratio: {filtered_aspect}")
        print(f"  - Too transparent: {filtered_transparency}")
        print(f"  - Low solidity: {filtered_solidity}")
        print(f"  - Retained: {len(sprites)}")
        
        qc = {
            "passed": len(sprites) > 0,
            "component_count": len(sprites),
            "notes": [],
            "filtered": {
                "size": filtered_size,
                "aspect": filtered_aspect,
                "transparency": filtered_transparency,
                "solidity": filtered_solidity
            }
        }
        if not sprites:
            qc['notes'].append('No sprites detected after filtering')
        elif len(sprites) > self.qc_config.get('max_components', 10):
            qc['notes'].append('High number of sprite components')
        return sprites, qc
    
    async def _extract_sprites_grid_qc(self, image: Image.Image, grid_size: Tuple[int, int]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Extract sprites using a fixed grid with QC info"""
        sprite_width, sprite_height = grid_size
        padding = self.extract_config.get('padding', 0)
        
        sprites = []
        retained = 0
        
        for y in range(0, image.height, sprite_height):
            for x in range(0, image.width, sprite_width):
                # Calculate bounds
                x1 = x
                y1 = y
                x2 = min(x + sprite_width, image.width)
                y2 = min(y + sprite_height, image.height)
                
                # Crop sprite
                sprite_img = image.crop((x1, y1, x2, y2))
                
                # Check if sprite is not empty
                if self._is_sprite_empty(sprite_img):
                    continue
                
                # Trim if needed
                if padding:
                    sprite_img = self._trim_transparent(sprite_img, padding)
                
                retained += 1
                sprites.append({
                    'image': sprite_img,
                    'bounds': (x1, y1, x2, y2),
                    'size': (x2 - x1, y2 - y1),
                    'grid_position': (x // sprite_width, y // sprite_height)
                })
        qc = {
            'passed': retained > 0,
            'component_count': retained,
            'notes': [f'Grid extraction {grid_size}']
        }
        return sprites, qc
    
    def _is_sprite_empty(self, sprite: Image.Image) -> bool:
        """Check if sprite is empty (all transparent or white)"""
        if sprite.mode == 'RGBA':
            # Check alpha channel
            alpha = np.array(sprite)[:,:,3]
            return np.all(alpha < 10)
        else:
            # Check if mostly white
            data = np.array(sprite.convert('L'))
            return np.mean(data) > 250
    
    def _trim_transparent(self, sprite: Image.Image, padding: int = 0) -> Image.Image:
        """Trim transparent pixels from sprite"""
        if sprite.mode != 'RGBA':
            return sprite
        
        # Get bounding box of non-transparent pixels
        bbox = sprite.getbbox()
        
        if bbox:
            # Add padding
            x1, y1, x2, y2 = bbox
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(sprite.width, x2 + padding)
            y2 = min(sprite.height, y2 + padding)
            
            return sprite.crop((x1, y1, x2, y2))
        
        return sprite
    
    async def create_sprite_sheet(self, sprites: List[Image.Image], 
                                 columns: Optional[int] = None,
                                 padding: int = 2,
                                 background: Tuple[int, int, int, int] = (0, 0, 0, 0)) -> Image.Image:
        """Combine individual sprites into a sprite sheet"""
        
        if not sprites:
            raise ValueError("No sprites provided")
        
        # Determine grid layout
        if columns is None:
            # Auto-calculate columns (try to make square-ish)
            columns = int(np.ceil(np.sqrt(len(sprites))))
        
        rows = int(np.ceil(len(sprites) / columns))
        
        # Find max sprite size
        max_width = max(s.width for s in sprites)
        max_height = max(s.height for s in sprites)
        
        # Create sheet
        sheet_width = columns * max_width + (columns - 1) * padding
        sheet_height = rows * max_height + (rows - 1) * padding
        
        sheet = Image.new('RGBA', (sheet_width, sheet_height), background)
        
        # Place sprites
        for idx, sprite in enumerate(sprites):
            row = idx // columns
            col = idx % columns
            
            x = col * (max_width + padding)
            y = row * (max_height + padding)
            
            # Center sprite in cell
            x_offset = (max_width - sprite.width) // 2
            y_offset = (max_height - sprite.height) // 2
            
            sheet.paste(sprite, (x + x_offset, y + y_offset), sprite if sprite.mode == 'RGBA' else None)
        
        return sheet

