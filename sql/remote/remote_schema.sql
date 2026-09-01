--
-- PostgreSQL database dump
--
-- Dumped from database version 16.11 (Homebrew)
-- Dumped by pg_dump version 16.11 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: products; Type: TABLE; Schema: grocery; Owner: -
--

CREATE TABLE grocery.products (
    item_code bigint NOT NULL,
    item_name text,
    manufacture_name text,
    manufacture_country text,
    manufacture_item_description text,
    unit_qty text,
    quantity numeric,
    unit_of_measure text,
    is_weighted boolean,
    qty_in_package integer,
    item_type integer
);


--
-- Name: chain_prices; Type: TABLE; Schema: grocery; Owner: -
--

CREATE TABLE grocery.chain_prices (
    item_code bigint NOT NULL,
    chain_id bigint NOT NULL,
    median_price numeric(10,2)
);


--
-- Name: price_comparison; Type: TABLE; Schema: grocery; Owner: -
--

CREATE TABLE grocery.price_comparison (
    item_code bigint NOT NULL,
    shufersal_price numeric(10,2),
    rami_levy_price numeric(10,2),
    victory_price numeric(10,2),
    cheapest_price numeric(10,2),
    cheapest_chain text
);


--
-- Name: product_classification; Type: TABLE; Schema: grocery; Owner: -
--

CREATE TABLE grocery.product_classification (
    item_code bigint NOT NULL,
    category character varying(100),
    subcategory character varying(100),
    include_in_analysis boolean,
    classification_method character varying(50),
    classification_confidence numeric(4,3)
);


--
-- Name: stores; Type: TABLE; Schema: grocery; Owner: -
--

CREATE TABLE grocery.stores (
    chain_id bigint NOT NULL,
    store_id integer NOT NULL,
    chain_name text,
    sub_chain_id integer,
    sub_chain_name text,
    bikoret_no integer,
    store_type integer,
    store_name text,
    address text,
    city text,
    zip_code text,
    source_file text,
    extraction_date date
);


--
-- Name: chain_prices chain_prices_pkey; Type: CONSTRAINT; Schema: grocery; Owner: -
--

ALTER TABLE ONLY grocery.chain_prices
    ADD CONSTRAINT chain_prices_pkey PRIMARY KEY (item_code, chain_id);


--
-- Name: price_comparison price_comparison_pkey; Type: CONSTRAINT; Schema: grocery; Owner: -
--

ALTER TABLE ONLY grocery.price_comparison
    ADD CONSTRAINT price_comparison_pkey PRIMARY KEY (item_code);


--
-- Name: product_classification product_classification_pkey; Type: CONSTRAINT; Schema: grocery; Owner: -
--

ALTER TABLE ONLY grocery.product_classification
    ADD CONSTRAINT product_classification_pkey PRIMARY KEY (item_code);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: grocery; Owner: -
--

ALTER TABLE ONLY grocery.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (item_code);


--
-- Name: stores stores_pk; Type: CONSTRAINT; Schema: grocery; Owner: -
--

ALTER TABLE ONLY grocery.stores
    ADD CONSTRAINT stores_pk PRIMARY KEY (chain_id, store_id);


--
-- Name: chain_prices chain_prices_item_code_fkey; Type: FK CONSTRAINT; Schema: grocery; Owner: -
--

ALTER TABLE ONLY grocery.chain_prices
    ADD CONSTRAINT chain_prices_item_code_fkey FOREIGN KEY (item_code) REFERENCES grocery.products(item_code);


--
-- Name: product_classification fk_product_classification_product; Type: FK CONSTRAINT; Schema: grocery; Owner: -
--

ALTER TABLE ONLY grocery.product_classification
    ADD CONSTRAINT fk_product_classification_product FOREIGN KEY (item_code) REFERENCES grocery.products(item_code);


--
-- PostgreSQL database dump complete


