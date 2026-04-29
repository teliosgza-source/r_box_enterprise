"""
Database models matching existing schema
"""
from sqlalchemy import Column, Integer, String, BigInteger, JSON, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

Base = declarative_base()

class TeliosGeojson(Base):
    """Matches existing teliosgeojson table structure"""
    __tablename__ = 'teliosgeojson'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    unitid = Column(BigInteger, unique=True, nullable=False)
    parent_id = Column(BigInteger)
    country_id = Column(Integer)
    levelid = Column(Integer)
    levelkey = Column(String(100))
    tellevelkey = Column(String(200))
    countnextlevel = Column(Integer)
    unit = Column(String(200))
    geo_json = Column(JSONB)  # This matches the column name in the table
    # created_at may or may not exist, so we'll make it optional
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=True)

class TeliosGeojsonData(Base):
    """Matches existing teliosgeojsondata table structure"""
    __tablename__ = 'teliosgeojsondata'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    teliosgeojson_id = Column(BigInteger, unique=True, nullable=False)
    geojson = Column(JSONB)
    levelkey = Column(String(50), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=True)
