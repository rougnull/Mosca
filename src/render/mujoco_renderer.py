"""
Renderizador FlyGym - VISTA ESTABILIZADA (YawOnly)
Solución: Parámetro targeted_fly_names + Zoom de proximidad.
"""

import numpy as np
from pathlib import Path
from tqdm import tqdm
import imageio
from typing import Optional, Dict, Any

from flygym import Fly, YawOnlyCamera, SingleFlySimulation
from flygym.arena import FlatTerrain

from src.core.config import RenderConfig
from src.core.data import load_kinematic_data, format_joint_data, get_n_frames

class MuJoCoRenderer:
    def __init__(self, config: RenderConfig):
        self.config = config
        self.sim = None
        self.fly = None
        self.cam = None
        self.formatted_data = None
        self.frames = []
        
    def load_data(self) -> bool:
        print("\n[1/4] Cargando datos cinemáticos...")
        try:
            raw_data = load_kinematic_data(self.config.data_file)
            self.formatted_data = format_joint_data(raw_data, self.config.subsample)
            return True
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False

    def _setup_environment(self):
        print(f"\n[2/4] Configurando Cámara Estabilizada (Tracking)...")
        
        # 1. Creamos la mosca con un nombre explícito: "fly"
        self.fly = Fly(
            name="fly", 
            init_pose="stretch", 
            control="position", 
            enable_adhesion=True
        )
        arena = FlatTerrain()
        
        # 2. Parámetros de vista: Muy cerca (8mm) y con zoom óptico (fovy 35)
        camera_config = {
            "pos": [0, 0, 8.0],   # Cerca para no ver el 'skybox' blanco
            "euler": [0, 0, 0],   # Vista desde arriba
            "fovy": 35            # Zoom
        }

        # --- CORRECCIÓN CRÍTICA ---
        # targeted_fly_names=["fly"] le dice a la cámara qué mosca rastrear.
        self.cam = YawOnlyCamera(
            attachment_point=self.fly.model.worldbody,
            camera_name="stabilized_top",
            targeted_fly_names=["fly"], # <--- Esto soluciona el ValueError
            window_size=(720, 720),
            camera_parameters=camera_config
        )
        
        self.sim = SingleFlySimulation(
            fly=self.fly,
            arena=arena,
            cameras=[self.cam],
            timestep=self.config.physics_timestep
        )
        print(f"  ✓ Cámara YawOnly configurada siguiendo a la mosca 'fly'.")

    def _get_action_for_frame(self, frame_idx: int) -> Dict[str, Any]:
        joint_angles = []
        
        for joint_name in self.fly.actuated_joints:
            # 1. Buscamos siempre el dato del lado IZQUIERDO (L) como fuente
            is_right = joint_name.startswith('R')
            source_name = 'L' + joint_name[1:] if is_right else joint_name
            
            angle = 0.0
            for key in self.formatted_data.keys():
                if source_name.lower() in key.lower() or key.lower() in source_name.lower():
                    angle = self.formatted_data[key][frame_idx]
                    break
            
            # 2. Conversión a Radianes
            if abs(angle) > 6.28:
                angle = np.deg2rad(angle)
            
            # 3. SIMETRÍA INTELIGENTE
            # Solo invertimos el signo en articulaciones que mueven la pata hacia los lados (Roll/Yaw)
            # Las de flexión (Coxa, Femur, Tibia sin 'roll') NO se invierten.
            if is_right:
                # Invertir solo si es un movimiento lateral/rotacional
                if 'roll' in joint_name.lower() or 'yaw' in joint_name.lower():
                    angle = -angle
                # Si es flexión principal, lo dejamos igual que la izquierda
                else:
                    angle = angle 

            joint_angles.append(angle)
            
        return {"joints": np.array(joint_angles), "adhesion": np.ones(6)}
    
    def render(self) -> bool:
        if self.sim is None: self._setup_environment()
        
        print("\n[3/4] Generando video estabilizado...")
        n_frames = get_n_frames(self.formatted_data)
        self.sim.reset()
        self.frames = []
        
        # Warm-up corto
        initial_action = self._get_action_for_frame(0)
        for _ in range(100): self.sim.step(initial_action)
            
        steps_per_frame = int((1.0 / self.config.fps) / self.sim.timestep)
        
        try:
            with tqdm(total=n_frames, desc="  Renderizando") as pbar:
                for f_idx in range(n_frames):
                    action = self._get_action_for_frame(f_idx)
                    for _ in range(steps_per_frame):
                        self.sim.step(action)
                    
                    # Capturamos el frame estabilizado
                    rendered_imgs = self.sim.render()
                    self.frames.append(rendered_imgs[0])
                    pbar.update(1)
            return True
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False
        finally:
            self.sim.close()

    def save_video(self, output_filename: str) -> bool:
        print("\n[4/4] Guardando video...")
        if not self.frames: return False
        output_path = self.config.output_dir / output_filename
        imageio.mimsave(output_path, self.frames, fps=self.config.fps)
        print(f"  ✓ Video guardado: {output_path}")
        return True

    def render_and_save(self, output_filename: str) -> bool:
        if not self.load_data(): return False
        if not self.render(): return False
        return self.save_video(output_filename)