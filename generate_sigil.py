import torch
from diffusers import DiffusionPipeline
import time

def generate_sigil(prompt, output_filename="chaos_magick_sigil.png"):
    print("Loading Diffusion Pipeline...")
    
    # Note: Even on AMD ROCm, PyTorch uses 'cuda' for the device string
    pipe = DiffusionPipeline.from_pretrained(
        "prism-ml/bonsai-image-ternary-4B-gemlite-2bit", 
        dtype=torch.bfloat16, 
        device_map="cuda" 
    )

    print(f"Generating Chaos Magick sigil with prompt:\n'{prompt}'")
    
    start_time = time.time()
    
    # Model card best practices: 4 steps, guidance = 1.0, native 1024x1024
    image = pipe(
        prompt=prompt,
        num_inference_steps=4,
        guidance_scale=1.0,
        height=1024,
        width=1024,
    ).images[0]
    
    end_time = time.time()
    
    print(f"Generation took {end_time - start_time:.2f} seconds.")
    
    image.save(output_filename)
    print(f"Saved generated sigil to {output_filename}")

if __name__ == "__main__":
    sigil_prompt = (
        "A highly intricate chaos magick sigil, glowing with ethereal arcane energy, "
        "integrated into a dark brass radionics machine circuit board, "
        "muted dark colors with vibrant glowing accents, occult aesthetics, highly detailed, 8k resolution"
    )
    generate_sigil(sigil_prompt)
