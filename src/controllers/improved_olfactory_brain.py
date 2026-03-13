"""
Controlador olfatorio MEJORADO con verdadera quimiotaxis bilateral.

ARREGLO CRÍTICO (2026-03-12):
- Problema: La mosca se acercaba al olor pero luego se alejaba al estar cerca
- Causa: Forward se basaba en concentración absoluta, no en cambio temporal
- Solución: Forward ahora usa d(concentración)/dt (temporal gradient)
  * Motor forward activa solo cuando concentración AUMENTA
  * Esto previene que la mosca siga caminando cuando está en la fuente
  * La mosca ahora hace circulos en la fuente en lugar de overshooting

La mosca ahora:
1. Sensea olor en la posición actual
2. Simula sensar en posición "izquierda" y "derecha"
3. Compara gradiente bilateral para decidir hacia dónde girar
4. Avanza solo cuando concentración está AUMENTANDO (temporal gradient)
"""

import numpy as np
from typing import Optional


class ImprovedOlfactoryBrain:
    """
    Cerebro olfatorio con detección de gradiente bilateral simulado
    y control temporal de forward.
    
    Implementa verdadera quimiotaxis positiva:
    - Detecta diferencia bilateral: derecha vs izquierda → Controls turn
    - Detecta cambio temporal: dC/dt → Controls forward
    - Si conc está aumentando: caminar hacia adelante
    - Si conc está disminuyendo: parar o hacer backup
    - Si conc está estable: solo girar hacia el gradiente
    """
    
    def __init__(
        self,
        bilateral_distance: float = 1.2,  # mm: distancia entre antenas (biológico: ~1.2mm)
        forward_scale: float = 1.0,
        turn_scale: float = 0.8,
        threshold: float = 0.01,
        temporal_gradient_gain: float = 10.0,  # Ganancia para dC/dt → forward
    ):
        """
        Inicializar cerebro olfatorio bilateral con temporal gradient.

        Parameters
        ----------
        bilateral_distance : float, default=1.2
            Distancia entre puntos de sensado izquierdo/derecho (mm).
            Simula distancia entre antenas de Drosophila (~1.2mm real).
        forward_scale : float, default=1.0
            Escala de velocidad forward. Con 1.0, forward=1.0 corresponde a
            ~10 mm/s (velocidad típica de marcha de Drosophila).
        turn_scale : float, default=0.8
            Escala de giro basado en gradiente lateral bilateral.
        threshold : float, default=0.01
            Umbral mínimo de concentración normalizada para activar (0-1).
        temporal_gradient_gain : float, default=10.0
            Ganancia aplicada al cambio temporal de concentración.
            Amplifica dC/dt para generar señal forward adecuada.
        """
        self.bilateral_distance = bilateral_distance
        self.forward_scale = forward_scale
        self.turn_scale = turn_scale
        self.threshold = threshold
        self.temporal_gradient_gain = temporal_gradient_gain
        
        self._concentration_history = []
        self._max_history = 20
        self._conc_max_persistent = 0.0  # Máximo visto en el "peak" actual
        self._is_descending = False  # ¿Está bajando desde el máximo?
        self._local_peak_concentration = 0.0  # Máximo local visto recientemente (últimas 100 steps)
        self._steps_without_improvement = 0  # Cuántos steps sin mejorar concentración
        self._debug_step_count = 0  # DEBUG: Track calls
    
    def step(
        self,
        odor_field,
        current_position: np.ndarray,
        heading_radians: float,
        wall_proximity_mm: float = 999.0,
        wall_offset_angle: float = 0.0
    ) -> np.ndarray:
        """
        Ejecutar paso de decisión con gradiente temporal + bilateral + evasión de obstáculos.
        
        Parameters
        ----------
        odor_field : OdorField
            Campo de olor del entorno.
        current_position : np.ndarray
            Posición actual (x, y, z).
        heading_radians : float
            Orientación actual en radianes.
        wall_proximity_mm : float, optional
            Distancia a la pared más cercana en mm. Default 999.0 (sin pared).
            Rango sensable: 0-3mm. > 3mm = sin detección.
        wall_offset_angle : float, optional
            Ángulo relativo a la pared detectada: -1.0 (izquierda) a +1.0 (derecha).
            Default 0.0 (pared al frente).
        
        Returns
        -------
        np.ndarray
            Vector motor [forward, turn]
            - forward: basado en CAMBIO temporal de concentración (d C/dt)
            - turn: basado en DIFERENCIA bilateral del gradient + evasión de obstáculos
        """
        # DEBUG: Print inputs on first few steps
        self._debug_step_count += 1
        if self._debug_step_count <= 5:
            print(f"\n[Brain Step {self._debug_step_count}]")
            print(f"  Position: {current_position}")
            print(f"  Heading: {heading_radians:.4f} rad ({np.degrees(heading_radians):.1f}°)")

        # 1. Sensear concentración en centro
        conc_center = float(odor_field.concentration_at(current_position))
        
        # 2. Sensear en puntos laterales (bilaterales)
        #    BIOLOGÍA: Antenas de Drosophila están ADELANTE (~30-40° hacia adelante), no perpendiculares
        #    Esto permite censear el gradiente que VIENE ADELANTE (anticipación)
        #    Si la mosca va a encontrar más olor a la izquierda, la antena izquierda lo detecta
        
        # Ángulo de los sensores respecto al heading: ±35° adelante (forward-looking)
        # Esto simula antenas bilaterales que "miran hacia adelante" diagonalmente
        bilateral_angle_offset = np.radians(35)  # 35° hacia adelante
        left_angle = heading_radians + bilateral_angle_offset   # Adelante-izquierda
        right_angle = heading_radians - bilateral_angle_offset  # Adelante-derecha
        
        left_pos = current_position + self.bilateral_distance * np.array([
            np.cos(left_angle),
            np.sin(left_angle),
            0
        ])
        right_pos = current_position + self.bilateral_distance * np.array([
            np.cos(right_angle),
            np.sin(right_angle),
            0
        ])
        
        conc_left = float(odor_field.concentration_at(left_pos))
        conc_right = float(odor_field.concentration_at(right_pos))
        
        # 3. Calcular CAMBIO TEMPORAL de concentración
        # BIOLOGÍA: Drosophila detecta dC/dt mediante órganos sensoriales específicos
        # Forward solo se activa cuando concentración está AUMENTANDO
        if len(self._concentration_history) > 0:
            # Tenemos historial: usar verdadero cambio temporal
            conc_change = conc_center - self._concentration_history[-1]
        else:
            # PRIMER PASO: Sin historial, no hay gradiente temporal real
            # Biológicamente correcto: dC/dt = 0 en first step (no hay cambio aún)
            conc_change = 0.0
        
        # Guardar en historial
        self._concentration_history.append(conc_center)
        if len(self._concentration_history) > self._max_history:
            self._concentration_history.pop(0)
        
        # Actualizar máximo persistente (para detección de escape)
        # Si conc está mejorando: posible nuevo pico, actualizar máximo
        # Si conc está empeorando: estamos saliendo, usar este máximo como referencia
        if len(self._concentration_history) > 1:
            if conc_change > 0:
                # Mejorando: posiblemente acercándonos a nuevo pico
                self._conc_max_persistent = max(self._conc_max_persistent, conc_center)
                self._is_descending = False
                # Actualizar pico local
                if conc_center > self._local_peak_concentration:
                    self._local_peak_concentration = conc_center
                    self._steps_without_improvement = 0
                else:
                    self._steps_without_improvement += 1
            else:
                # Empeorando: estamos saliendo del máximo
                if not self._is_descending:
                    # Acabamos de COMENZAR a descender
                    self._conc_max_persistent = conc_center
                    self._is_descending = True
                self._steps_without_improvement += 1
        else:
            # Primer paso: inicializar
            self._conc_max_persistent = conc_center
            self._is_descending = False
            self._local_peak_concentration = conc_center
            self._steps_without_improvement = 0
        
        # 4. Calcular diferencia bilateral de gradiente (espacial)
        gradient_difference = conc_left - conc_right

        # DEBUG: Print concentration values on first few steps
        if self._debug_step_count <= 5:
            print(f"  Conc center: {conc_center:.6f}")
            print(f"  Conc left: {conc_left:.6f}")
            print(f"  Conc right: {conc_right:.6f}")
            print(f"  Gradient diff (L-R): {gradient_difference:.6f}")
            if len(self._concentration_history) > 1:
                print(f"  Conc change: {conc_change:.6f}")
            else:
                print(f"  Conc change: {conc_change:.6f} (bootstrap)")

        # 5. Generar acciones motoras:
        
        # ============================================================================
        # NUEVA ARQUITECTURA DE FORWARD (2026-03-13 Phase 5D - Transición Suave)
        # ============================================================================
        # PRINCIPIO: Forward es casi constante en approach,
        #            luego transición gaussiana suave en zona de saturación (>85)
        #
        # BIOLOGÍA: La mosca mantiene velocidad constante buscando,
        #           pero cuando concentración es muy alta, empieza a frenar suavemente
        #           (no bruscamente) para evitar oscilaciones alrededor del máximo
        # ============================================================================
        
        # COMPONENTE 1: TEMPORAL GRADIENT (¿mejorando la situación?)
        # Válido en TODO el rango - qué importa es si C está subiendo o bajando
        if conc_center > 1.0:
            normalized_gradient = conc_change / conc_center
        else:
            normalized_gradient = 0.0
        
        # Forward base basado en temporal gradient
        temporal_forwarding = 1.0
        if normalized_gradient > 0.05:
            temporal_forwarding = 1.0
        elif normalized_gradient > 0.0:
            temporal_forwarding = 0.95
        elif normalized_gradient > -0.05:
            temporal_forwarding = 0.85
        else:
            temporal_forwarding = 0.4
        
        # COMPONENTE 2: BILATERAL ALIGNMENT (¿qué tan bien alineado estoy?)
        bilateral_normalized = 0.0
        if (conc_left + conc_right) > 1.0:
            bilateral_normalized = abs(conc_left - conc_right) / (conc_left + conc_right)
        
        alignment_penalty = 1.0 - bilateral_normalized * 0.8
        alignment_penalty = max(0.2, alignment_penalty)
        
        # COMPONENTE 3: SATURACIÓN CON COLAPSO FINAL
        # En lugar de transición suave, usar ESCALÓN suave en conc > 85
        # Objetivo: mantener forward alto en approach, COLAPSAR en saturación final
        saturation_penalty = 1.0
        if conc_center > 85.0:
            # ZONA CRÍTICA: Concentración extremadamente alta (muy pegado al máximo)
            # Forward debe COLAPSAR casi a cero para prevenir escape
            # conc = 85: penalización pequeña, forward ~ 0.8 * original
            # conc = 88: penalización fuerte, forward ~ 0.1 * original  
            # conc = 90: penalización máxima, forward ~ 0.05 * original
            saturation_excess = (conc_center - 85.0) / 3.0  # Ancho de 3 unidades
            # Exponencial AGRESIVO: exp(-x^2) pero centrado en 85
            saturation_penalty = np.exp(-2.0 * (saturation_excess ** 2))
            # Cap mínimo para micro-ajustes
            saturation_penalty = max(0.05, saturation_penalty)
        
        # COMPONENTE 4: PENALIDAD ANTI-ESCAPE (¿conc está bajando desde máximo?)
        # ESTRATEGIA: Rastrea el máximo alcanzado en el "peak" actual
        # Si estamos DESCENDIENDO desde ese máximo, penalizar agresivamente
        # BIOLOGÍA: Cuando una mosca se aleja del máximo (dC/dt < 0), FRENA CASI TOTALMENTE
        anti_escape_penalty = 1.0
        
        # Primero, penalidad por CAÍDA INSTANTÁNEA (dC/dt muy negativo)
        if normalized_gradient < -0.05:
            anti_escape_penalty = 0.01  # Prácticamente inmóvil
        elif normalized_gradient < 0.0:
            anti_escape_penalty = max(0.01, 1.0 + (normalized_gradient / 0.05))
        
        # Segundo, PENALIDAD PERSISTENTE: si estamos en FASE DESCENDENTE
        # Una vez que dC/dt se volvió negativo, penalizar cualquier avance hacia atrás
        if self._is_descending and conc_center < self._conc_max_persistent:
            conc_deficit = self._conc_max_persistent - conc_center
            # Penalidad agresiva: 10% menos forward por cada punto de distancia
            # deficit=1: penalty=0.90, deficit=5: penalty=0.50, deficit=10: penalty=0.0
            # PERO con piso de 0.01 para micro-movimientos únicamente
            descent_penalty = max(0.01, 1.0 - (conc_deficit * 0.1))
            anti_escape_penalty = min(anti_escape_penalty, descent_penalty)
        
        # Tercero, penalidad si ESTAMOS ESCAPANDO (descending + lejos)
        # Solo si ya estamos en fase descendente
        if self._is_descending and conc_center < 45.0:
            anti_escape_penalty = min(anti_escape_penalty, 0.01)
        
        # FORWARD FINAL: Combinar componentes
        if conc_center > 0.5:
            forward = self.forward_scale if self.forward_scale <= 1.0 else 1.0
        else:
            forward = 0.0
        
        forward = forward * temporal_forwarding * alignment_penalty * anti_escape_penalty * saturation_penalty
        forward = max(0.0, forward)
        
        # PLATEAU DE MÁXIMO: Cuando la mosca está en el máximo (conc muy alta y no mejora)
        # LÓGICA: Si conc > 88 y ha pasado 10+ steps sin mejorar, la mosca LLEGÓ al máximo
        # No es un plateau exacto, es "no estoy mejorando" durante suficiente tiempo
        if conc_center > 88.0 and self._steps_without_improvement >= 10:
            # Estamos en el máximo: concentración ESTABLE y no mejora
            # La mosca llegó a la comida, PARA COMPLETAMENTE
            forward = 0.0
        
        # HARD CAP: Si estamos DESCENDIENDO, forward JAMÁS puede exceder 0.02
        # Esta es una restricción NO-NEGOCIABLE biológicamente: 
        # mosca alejándose del máximo = casi completamente inmóvil hacia adelante
        if self._is_descending:
            forward = min(forward, 0.02)
        
        # RESPUESTA TURN: Dinámica adaptativa basada en concentración y alineamiento
        # =========================================================================
        # Turn responde a bilateral gradient SIEMPRE,
        # pero la amplitud se reduce gradualmente cuando conc es muy alta
        
        # Normalizar el gradiente bilateral por concentración total
        conc_sum = conc_left + conc_right + 1e-8
        grad_normalized = gradient_difference / conc_sum
        
        # Aplicar tanh para suavidad NO-lineal
        turn_intensity = np.tanh(self.turn_scale * grad_normalized)
        
        # MODULACIÓN DEL TURN: Basada en concentración y desalineamiento
        # En búsqueda/approach: turn fuerte para corregir heading
        # En saturación: turn débil para micro-correcciones
        
        if conc_center < 80.0:
            # Búsqueda/approach: turn FUERTE para guiar hacia el máximo
            # El bilateral gradient apunta donde está el máximo
            # Aumentar significativamente para que forward sea "guiado" por turn
            bilateral_aligned = 0.0
            if (conc_left + conc_right) > 1.0:
                bilateral_aligned = abs(conc_left - conc_right) / (conc_left + conc_right)
            
            # FACTOR COORDINATIVO: Forward está activo, turn debe ser MUY FUERTE
            # para crear trayectoria en espiral hacia el máximo
            # Multiplicar turn x2-4 basado en desalineamiento
            bilateral_alignment_factor = 2.0 + bilateral_aligned * 3.0  # 2.0 a 5.0x
            turn_intensity = turn_intensity * bilateral_alignment_factor
        else:
            # Saturación (80-88): turn sigue siendo FUERTE para guiar aproximación final
            # pero suavemente se reduce para permitir estabilización
            # La mosca aún está aproximándose, necesita girar hacia el máximo
            saturation_excess = (conc_center - 85.0) / 5.0  # Ancho más suave (5 vs 7)
            turn_saturation_factor = np.exp(-saturation_excess ** 2)
            # No reducir tan fuerte - mantener turn fuerte durante approach final
            turn_saturation_factor = max(0.5, turn_saturation_factor)  # 50% mínimo, no 15%
            turn_intensity = turn_intensity * turn_saturation_factor
        
        # Dirección del giro (positivo = izquierda, negativo = derecha)
        turn = turn_intensity if gradient_difference > 0 else -turn_intensity
        
        # ========================================================================
        # OBSTACLE AVOIDANCE: Evasión reactiva de paredes
        # ========================================================================
        # STRATEGY: Cuando hay pared cercana, aumentar turn en dirección OPUESTA a la pared
        # BIOLOGÍA: Sistema nervioso sensorimotor activa giro de escape cuando toca un obstacle
        # 
        # wall_offset_angle: -1.0=izquierda, 0.0=frente, 1.0=derecha
        # Ejemplo: wire en la derecha (offset=1.0) → girar a la izquierda (turn < 0)
        # ========================================================================
        
        OBSTACLE_SENSING_DISTANCE = 3.0  # mm: rango de sensado de paredes
        OBSTACLE_TURN_THRESHOLD = 2.0    # mm: distancia a partir de que empieza a evadir
        OBSTACLE_TURN_GAIN = 2.0         # Amplitud de la respuesta de evasión
        
        if wall_proximity_mm < OBSTACLE_SENSING_DISTANCE:
            # Hay un muro detectado
            obstacle_turn_magnitude = OBSTACLE_TURN_GAIN
            
            # Cuanto más cerca, más agresivo el giro
            if wall_proximity_mm < OBSTACLE_TURN_THRESHOLD:
                # Muy cerca: activar evasión fuerte
                proximity_factor = 1.0 + (OBSTACLE_TURN_THRESHOLD - wall_proximity_mm) / OBSTACLE_TURN_THRESHOLD
                proximity_factor = min(2.0, proximity_factor)  # Max 2x amplificación
                obstacle_turn_magnitude *= proximity_factor
                
                # Dirección: OPUESTA a wall_offset_angle
                # wall_offset_angle = 1.0 (derecha) → girar izquierda (turn negativo)
                # wall_offset_angle = -1.0 (izquierda) → girar derecha (turn positivo)
                obstacle_turn_signal = -wall_offset_angle * obstacle_turn_magnitude
                
                # Combinar: Obstacle turn SON DOMINANTE cuando hay pared muy cercana
                # Esto asegura que el córdoba evita obstáculos aunque no haya olor
                turn = obstacle_turn_signal
            else:
                # Moderadamente cerca: blending entre odor turn y obstacle avoidance
                # No domina completamente, pero influye significativamente
                proximity_factor = (OBSTACLE_SENSING_DISTANCE - wall_proximity_mm) / (OBSTACLE_SENSING_DISTANCE - OBSTACLE_TURN_THRESHOLD)
                proximity_factor = np.clip(proximity_factor, 0.0, 1.0)
                
                obstacle_turn_signal = -wall_offset_angle * obstacle_turn_magnitude * 0.5
                
                # Blend: 70% odor-based, 30% obstacle-based cuando moderadamente cerca
                turn = (1.0 - proximity_factor * 0.3) * turn + proximity_factor * 0.3 * obstacle_turn_signal
        
        # Clamp turn to valid range [-1, 1]
        turn = np.clip(turn, -1.0, 1.0)

        # DEBUG: Print outputs on first few steps
        if self._debug_step_count <= 5:
            wall_info = ""
            if wall_proximity_mm < 999.0:
                wall_info = f" | wall_proximity={wall_proximity_mm:.1f}mm wall_offset={wall_offset_angle:.2f}"
            print(f"  Motor signal: forward={forward:.6f}, turn={turn:.6f}{wall_info}")

        return np.array([forward, turn])
    
    def get_diagnostics(self) -> dict:
        """Obtener información de diagnóstico del cerebro."""
        if not self._concentration_history:
            return {
                "mean_concentration": 0.0,
                "max_concentration": 0.0,
                "history_length": 0,
            }
        
        conc_arr = np.array(self._concentration_history)
        return {
            "mean_concentration": float(np.mean(conc_arr)),
            "max_concentration": float(np.max(conc_arr)),
            "min_concentration": float(np.min(conc_arr)),
            "history_length": len(self._concentration_history),
        }
