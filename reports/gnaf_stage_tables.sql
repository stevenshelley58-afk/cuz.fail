-- G-NAF WA load (MAY 2026, GDA2020 -> EPSG:7844)
-- Run inside psql with \copy from the unzipped Standard/ WA PSV files.
-- Idempotent: stage tables rebuilt each run; final insert ON CONFLICT (gnaf_pid) DO UPDATE.

CREATE SCHEMA IF NOT EXISTS gnaf_stage;

DROP TABLE IF EXISTS gnaf_stage.address_detail;
CREATE TABLE gnaf_stage.address_detail (
  address_detail_pid text, date_created text, date_last_modified text, date_retired text,
  building_name text, lot_number_prefix text, lot_number text, lot_number_suffix text,
  flat_type_code text, flat_number_prefix text, flat_number text, flat_number_suffix text,
  level_type_code text, level_number_prefix text, level_number text, level_number_suffix text,
  number_first_prefix text, number_first text, number_first_suffix text,
  number_last_prefix text, number_last text, number_last_suffix text,
  street_locality_pid text, location_description text, locality_pid text,
  alias_principal text, postcode text, private_street text, legal_parcel_id text,
  confidence text, address_site_pid text, level_geocoded_code text,
  property_pid text, gnaf_property_pid text, primary_secondary text
);

DROP TABLE IF EXISTS gnaf_stage.default_geocode;
CREATE TABLE gnaf_stage.default_geocode (
  address_default_geocode_pid text, date_created text, date_retired text,
  address_detail_pid text, geocode_type_code text, longitude text, latitude text
);

DROP TABLE IF EXISTS gnaf_stage.street_locality;
CREATE TABLE gnaf_stage.street_locality (
  street_locality_pid text, date_created text, date_retired text, street_class_code text,
  street_name text, street_type_code text, street_suffix_code text, locality_pid text,
  gnaf_street_pid text, gnaf_street_confidence text, gnaf_reliability_code text
);

DROP TABLE IF EXISTS gnaf_stage.locality;
CREATE TABLE gnaf_stage.locality (
  locality_pid text, date_created text, date_retired text, locality_name text,
  primary_postcode text, locality_class_code text, state_pid text,
  gnaf_locality_pid text, gnaf_reliability_code text
);
