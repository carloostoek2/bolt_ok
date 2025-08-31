from sqlalchemy import Column, Integer, String, Text, ForeignKey, BigInteger, JSON, Boolean, DateTime, Index, func
from sqlalchemy.orm import relationship
from uuid import uuid4
from .base import Base


class NarrativeFragment(Base):
    """Modelo unificado para fragmentos narrativos con soporte para historia, decisiones e información.
    
    Este modelo representa fragmentos narrativos que pueden ser de diferentes tipos:
    - STORY: Fragmentos de historia principal
    - DECISION: Puntos de decisión con opciones
    - INFO: Fragmentos informativos
    
    Cada fragmento puede tener requerimientos (pistas necesarias) y triggers (recompensas/pistas).
    """
    
    __tablename__ = 'narrative_fragments_unified'
    __table_args__ = (
        Index('ix_narrative_fragments_unified_type_active', 'fragment_type', 'is_active'),
        Index('ix_narrative_fragments_unified_active', 'is_active'),
    )

    # UUID primary key for global uniqueness
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    
    # Fragment type classification
    FRAGMENT_TYPES = (
        ('STORY', 'Fragmento de historia'),
        ('DECISION', 'Punto de decisión'),
        ('INFO', 'Fragmento informativo'),
    )
    fragment_type = Column(String(20), nullable=False)
    
    # Choices for decision points (JSON field)
    choices = Column(JSON, default=list, nullable=False)
    
    # Triggers for rewards and other effects (JSON field)
    triggers = Column(JSON, default=dict, nullable=False)
    
    # Required clues/pistas for unlocking this fragment
    required_clues = Column(JSON, default=list, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Active status
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<NarrativeFragment(id={self.id}, title='{self.title}', type='{self.fragment_type}')>"

    @property
    def is_story(self):
        """Check if fragment is a story fragment."""
        return self.fragment_type == 'STORY'

    @property
    def is_decision(self):
        """Check if fragment is a decision point."""
        return self.fragment_type == 'DECISION'

    @property
    def is_info(self):
        """Check if fragment is an info fragment."""
        return self.fragment_type == 'INFO'


class UserNarrativeState(Base):
    """Estado narrativo unificado del usuario.
    
    Este modelo rastrea el progreso del usuario en el sistema narrativo unificado,
    incluyendo fragmentos visitados, completados, y pistas desbloqueadas.
    """
    
    __tablename__ = 'user_narrative_states_unified'
    
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    current_fragment_id = Column(String, ForeignKey('narrative_fragments_unified.id'), nullable=True)
    visited_fragments = Column(JSON, default=list, nullable=False)  # Lista de IDs de fragmentos visitados
    completed_fragments = Column(JSON, default=list, nullable=False)  # Lista de IDs de fragmentos completados
    unlocked_clues = Column(JSON, default=list, nullable=False)  # Lista de códigos de pistas desbloqueadas
    
    # Relaciones
    user = relationship("User", backref="narrative_state_unified", uselist=False)
    current_fragment = relationship("NarrativeFragment", foreign_keys=[current_fragment_id])
    
    async def get_progress_percentage(self, session):
        """Calcula el porcentaje de progreso del usuario.
        
        Args:
            session: Sesión de base de datos SQLAlchemy
            
        Returns:
            float: Porcentaje de progreso (0-100)
        """
        from sqlalchemy import func, select
        # Contar fragmentos activos
        total_fragments_result = await session.execute(
            select(func.count(NarrativeFragment.id)).where(NarrativeFragment.is_active == True)
        )
        total_fragments = total_fragments_result.scalar()
        
        if total_fragments == 0:
            return 0
        
        completed_count = len(self.completed_fragments)
        return (completed_count / total_fragments) * 100
    
    def has_unlocked_clue(self, clue_code):
        """Verifica si el usuario ha desbloqueado una pista específica.
        
        Args:
            clue_code (str): Código de la pista a verificar
            
        Returns:
            bool: True si la pista está desbloqueada, False en caso contrario
        """
        return clue_code in self.unlocked_clues

    def has_visited_fragment(self, fragment_id):
        """Verifica si el usuario ha visitado un fragmento específico.
        
        Args:
            fragment_id (str): ID del fragmento a verificar
            
        Returns:
            bool: True si el fragmento ha sido visitado, False en caso contrario
        """
        return fragment_id in self.visited_fragments

    def has_completed_fragment(self, fragment_id):
        """Verifica si el usuario ha completado un fragmento específico.
        
        Args:
            fragment_id (str): ID del fragmento a verificar
            
        Returns:
            bool: True si el fragmento ha sido completado, False en caso contrario
        """
        return fragment_id in self.completed_fragments


class UserDecisionLog(Base):
    """Log de decisiones del usuario en el sistema narrativo unificado.
    
    Este modelo registra todas las decisiones tomadas por los usuarios para
    análisis, seguimiento de progreso y prevención de recompensas duplicadas.
    """
    
    __tablename__ = 'user_decision_log_unified'
    __table_args__ = (
        Index('ix_user_decision_log_unified_user', 'user_id'),
        Index('ix_user_decision_log_unified_time', 'made_at'),
        Index('ix_user_decision_log_unified_fragment', 'fragment_id'),
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    fragment_id = Column(String, ForeignKey('narrative_fragments_unified.id', ondelete='CASCADE'), nullable=False)
    decision_choice = Column(String(100), nullable=False)  # Texto de la opción elegida
    points_awarded = Column(Integer, default=0, nullable=False)
    clues_unlocked = Column(JSON, default=list, nullable=False)  # Lista de códigos de pistas desbloqueadas
    made_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relaciones
    user = relationship("User", lazy="selectin")
    fragment = relationship("NarrativeFragment", lazy="selectin")

    def __repr__(self):
        return f"<UserDecisionLog(id={self.id}, user_id={self.user_id}, fragment_id='{self.fragment_id}', choice='{self.decision_choice}')>"