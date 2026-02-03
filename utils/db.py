from pathlib import Path
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Table,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

from utils.ai import PesquisaPrompt

# SQLAlchemy Base
Base = declarative_base()


class Query(Base):
    """Represents a search query with its metadata."""

    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(String, nullable=False)
    query_text = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Many-to-many relationship with Candidate through QueryCandidate
    candidates = relationship(
        "Candidate",
        secondary="query_candidates",
        back_populates="queries",
    )

    # Direct relationship with QueryCandidate for accessing metadata
    query_candidates = relationship(
        "QueryCandidate",
        back_populates="query",
        cascade="all, delete-orphan",
        overlaps="candidates",
    )


class Candidate(Base):
    """Represents a candidate item that can be reused across queries."""

    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_text = Column(String, nullable=False, unique=True, index=True)

    # Many-to-many relationship with Query through QueryCandidate
    queries = relationship(
        "Query",
        secondary="query_candidates",
        back_populates="candidates",
    )

    # Direct relationship with QueryCandidate for accessing metadata
    query_candidates = relationship(
        "QueryCandidate",
        back_populates="candidate",
        overlaps="queries",
    )


class QueryCandidate(Base):
    """Association table with query-specific metadata for each candidate."""

    __tablename__ = "query_candidates"

    query_id = Column(Integer, ForeignKey("queries.id", ondelete="CASCADE"), primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    distance = Column(Float, nullable=False)
    score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)

    # Relationships to access parent objects
    query = relationship("Query", back_populates="query_candidates")
    candidate = relationship("Candidate", back_populates="query_candidates")

    # Index for efficient query lookups
    __table_args__ = (
        Index("idx_query_candidates_query_id", "query_id"),
    )


class QueryResultsDB:
    """SQLAlchemy ORM helper for storing prompts and candidate items with many-to-many relationship."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.session: Optional[Session] = None
        self._init_schema()

    def _init_schema(self) -> None:
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)

    def _get_or_create_candidate(self, candidate_text: str) -> Candidate:
        """Get existing candidate or create new one."""
        candidate = (
            self.session.query(Candidate)
            .filter(Candidate.candidate_text == candidate_text)
            .one_or_none()
        )

        if candidate is None:
            candidate = Candidate(candidate_text=candidate_text)
            self.session.add(candidate)
            self.session.flush()

        return candidate

    def store_prompts(self, prompts: list[PesquisaPrompt]) -> None:
        """Persist prompts and their candidate items with deduplication.

        Candidates are deduplicated by text - if a candidate with the same text
        already exists, it will be reused. Query-specific metadata (distance, score, rank)
        is stored in the association table.
        """
        if self.session is None:
            raise ValueError("Database session is not initialized.")

        for prompt in prompts:
            # Create new query
            query = Query(
                prompt_id=str(prompt.id),
                query_text=prompt.item_description,
            )
            self.session.add(query)
            self.session.flush()  # Get query.id

            # Process candidates with deduplication
            for rank, item in enumerate(prompt.items, start=1):
                candidate = self._get_or_create_candidate(item.description)

                # Create association with query-specific metadata
                query_candidate = QueryCandidate(
                    query_id=query.id,
                    candidate_id=candidate.id,
                    distance=item.distance,
                    score=item.score,
                    rank=rank,
                )
                self.session.add(query_candidate)

        self.session.commit()

    def close(self) -> None:
        """Close the database session."""
        if self.session:
            self.session.close()
            self.session = None

    def __enter__(self):
        """Context manager entry - create a new session."""
        self.session = self.SessionLocal()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager exit - close the session."""
        self.close()
