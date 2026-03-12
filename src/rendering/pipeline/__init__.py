"""
Módulo Pipeline - Orquestación

Contiene la canalización principal que integra todos los componentes
de rendering (carga, renderizado, codificación) en un flujo unificado.

Clases:
    - RenderingPipeline: Orquestador principal del flujo completo
"""

from .rendering_pipeline import RenderingPipeline

__all__ = ["RenderingPipeline"]
