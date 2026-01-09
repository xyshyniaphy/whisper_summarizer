"""Base class line 12 coverage test.

This test specifically targets app/db/base_class.py line 12:
    return cls.__name__.lower() + "s"

This line is called by SQLAlchemy's @declared_attr decorator when a new
model class is created. To execute this line, we need to dynamically create
a new class that inherits from Base during test execution.
"""

import pytest
from sqlalchemy import Column, String, Integer
from app.db.base_class import Base


class TestBaseClassLine12Coverage:
    """Test Base class @declared_attr method (line 12)."""

    def test_declared_attr_generates_tablename_hits_line_12(self) -> None:
        """
        Test that creating a new model class executes line 12.

        This targets base_class.py line 12:
        ```python
        return cls.__name__.lower() + "s"
        ```

        The @declared_attr decorator is called when a class inherits from Base.
        By creating a new class dynamically, we ensure line 12 is executed.

        Strategy: Create a test model class and verify tablename is generated.
        """
        # Create a new model class dynamically
        # This triggers the @declared_attr decorator on line 12
        class TestModel(Base):
            """Test model to trigger line 12 execution."""
            __name__ = "TestModel"
            # Don't set __tablename__ - let @declared_attr generate it via line 12
            id = Column(Integer, primary_key=True)

        # Accessing __tablename__ triggers the @declared_attr method
        # which executes line 12: return cls.__name__.lower() + "s"
        tablename = TestModel.__tablename__

        # Verify the tablename was generated correctly by line 12
        assert tablename == "testmodels"
        assert tablename.endswith("s")  # Line 12 adds "s" suffix
        assert "testmodel" in tablename  # Line 12 uses .lower()

    def test_multiple_classes_each_execute_line_12(self) -> None:
        """
        Test that each class creation executes line 12 independently.

        This verifies that line 12 is called for each model class.
        """
        # Create multiple test models
        class FirstModel(Base):
            __name__ = "FirstModel"
            # Don't set __tablename__ - let @declared_attr generate it
            id = Column(Integer, primary_key=True)

        class SecondModel(Base):
            __name__ = "SecondModel"
            # Don't set __tablename__ - let @declared_attr generate it
            id = Column(Integer, primary_key=True)

        # Each should have executed line 12 independently
        assert FirstModel.__tablename__ == "firstmodels"
        assert SecondModel.__tablename__ == "secondmodels"

        # Verify they're different (line 12 executed separately)
        assert FirstModel.__tablename__ != SecondModel.__tablename__
