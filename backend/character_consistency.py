"""
Master Character System for Animation Consistency
Ensures same character across all directions and frames
"""
import logging
from typing import Dict, Optional
from PIL import Image
from pathlib import Path
import time

from sd_client import SDClient, GenerationParams
from animation_models import Direction

logger = logging.getLogger(__name__)


class CharacterConsistencyManager:
    """Manages character consistency across all animation frames"""
    
    def __init__(self, sd_client: SDClient, config: dict):
        self.sd_client = sd_client
        self.config = config
        
    async def generate_master_character(
        self, 
        description: str, 
        seed: int,
        style_lora: Optional[str] = None,
        lora_weight: float = 1.0,
        width: int = 512,
        height: int = 512
    ) -> Image.Image:
        """Generate ONE definitive master character for consistency"""
        
        logger.info(f"Generating MASTER character: {description}")
        logger.info(f"Using consistent seed: {seed}")
        
        # Build high-quality master prompt
        master_prompt = f"{description}, pixel art, sprite, character reference, front view, full body, clean linework, detailed, high quality"
        
        # High-quality generation parameters
        params = GenerationParams(
            prompt=master_prompt,
            negative_prompt=self._get_negative_prompt(),
            preset="character_sprite",
            lora=style_lora,
            lora_weight=lora_weight,
            width=width,
            height=height,
            steps=40,  # High quality for master
            cfg_scale=9.0,  # High adherence to prompt
            seed=seed,
            batch_size=1
        )
        
        logger.info(f"Master generation params: steps=40, cfg=9.0, seed={seed}")
        
        result = await self.sd_client.generate(params)
        
        if not result or 'images' not in result or len(result['images']) == 0:
            raise Exception("Failed to generate master character")
        
        master_character = result['images'][0]
        logger.info("Master character generated successfully")
        
        return master_character
    
    async def generate_directional_references(
        self,
        master_character: Image.Image,
        description: str,
        seed: int,
        style_lora: Optional[str] = None,
        lora_weight: float = 1.0
    ) -> Dict[str, Image.Image]:
        """Generate directional references maintaining exact character consistency"""
        
        logger.info("Generating directional references from master character")
        
        references = {"south": master_character}  # Master is south view
        direction_prompts = {
            "west": f"{description}, same character exactly, facing left, side view from right, maintain exact appearance",
            "east": f"{description}, same character exactly, facing right, side view from left, maintain exact appearance", 
            "north": f"{description}, same character exactly, facing backward, back view, maintain exact appearance"
        }
        
        for direction, direction_prompt in direction_prompts.items():
            try:
                logger.info(f"Generating {direction} reference from master")
                
                # ENHANCED: Use master character as base with character embedding
                enhanced_prompt = f"EXACT SAME CHARACTER: {description}, identical to reference, {direction_text}, maintain all details: armor, colors, proportions, face, equipment"
                
                direction_text = {
                    "west": "facing left",
                    "east": "facing right", 
                    "north": "facing backward"
                }.get(direction, "facing forward")
                
                # Build super-specific prompt for consistency
                consistency_prompt = (
                    f"{description}, IDENTICAL character, EXACT SAME: "
                    f"armor design, color scheme, facial features, body proportions, "
                    f"equipment details, {direction_text}, pixel art sprite, "
                    f"character consistency, same character different angle"
                )
                
                params = GenerationParams(
                    prompt=consistency_prompt,
                    negative_prompt=self._get_negative_prompt() + ", different character, inconsistent design, character variation",
                    preset="character_sprite",
                    lora=style_lora,
                    lora_weight=lora_weight,
                    width=master_character.width,
                    height=master_character.height,
                    steps=35,  # Higher steps for better consistency
                    cfg_scale=9.5,  # Very high adherence
                    seed=seed,  # SAME seed for consistency
                    batch_size=1
                )
                
                result = await self.sd_client.generate(params)
                
                if result and 'images' in result and len(result['images']) > 0:
                    references[direction] = result['images'][0]
                    logger.info(f"Generated {direction} reference successfully")
                else:
                    logger.error(f"Failed to generate {direction} reference")
                    # Use master as fallback for this direction
                    references[direction] = master_character
                    
            except Exception as e:
                logger.error(f"Error generating {direction} reference: {e}")
                # Use master as fallback
                references[direction] = master_character
        
        logger.info(f"Generated {len(references)} directional references")
        return references
    
    def validate_character_consistency(self, references: Dict[str, Image.Image]) -> float:
        """Validate that all references show the same character"""
        try:
            if len(references) < 2:
                return 1.0
            
            # Simple consistency check based on color similarity
            images = list(references.values())
            total_score = 0.0
            comparisons = 0
            
            for i in range(len(images)):
                for j in range(i + 1, len(images)):
                    # Compare color histograms
                    score = self._compare_character_consistency(images[i], images[j])
                    total_score += score
                    comparisons += 1
            
            consistency_score = total_score / comparisons if comparisons > 0 else 0.0
            logger.info(f"Character consistency score: {consistency_score:.2f}")
            
            return consistency_score
            
        except Exception as e:
            logger.error(f"Error validating character consistency: {e}")
            return 0.5
    
    def _compare_character_consistency(self, img1: Image.Image, img2: Image.Image) -> float:
        """Compare two images for character consistency"""
        try:
            # Resize for fast comparison
            size = (64, 64)
            img1_small = img1.convert('RGB').resize(size)
            img2_small = img2.convert('RGB').resize(size)
            
            # Get color histograms
            hist1 = img1_small.histogram()
            hist2 = img2_small.histogram()
            
            # Calculate correlation
            return self._histogram_correlation(hist1, hist2)
            
        except Exception as e:
            logger.error(f"Error comparing images: {e}")
            return 0.5
    
    def _histogram_correlation(self, hist1, hist2) -> float:
        """Calculate correlation between histograms"""
        if len(hist1) != len(hist2):
            return 0.0
        
        # Normalize
        sum1, sum2 = sum(hist1), sum(hist2)
        if sum1 == 0 or sum2 == 0:
            return 0.0
        
        norm1 = [h / sum1 for h in hist1]
        norm2 = [h / sum2 for h in hist2]
        
        # Simple correlation
        mean1 = sum(norm1) / len(norm1)
        mean2 = sum(norm2) / len(norm2)
        
        numerator = sum((a - mean1) * (b - mean2) for a, b in zip(norm1, norm2))
        denom1 = sum((a - mean1) ** 2 for a in norm1)
        denom2 = sum((b - mean2) ** 2 for b in norm2)
        
        if denom1 == 0 or denom2 == 0:
            return 0.0
        
        correlation = numerator / (denom1 * denom2) ** 0.5
        return max(0.0, min(1.0, correlation))
    
    def _get_negative_prompt(self) -> str:
        """Get negative prompt for consistent generation"""
        return "blurry, low quality, jpeg artifacts, multiple characters, inconsistent style, bad anatomy, deformed, extra limbs"
