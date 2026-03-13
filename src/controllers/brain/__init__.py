"""Modular Drosophila brain architecture."""

from .sensors.olfactory_sensor import OlfactorySensor
from .sensors.visual_sensor import VisualSensor
from .sensors.mechanoreceptor_sensor import MechanoreceptorSensor

__all__ = [
    "OlfactorySensor",
    "VisualSensor",
    "MechanoreceptorSensor",
]
