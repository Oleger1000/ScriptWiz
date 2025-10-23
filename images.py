import os
import random
import tempfile
from PIL import Image

def prepare_image(path):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    m = min(w, h)
    img = img.crop(((w - m)//2, (h - m)//2, (w + m)//2, (h + m)//2))
    tmp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    img.save(tmp_file.name, "JPEG", quality=95)
    return tmp_file.name

def get_random_avatar(avatars_dir):
    avatars = [os.path.join(avatars_dir, f) for f in os.listdir(avatars_dir)
               if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not avatars:
        return None
    return random.choice(avatars)
