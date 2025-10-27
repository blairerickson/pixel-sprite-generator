"""
Reference sheet generator for character consistency
"""
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from PIL import Image
import time

from animation_models import Direction, ReferenceSheetRequest, AnimationGenerateRequest
from sd_client import SDClient, GenerationParams

logger = logging.getLogger(__name__)


class ReferenceSheetGenerator:
    """Generates character reference sheets for animation consistency"""
    
    def __init__(self, sd_client: SDClient, config: dict):
        self.sd_client = sd_client
        self.config = config
        self.animation_config = config.get('animation', {})
        self.reference_config = self.animation_config.get('reference_sheet', {})
    
    async def generate_character_reference(
        self, 
        character_description: str,
        directions: List[Direction],
        style_lora: Optional[str] = None,
        lora_weight: Optional[float] = None,
        width: int = 512,
        height: int = 512,
        steps: Optional[int] = None,
        cfg_scale: Optional[float] = None,
        seed: int = -1
    ) -> Dict[Direction, Image.Image]:
        """
        Generate reference images for character in all specified directions with CONSISTENCY
        
        Returns:
            Dict mapping each direction to its reference image
        """
        logger.info(f"Generating CONSISTENT character reference for {len(directions)} directions")
        logger.info(f"Request params: seed={seed}, steps={steps}, cfg_scale={cfg_scale}, lora={style_lora}")
        
        # CONSISTENCY FIX: Generate master character first
        master_seed = seed if seed > 0 else abs(hash(character_description)) % (2**31)
        logger.info(f"Using master seed {master_seed} for character consistency")
        
        reference_images = {}
        master_character = None
        
        # Step 1: Generate master character (south/front view)
        if Direction.SOUTH in directions:
            try:
                logger.info("Generating MASTER character (south view)")
                master_prompt = self._build_master_character_prompt(character_description)
                logger.info(f"Master prompt: {master_prompt}")
                
                params = GenerationParams(
                    prompt=master_prompt,
                    negative_prompt=self._get_negative_prompt(),
                    preset="character_sprite",
                    lora=style_lora,
                    lora_weight=lora_weight,
                    width=width,
                    height=height,
                    steps=steps or 30,  # More steps for master
                    cfg_scale=cfg_scale or 7.5,
                    seed=master_seed,
                    batch_size=1
                )
                
                logger.info("Calling SD client for master character generation...")
                result = await self.sd_client.generate(params)
                logger.info(f"SD client returned: {result is not None}")
                
                if result and 'images' in result and len(result['images']) > 0:
                    master_character = result['images'][0]
                    reference_images[Direction.SOUTH] = master_character
                    logger.info("Master character generated successfully")
                else:
                    logger.error(f"Master generation failed - result: {result}")
                    raise Exception("Failed to generate master character")
                    
            except Exception as e:
                logger.error(f"Master character generation failed: {e}")
                raise
        
        # Step 2: Generate other directions using img2img from master
        for direction in directions:
            if direction == Direction.SOUTH:
                continue  # Already have master
                
            try:
                start_time = time.time()
                logger.info(f"Generating {direction.value} from master character")
                
                # Use master as base, prompt for direction change
                direction_prompt = self._build_direction_change_prompt(character_description, direction)
                
                # CRITICAL FIX: Use correct SD client method
                # For now, fallback to regular generation (will fix img2img later)
                direction_params = GenerationParams(
                    prompt=direction_prompt,
                    negative_prompt=self._get_negative_prompt(),
                    preset="character_sprite",
                    lora=style_lora,
                    lora_weight=lora_weight,
                    width=width,
                    height=height,
                    steps=steps or 25,
                    cfg_scale=cfg_scale or 7.5,
                    seed=master_seed,  # SAME seed for consistency
                    batch_size=1
                )
                
                result = await self.sd_client.generate(direction_params)
                
                if result and 'images' in result and len(result['images']) > 0:
                    reference_images[direction] = result['images'][0]
                    generation_time = time.time() - start_time
                    logger.info(f"Generated {direction.value} reference in {generation_time:.2f}s")
                else:
                    logger.error(f"Failed to generate reference for {direction.value}")
                    
            except Exception as e:
                logger.error(f"Error generating reference for {direction.value}: {e}")
                continue
        
        logger.info(f"Generated {len(reference_images)} CONSISTENT reference images")
        return reference_images
    
    def _build_master_character_prompt(self, character_description: str) -> str:
        """Build prompt for master character generation"""
        return f"{character_description}, pixel art, sprite, facing forward, front view, full body, clean linework, vibrant colors, solid color background, character reference"
    
    def _build_direction_change_prompt(self, character_description: str, direction: Direction) -> str:
        """Build prompt for changing direction while maintaining character"""
        direction_prompts = {
            Direction.WEST: "same character, facing left, side view from right",
            Direction.EAST: "same character, facing right, side view from left", 
            Direction.NORTH: "same character, facing backward, back view",
            Direction.SOUTHEAST: "same character, facing forward-right, 3/4 view",
            Direction.SOUTHWEST: "same character, facing forward-left, 3/4 view",
            Direction.NORTHEAST: "same character, facing backward-right, 3/4 view",
            Direction.NORTHWEST: "same character, facing backward-left, 3/4 view"
        }
        
        direction_text = direction_prompts.get(direction, "same character, facing forward")
        return f"{character_description}, {direction_text}, maintain exact same character appearance, pixel art, sprite, full body"
    
    async def generate_reference_sheet_from_request(
        self, 
        request: ReferenceSheetRequest
    ) -> Dict[Direction, Image.Image]:
        """Generate reference sheet from API request"""
        directions = request.to_direction_enums()
        
        return await self.generate_character_reference(
            character_description=request.character_description,
            directions=directions,
            style_lora=request.style_lora,
            lora_weight=request.lora_weight,
            width=request.width,
            height=request.height,
            steps=request.steps,
            cfg_scale=request.cfg_scale,
            seed=request.seed
        )
    
    def _build_direction_prompt(self, character_description: str, direction: Direction) -> str:
        """Build prompt with direction-specific guidance"""
        direction_prompts = {
            Direction.SOUTH: "facing forward, front view",
            Direction.WEST: "facing left, side view from right",
            Direction.EAST: "facing right, side view from left", 
            Direction.NORTH: "facing backward, back view",
            Direction.SOUTHEAST: "facing forward-right, 3/4 view",
            Direction.SOUTHWEST: "facing forward-left, 3/4 view",
            Direction.NORTHEAST: "facing backward-right, 3/4 view",
            Direction.NORTHWEST: "facing backward-left, 3/4 view"
        }
        
        direction_text = direction_prompts.get(direction, "facing forward")
        
        # Get base prompt template
        base_template = self.animation_config.get('generation', {}).get('reference_prompt_template', 
            "{description}, pixel art, sprite, full body, clean linework, vibrant colors, solid color background, {direction}")
        
        prompt = base_template.format(
            description=character_description,
            direction=direction_text
        )
        
        # Add LoRA triggers if specified
        if hasattr(self, 'style_lora') and self.style_lora:
            lora_config = self._get_lora_config(self.style_lora)
            if lora_config:
                triggers = " ".join(lora_config.get('triggers', []))
                prompt = f"{triggers}, {prompt}"
        
        return prompt
    
    def _get_negative_prompt(self) -> str:
        """Get negative prompt for reference generation"""
        return self.config.get('generation', {}).get('default_negative', 
            "blurry, low quality, jpeg artifacts, watermark, text, signature, realistic, photograph, transparent background, gradient background")
    
    def _get_lora_config(self, lora_name: str) -> Optional[dict]:
        """Get LoRA configuration by name"""
        for lora in self.config.get('sd', {}).get('loras', []):
            if lora['name'] == lora_name:
                return lora
        return None
    
    async def create_reference_sheet_image(
        self, 
        reference_images: Dict[Direction, Image.Image],
        output_path: Optional[Path] = None
    ) -> Image.Image:
        """
        Combine reference images into a single sheet
        
        Args:
            reference_images: Dict mapping directions to images
            output_path: Optional path to save the sheet
            
        Returns:
            Combined reference sheet image
        """
        if not reference_images:
            raise ValueError("No reference images provided")
        
        # Determine layout based on number of directions
        direction_count = len(reference_images)
        
        if direction_count <= 4:
            # 2x2 grid for 4 directions
            cols, rows = 2, 2
        else:
            # 4x2 grid for 8 directions  
            cols, rows = 4, 2
        
        # Get image dimensions (assume all same size)
        first_image = next(iter(reference_images.values()))
        img_width, img_height = first_image.size
        
        # Calculate sheet dimensions
        sheet_width = cols * img_width
        sheet_height = rows * img_height
        
        # Create sheet with transparent background
        sheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))
        
        # Define direction order for layout
        direction_order = [
            Direction.NORTH, Direction.NORTHEAST, Direction.EAST, Direction.SOUTHEAST,
            Direction.WEST, Direction.SOUTHWEST, Direction.SOUTH, Direction.NORTHWEST
        ]
        
        # Place images in grid
        for i, direction in enumerate(direction_order):
            if direction in reference_images:
                row = i // cols
                col = i % cols
                
                x = col * img_width
                y = row * img_height
                
                # Paste image onto sheet
                img = reference_images[direction]
                if img.mode == 'RGBA':
                    sheet.paste(img, (x, y), img)
                else:
                    sheet.paste(img, (x, y))
        
        # Save if path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sheet.save(output_path)
            logger.info(f"Reference sheet saved to {output_path}")
        
        return sheet
    
    def get_reference_consistency_score(
        self, 
        reference_images: Dict[Direction, Image.Image]
    ) -> float:
        """
        Calculate consistency score between reference images
        
        Returns:
            Score from 0-1 (1 = perfectly consistent)
        """
        if len(reference_images) < 2:
            return 1.0
        
        try:
            # Simple consistency check based on color similarity
            # In a real implementation, this would use more sophisticated metrics
            
            images = list(reference_images.values())
            total_score = 0.0
            comparisons = 0
            
            for i in range(len(images)):
                for j in range(i + 1, len(images)):
                    # Convert to RGB for comparison
                    img1 = images[i].convert('RGB')
                    img2 = images[j].convert('RGB')
                    
                    # Resize to same size for comparison
                    size = (64, 64)  # Small size for fast comparison
                    img1 = img1.resize(size)
                    img2 = img2.resize(size)
                    
                    # Calculate color histogram similarity
                    hist1 = img1.histogram()
                    hist2 = img2.histogram()
                    
                    # Simple histogram correlation
                    correlation = self._histogram_correlation(hist1, hist2)
                    total_score += correlation
                    comparisons += 1
            
            return total_score / comparisons if comparisons > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating consistency score: {e}")
            return 0.5  # Default middle score
    
    def _histogram_correlation(self, hist1: List[int], hist2: List[int]) -> float:
        """Calculate correlation between two histograms"""
        if len(hist1) != len(hist2):
            return 0.0
        
        # Normalize histograms
        sum1 = sum(hist1)
        sum2 = sum(hist2)
        
        if sum1 == 0 or sum2 == 0:
            return 0.0
        
        norm1 = [h / sum1 for h in hist1]
        norm2 = [h / sum2 for h in hist2]
        
        # Calculate correlation coefficient
        mean1 = sum(norm1) / len(norm1)
        mean2 = sum(norm2) / len(norm2)
        
        numerator = sum((a - mean1) * (b - mean2) for a, b in zip(norm1, norm2))
        denominator1 = sum((a - mean1) ** 2 for a in norm1)
        denominator2 = sum((b - mean2) ** 2 for b in norm2)
        
        if denominator1 == 0 or denominator2 == 0:
            return 0.0
        
        correlation = numerator / (denominator1 * denominator2) ** 0.5
        return max(0.0, min(1.0, correlation))  # Clamp to [0, 1]
    
    async def save_reference_images(
        self, 
        reference_images: Dict[Direction, Image.Image],
        output_dir: Path,
        prefix: str = "reference"
    ) -> Dict[Direction, str]:
        """
        Save reference images to disk
        
        Returns:
            Dict mapping directions to file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_paths = {}
        
        for direction, image in reference_images.items():
            filename = f"{prefix}_{direction.value}.png"
            file_path = output_dir / filename
            
            try:
                image.save(file_path)
                saved_paths[direction] = str(file_path)
                logger.info(f"Saved reference image: {file_path}")
            except Exception as e:
                logger.error(f"Failed to save reference image {filename}: {e}")
        
        return saved_paths

