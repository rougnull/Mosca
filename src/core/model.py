"""
Módulo de Modelos (Legacy Bridge)
FlyGym gestiona la carga del modelo internamente.
"""

from pathlib import Path
from typing import Optional

def find_neuromechfly_model() -> Optional[Path]:
    """Localiza el XML oficial de FlyGym."""
    try:
        import flygym
        return Path(flygym.__file__).parent / "data" / "mjcf" / "neuromechfly.xml"
    except:
        return None

# Placeholders para evitar errores de importación en render_enhanced_3d_v2.py
def modify_xml_for_high_res(xml_content, width=1920, height=1080): return xml_content
def modify_xml_floor(xml_content, floor_enabled=True, floor_config=None): return xml_content
def load_and_setup_model(model_path, width=1920, height=1080, environment_config=None): return None, None
def create_minimal_model(output_dir, environment_config=None): return None, None