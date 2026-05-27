"""Generate one cinematic 'AI image' using Gemini Nano Banana via emergentintegrations.
The image will be composited into the AI IMAGES section of the promo video."""
import asyncio
import base64
import os
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from emergentintegrations.llm.gemeni.image_generation import GeminiImageGeneration

OUT = "/app/app_preview/promo_frames/_ai_generated.png"

async def main():
    key = os.environ.get("EMERGENT_LLM_KEY", "sk-emergent-87e368c67C65613825")
    gen = GeminiImageGeneration(api_key=key)
    images = await gen.generate_images(
        prompt=(
            "Stunning cinematic 4K image: a futuristic cyberpunk woman with glowing neon green "
            "and electric blue lights reflecting on her face, futuristic city background at night, "
            "rain droplets, hyper-realistic skin texture, dramatic lighting, ultra-detailed, "
            "vertical 9:16 aspect ratio, professional advertisement quality"
        ),
        number_of_images=1,
    )
    if images:
        # images is a list of bytes
        data = images[0]
        with open(OUT, "wb") as f:
            f.write(data)
        print(f"✅ Saved {OUT} ({len(data)} bytes)")
    else:
        print("❌ No images returned")

asyncio.run(main())
