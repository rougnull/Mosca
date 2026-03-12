#!/usr/bin/env python3
"""
Rendering Pipeline Orchestrator - Orquesta el pipeline completo de renderizado.

Pipeline modular:
1. DATA_LOADER: Carga .pkl → extrae joint angles
2. ENVIRONMENT_SETUP: Inicializa FlyGym
3. FRAME_RENDERER: Ejecuta simulation steps y captura frames
4. VIDEO_WRITER: Guarda frames como MP4

Separación de concernencias: Cada módulo es independiente y puede ser usado
por separado. El orquestador solo coordina el flujo.

Uso:
    from src.rendering import RenderingPipeline
    
    pipeline = RenderingPipeline()
    success = pipeline.render(
        data_file_path,
        output_video_path,
        fps=60
    )
"""

from pathlib import Path
from typing import Optional, Dict, Any
import json

from ..data.data_loader import DataLoader
from ..data.environment_setup import EnvironmentSetup
from ..core.frame_renderer import FrameRenderer
from ..core.video_writer import VideoWriter


class RenderingPipeline:
    """Orquestador del pipeline de renderizado 3D."""
    
    def __init__(self, verbose: bool = True):
        """
        Inicializar pipeline.
        
        Args:
            verbose: Imprimir progreso detallado
        """
        self.verbose = verbose
        
        # Componentes
        self.data_loader = DataLoader(verbose)
        self.env_setup = EnvironmentSetup(verbose)
        self.frame_renderer = None
        self.video_writer = VideoWriter(verbose)
        
        # Estado
        self.pipeline_report = {}
        self.success = False
        
    def _log(self, msg: str):
        """Log con control de verbosity."""
        if self.verbose:
            print(msg)
    
    def render(
        self,
        data_file: Path,
        output_video: Optional[Path] = None,
        fps: int = 60,
        arena_type: str = "flat",
        camera_type: str = "yaw_only",
        verbose: bool = None,
    ) -> bool:
        """
        Ejecutar pipeline completo de renderizado.
        
        Args:
            data_file: Ruta al archivo .pkl con datos de simulación
            output_video: Ruta destino del video MP4
            fps: Frames per second
            arena_type: Tipo de arena FlyGym
            camera_type: Tipo de cámara
            verbose: Override verbosity
        
        Returns:
            True si renderizado exitoso
        """
        if verbose is not None:
            self.verbose = verbose
            self.data_loader.verbose = verbose
            self.env_setup.verbose = verbose
            self.video_writer.verbose = verbose
        
        self._log("\n" + "="*70)
        self._log("PIPELINE DE RENDERIZADO 3D")
        self._log("="*70)
        
        # Fijar nombre de salida por defecto
        if output_video is None:
            output_video = Path(data_file).parent / "fly_3d_animation.mp4"
        output_video = Path(output_video)
        
        # PASO 1: Cargar datos
        self._log("\n[1/4] CARGANDO DATOS")
        self._log("-" * 70)
        
        if not self.data_loader.load_from_file(data_file):
            self._log("✗ Fallo cargando datos")
            self.success = False
            return False
        
        if not self.data_loader.extract_joint_angles():
            self._log("✗ Fallo extrayendo angles")
            self.success = False
            return False
        
        # Validar integridad
        valid, msg = self.data_loader.validate_data_integrity()
        self._log(msg)
        if not valid:
            self._log("✗ Datos inválidos")
            self.success = False
            return False
        
        # PASO 2: Configurar ambiente FlyGym
        self._log("\n[2/4] CONFIGURANDO AMBIENTE")
        self._log("-" * 70)
        
        if not self.env_setup.setup_complete(
            arena_type=arena_type,
            camera_type=camera_type,
        ):
            self._log("✗ Fallo configurando ambiente")
            self.success = False
            return False
        
        # PASO 3: Renderizar frames
        self._log("\n[3/4] RENDERIZANDO FRAMES")
        self._log("-" * 70)
        
        joint_angles = self.data_loader.get_joint_angles()
        self.frame_renderer = FrameRenderer(
            self.env_setup.get_simulation(),
            joint_angles,
            verbose=self.verbose
        )
        
        if not self.frame_renderer.render_frames(fps=fps):
            self._log("✗ Fallo renderizando frames")
            self.success = False
            return False
        
        frames = self.frame_renderer.get_frames()
        if not frames:
            self._log("✗ No hay frames para guardar")
            self.success = False
            return False
        
        # PASO 4: Guardar video
        self._log("\n[4/4] GUARDANDO VIDEO MP4")
        self._log("-" * 70)
        
        if not self.video_writer.save_video(
            frames,
            output_video,
            fps=fps,
        ):
            self._log("✗ Fallo guardando video")
            self.success = False
            return False
        
        # EXITO
        self._log("\n" + "="*70)
        self._log("✓ RENDERIZADO COMPLETADO EXITOSAMENTE")
        self._log("="*70)
        self.success = True
        
        # Generar reporte
        self._generate_report(data_file, output_video, fps)
        
        return True
    
    def _generate_report(self, data_file: Path, output_video: Path, fps: int):
        """Generar reporte del pipeline."""
        self.pipeline_report = {
            'status': 'success' if self.success else 'failed',
            'components': {
                'data_loader': str(self.data_loader),
                'environment': str(self.env_setup),
                'frame_renderer': str(self.frame_renderer),
                'video_writer': str(self.video_writer),
            },
            'data': {
                'input_file': str(data_file),
                'output_file': str(output_video),
                'fps': fps,
            },
            'results': {
                'total_frames': self.frame_renderer.get_frame_count() if self.frame_renderer else 0,
                'error_frames': self.frame_renderer.get_error_count() if self.frame_renderer else 0,
                'video_info': self.video_writer.get_last_output_info(),
            }
        }
    
    def get_report(self) -> Dict[str, Any]:
        """Obtener reporte del último rendering."""
        return self.pipeline_report
    
    def save_report(self, report_file: Path):
        """Guardar reporte en archivo JSON."""
        report_file = Path(report_file)
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(self.pipeline_report, f, indent=2)
        
        self._log(f"Reporte guardado: {report_file}")
    
    def __repr__(self) -> str:
        """Representación string."""
        return f"RenderingPipeline(success={self.success})"
