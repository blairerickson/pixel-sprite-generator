"""
Stable Diffusion client - supports multiple backends
"""
import base64
import io
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, asdict
from PIL import Image
import requests
import json

@dataclass
class GenerationParams:
    """Parameters for image generation"""
    prompt: str
    negative_prompt: Optional[str] = None
    preset: Optional[str] = "character_sprite"
    lora: Optional[str] = None
    lora_weight: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    steps: Optional[int] = None
    cfg_scale: Optional[float] = None
    seed: int = -1
    batch_size: int = 1
    sampler: Optional[str] = None
    base_model: Optional[str] = None

class SDClient:
    """
    Client for Stable Diffusion generation
    Supports: Automatic1111, ComfyUI, or local diffusers
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backend = config['sd']['backend']
        self.api_url = config['sd'].get('api_url', 'http://127.0.0.1:7860')
        
    async def check_health(self) -> bool:
        """Check if SD backend is available"""
        try:
            if self.backend == "automatic1111":
                response = requests.get(f"{self.api_url}/sdapi/v1/sd-models", timeout=5)
                return response.status_code == 200
            elif self.backend == "comfyui":
                response = requests.get(f"{self.api_url}/system_stats", timeout=5)
                return response.status_code == 200
            else:
                # For diffusers, always return True
                return True
        except:
            return False
    
    async def generate(self, params: GenerationParams) -> Dict[str, Any]:
        """Generate images based on parameters"""
        if self.backend == "automatic1111":
            return await self._generate_a1111(params)
        elif self.backend == "comfyui":
            return await self._generate_comfyui(params)
        elif self.backend == "diffusers":
            return await self._generate_diffusers(params)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")
    
    async def generate_with_inpaint(
        self, 
        params: GenerationParams,
        init_image: Image.Image,
        mask: Image.Image
    ) -> Dict[str, Any]:
        """Generate using inpainting - paint character into masked region"""
        if self.backend == "automatic1111":
            return await self._generate_a1111_inpaint(params, init_image, mask)
        else:
            raise NotImplementedError(f"Inpainting not implemented for {self.backend}")
    
    async def generate_with_controlnet(
        self,
        params: GenerationParams,
        control_image: Image.Image,
        controlnet_model: str = "control_openpose",
        preprocessor: str = "openpose_full",
        control_weight: float = 1.0,
        guidance_start: float = 0.0,
        guidance_end: float = 1.0
    ) -> Dict[str, Any]:
        """Generate using ControlNet guidance"""
        if self.backend == "automatic1111":
            return await self._generate_a1111_controlnet(
                params, control_image, controlnet_model, preprocessor,
                control_weight, guidance_start, guidance_end
            )
        else:
            raise NotImplementedError(f"ControlNet not implemented for {self.backend}")
    
    async def get_available_models(self) -> List[str]:
        """Get list of available models from SD backend"""
        if self.backend == "automatic1111":
            try:
                response = requests.get(f"{self.api_url}/sdapi/v1/sd-models", timeout=5)
                if response.status_code == 200:
                    models = response.json()
                    return [m.get('title', m.get('model_name', 'Unknown')) for m in models]
            except:
                pass
        return []
    
    async def get_controlnet_models(self) -> List[Dict[str, Any]]:
        """Get list of available ControlNet models"""
        if self.backend == "automatic1111":
            try:
                response = requests.get(f"{self.api_url}/controlnet/model_list", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return data.get('model_list', [])
            except:
                pass
        return []
    
    async def get_controlnet_preprocessors(self) -> List[str]:
        """Get list of available ControlNet preprocessors"""
        if self.backend == "automatic1111":
            try:
                response = requests.get(f"{self.api_url}/controlnet/preprocessor_list", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return data.get('preprocessor_list', [])
            except:
                pass
        return []
    
    async def is_controlnet_available(self) -> bool:
        """Check if ControlNet is available"""
        try:
            models = await self.get_controlnet_models()
            return len(models) > 0
        except:
            return False
    
    async def _switch_model_a1111(self, model_name: str):
        """Switch the active model in A1111"""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.api_url}/sdapi/v1/options",
                    json={"sd_model_checkpoint": model_name},
                    timeout=10
                )
            )
            if response.status_code != 200:
                print(f"Warning: Failed to switch model to {model_name}: {response.text}")
        except Exception as e:
            print(f"Warning: Error switching model to {model_name}: {e}")
    
    async def _generate_a1111(self, params: GenerationParams) -> Dict[str, Any]:
        """Generate using Automatic1111 API"""
        
        # Switch model if specified
        if params.base_model:
            await self._switch_model_a1111(params.base_model)
        
        # Get preset settings
        preset_config = None
        if params.preset and params.preset in self.config['generation']['presets']:
            preset_config = self.config['generation']['presets'][params.preset]
        
        # Build prompt with LoRA
        prompt = params.prompt
        if params.lora:
            lora_config = self._get_lora_config(params.lora)
            if lora_config:
                # Add LoRA trigger words
                triggers = " ".join(lora_config.get('triggers', []))
                prompt = f"{triggers}, {prompt}"
                
                # Add LoRA to prompt
                weight = params.lora_weight or lora_config['default_weight']
                prompt += f" <lora:{params.lora}:{weight}>"
        
        # Add default suffix
        suffix = self.config['generation']['default_prompt_suffix']
        prompt = f"{prompt}, {suffix}"
        
        # Build negative prompt
        negative_prompt = params.negative_prompt or self.config['generation']['default_negative']
        
        # Apply preset template if available
        if preset_config and 'prompt_template' in preset_config:
            template = preset_config['prompt_template']
            prompt = template.format(description=prompt)
        
        # Build request payload
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": params.steps or (preset_config['steps'] if preset_config else 30),
            "cfg_scale": params.cfg_scale or (preset_config['cfg_scale'] if preset_config else 7.5),
            "width": params.width or (preset_config['width'] if preset_config else 512),
            "height": params.height or (preset_config['height'] if preset_config else 512),
            "sampler_name": params.sampler or (preset_config.get('sampler') if preset_config else "DPM++ 2M Karras"),
            "batch_size": params.batch_size,
            "seed": params.seed,
            "save_images": False,
            "send_images": True,
        }
        
        # Make request
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                f"{self.api_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=300
            )
        )
        
        if response.status_code != 200:
            raise Exception(f"A1111 API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        # Decode images
        images = []
        for img_data in result['images']:
            img_bytes = base64.b64decode(img_data)
            images.append(Image.open(io.BytesIO(img_bytes)))
        
        # Get info
        info = json.loads(result.get('info', '{}'))
        
        return {
            'images': images,
            'seed': info.get('seed', params.seed),
            'parameters': {
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'steps': payload['steps'],
                'cfg_scale': payload['cfg_scale'],
                'width': payload['width'],
                'height': payload['height'],
                'sampler': payload['sampler_name']
            }
        }
    
    async def _generate_a1111_inpaint(
        self, 
        params: GenerationParams,
        init_image: Image.Image,
        mask: Image.Image
    ) -> Dict[str, Any]:
        """Generate using Automatic1111 inpainting API"""
        
        # Get preset settings
        preset_config = None
        if params.preset and params.preset in self.config['generation']['presets']:
            preset_config = self.config['generation']['presets'][params.preset]
        
        # Build prompt with LoRA
        prompt = params.prompt
        if params.lora:
            lora_config = self._get_lora_config(params.lora)
            if lora_config:
                triggers = " ".join(lora_config.get('triggers', []))
                prompt = f"{triggers}, {prompt}"
                weight = params.lora_weight or lora_config['default_weight']
                prompt += f" <lora:{params.lora}:{weight}>"
        
        # Add default suffix
        suffix = self.config['generation']['default_prompt_suffix']
        prompt = f"{prompt}, {suffix}"
        
        # Build negative prompt
        negative_prompt = params.negative_prompt or self.config['generation']['default_negative']
        
        # Apply preset template if available (but strip background mentions for inpainting)
        if preset_config and 'prompt_template' in preset_config:
            template = preset_config['prompt_template']
            prompt = template.format(description=prompt)
            # Remove background references since we're inpainting
            prompt = prompt.replace("solid color background", "").replace("background", "").strip()
        
        # Convert images to base64
        def image_to_base64(img: Image.Image) -> str:
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        init_b64 = image_to_base64(init_image)
        mask_b64 = image_to_base64(mask)
        
        # Build request payload for img2img inpainting
        payload = {
            "init_images": [init_b64],
            "mask": mask_b64,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": params.steps or (preset_config['steps'] if preset_config else 30),
            "cfg_scale": params.cfg_scale or (preset_config['cfg_scale'] if preset_config else 7.5),
            "width": params.width or (preset_config['width'] if preset_config else 512),
            "height": params.height or (preset_config['height'] if preset_config else 512),
            "sampler_name": params.sampler or (preset_config.get('sampler') if preset_config else "DPM++ 2M Karras"),
            "batch_size": params.batch_size,
            "seed": params.seed,
            "denoising_strength": 1.0,  # Full strength for inpainting
            "inpaint_full_res": False,  # Process whole image
            "inpainting_fill": 1,  # Fill with original (magenta)
            "inpainting_mask_invert": 0,  # White = inpaint, black = preserve
            "save_images": False,
            "send_images": True,
        }
        
        # Make request to img2img endpoint
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                f"{self.api_url}/sdapi/v1/img2img",
                json=payload,
                timeout=300
            )
        )
        
        if response.status_code != 200:
            raise Exception(f"A1111 inpaint error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        # Decode images
        images = []
        for img_data in result['images']:
            img_bytes = base64.b64decode(img_data)
            images.append(Image.open(io.BytesIO(img_bytes)))
        
        # Get info
        info = json.loads(result.get('info', '{}'))
        
        return {
            'images': images,
            'seed': info.get('seed', params.seed),
            'parameters': {
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'steps': payload['steps'],
                'cfg_scale': payload['cfg_scale'],
                'width': payload['width'],
                'height': payload['height'],
                'sampler': payload['sampler_name'],
                'method': 'inpaint'
            }
        }
    
    async def _generate_a1111_controlnet(
        self,
        params: GenerationParams,
        control_image: Image.Image,
        controlnet_model: str,
        preprocessor: str,
        control_weight: float,
        guidance_start: float,
        guidance_end: float
    ) -> Dict[str, Any]:
        """Generate using Automatic1111 ControlNet API"""
        
        # Get preset settings
        preset_config = None
        if params.preset and params.preset in self.config['generation']['presets']:
            preset_config = self.config['generation']['presets'][params.preset]
        
        # Build prompt with LoRA
        prompt = params.prompt
        if params.lora:
            lora_config = self._get_lora_config(params.lora)
            if lora_config:
                triggers = " ".join(lora_config.get('triggers', []))
                prompt = f"{triggers}, {prompt}"
                weight = params.lora_weight or lora_config['default_weight']
                prompt += f" <lora:{params.lora}:{weight}>"
        
        # Add default suffix
        suffix = self.config['generation']['default_prompt_suffix']
        prompt = f"{prompt}, {suffix}"
        
        # Build negative prompt
        negative_prompt = params.negative_prompt or self.config['generation']['default_negative']
        
        # Convert control image to base64
        def image_to_base64(img: Image.Image) -> str:
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        control_b64 = image_to_base64(control_image)
        
        # Build ControlNet request payload
        controlnet_args = [{
            "input_image": control_b64,
            "model": controlnet_model,
            "preprocessor": preprocessor,
            "weight": control_weight,
            "guidance_start": guidance_start,
            "guidance_end": guidance_end,
            "control_mode": 0,  # Balanced
            "pixel_perfect": True
        }]
        
        # Build main request payload
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": params.steps or (preset_config['steps'] if preset_config else 30),
            "cfg_scale": params.cfg_scale or (preset_config['cfg_scale'] if preset_config else 7.5),
            "width": params.width or (preset_config['width'] if preset_config else 512),
            "height": params.height or (preset_config['height'] if preset_config else 512),
            "sampler_name": params.sampler or (preset_config.get('sampler') if preset_config else "DPM++ 2M Karras"),
            "batch_size": params.batch_size,
            "seed": params.seed,
            "alwayson_scripts": {
                "controlnet": {
                    "args": controlnet_args
                }
            },
            "save_images": False,
            "send_images": True,
        }
        
        # Make request
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                f"{self.api_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=300
            )
        )
        
        if response.status_code != 200:
            raise Exception(f"A1111 ControlNet error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        # Decode images
        images = []
        for img_data in result['images']:
            img_bytes = base64.b64decode(img_data)
            images.append(Image.open(io.BytesIO(img_bytes)))
        
        # Get info
        info = json.loads(result.get('info', '{}'))
        
        return {
            'images': images,
            'seed': info.get('seed', params.seed),
            'parameters': {
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'steps': payload['steps'],
                'cfg_scale': payload['cfg_scale'],
                'width': payload['width'],
                'height': payload['height'],
                'sampler': payload['sampler_name'],
                'method': 'controlnet',
                'controlnet_model': controlnet_model,
                'preprocessor': preprocessor,
                'control_weight': control_weight
            }
        }
    
    async def _generate_comfyui(self, params: GenerationParams) -> Dict[str, Any]:
        """Generate using ComfyUI API"""
        # TODO: Implement ComfyUI workflow execution
        # ComfyUI uses a workflow JSON format and websocket communication
        raise NotImplementedError("ComfyUI backend not yet implemented. Use Automatic1111 for now.")
    
    async def _generate_diffusers(self, params: GenerationParams) -> Dict[str, Any]:
        """Generate using local diffusers pipeline"""
        # TODO: Implement direct diffusers generation
        # This would use diffusers library directly without a separate server
        raise NotImplementedError("Diffusers backend not yet implemented. Use Automatic1111 for now.")
    
    def _get_lora_config(self, lora_name: str) -> Optional[Dict[str, Any]]:
        """Get LoRA configuration by name"""
        for lora in self.config['sd']['loras']:
            if lora['name'] == lora_name:
                return lora
        return None

class MockSDClient(SDClient):
    """Mock client for testing without SD backend"""
    
    async def check_health(self) -> bool:
        return True
    
    async def generate(self, params: GenerationParams) -> Dict[str, Any]:
        """Generate mock images"""
        from PIL import Image, ImageDraw, ImageFont
        
        # Get dimensions
        preset_config = self.config['generation']['presets'].get(params.preset, {})
        width = params.width or preset_config.get('width', 512)
        height = params.height or preset_config.get('height', 512)
        
        images = []
        for i in range(params.batch_size):
            # Create a simple test image
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Draw a simple sprite placeholder
            draw.rectangle([width//4, height//4, 3*width//4, 3*height//4], 
                          fill='lightblue', outline='black', width=2)
            draw.text((width//2, height//2), "Mock Sprite", 
                     fill='black', anchor='mm')
            
            images.append(img)
        
        return {
            'images': images,
            'seed': params.seed if params.seed != -1 else 42,
            'parameters': {
                'prompt': params.prompt,
                'width': width,
                'height': height
            }
        }

