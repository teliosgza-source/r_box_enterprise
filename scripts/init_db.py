-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create tables
CREATE TABLE IF NOT EXISTS unit (
    unitid BIGINT PRIMARY KEY,
    parentid BIGINT,
    country_id INTEGER NOT NULL,
    country VARCHAR(100),
    country_code VARCHAR(3),
    levelDescription VARCHAR(50),
    countryLevelId INTEGER,
    levelKey VARCHAR(100),
    telioslevelKey VARCHAR(200) UNIQUE,
    countnextLevel INTEGER DEFAULT 0,
    unit VARCHAR(200),
    parentlevelKey VARCHAR(100),
    teliosparentlevelKey VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS psql_geo (
    id BIGSERIAL PRIMARY KEY,
    unitid BIGINT REFERENCES unit(unitid),
    parent_id BIGINT,
    country_id INTEGER,
    levelid INTEGER,
    levelkey VARCHAR(100),
    tellevelkey VARCHAR(200),
    countnextlevel INTEGER,
    unit VARCHAR(200),
    geometry JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teliosgeojson (
    id BIGSERIAL PRIMARY KEY,
    unitid BIGINT REFERENCES unit(unitid),
    parent_id BIGINT,
    country_id INTEGER,
    levelid INTEGER,
    levelkey VARCHAR(100),
    tellevelkey VARCHAR(200),
    countnextlevel INTEGER,
    unit VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teliosgeojsondata (
    id BIGSERIAL PRIMARY KEY,
    teliosgeojson_id BIGINT REFERENCES teliosgeojson(unitid),
    geojson JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_unit_parentid ON unit(parentid);
CREATE INDEX idx_unit_country_id ON unit(country_id);
CREATE INDEX idx_unit_telioslevelKey ON unit(telioslevelKey);
CREATE INDEX idx_unit_country ON unit(country);

CREATE INDEX idx_psql_geo_unitid ON psql_geo(unitid);
CREATE INDEX idx_psql_geo_tellevelkey ON psql_geo(tellevelkey);

CREATE INDEX idx_teliosgeojson_unitid ON teliosgeojson(unitid);
CREATE INDEX idx_teliosgeojsondata_id ON teliosgeojsondata(teliosgeojson_id);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_unit_updated_at BEFORE UPDATE
    ON unit FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();