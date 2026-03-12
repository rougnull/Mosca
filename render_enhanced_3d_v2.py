#!/usr/bin/env python3
from src.core.config import create_moldeable_render
from src.render.mujoco_renderer import MuJoCoRenderer

def main():
    print("Iniciando Renderizado Estable - VISTA SUPERIOR (720p)")
    
    config = create_moldeable_render(fps=60)
    # Límite de seguridad: 720p
    config.width = 720
    config.height = 720 

    renderer = MuJoCoRenderer(config)
    renderer.render_and_save("neuromechfly_superior_caminar_recto2.mp4")

if __name__ == "__main__":
    main()