/*
PRICE COMPARISON TABLE

Purpose:
Create one row per comparable product with the representative
price for each supermarket chain and identify the cheapest chain.
*/

-- 1. Create the table
CREATE TABLE grocery.price_comparison (
    item_code BIGINT PRIMARY KEY,
    shufersal_price NUMERIC(10,2),
    rami_levy_price NUMERIC(10,2),
    victory_price NUMERIC(10,2),
    cheapest_price NUMERIC(10,2),
    cheapest_chain TEXT
);

-- 2. Populate / refresh the table
/*1. TRUNCATE
   clears old comparison rows

2. pivoted_prices
   converts one row per product+chain
   into one row per product with 3 price columns

3. with_cheapest_price
   adds the lowest available price

4. with_cheapest_chain
   adds the winning chain or Tie

5. INSERT INTO grocery.price_comparison
   saves the final result permanently*/

TRUNCATE TABLE grocery.price_comparison;

WITH pivoted_prices AS (
    SELECT
        cp.item_code,

        MAX(
            CASE
                WHEN cp.chain_id = 7290027600007
                THEN cp.median_price
            END
        ) AS shufersal_price,
		
		MAX(
            CASE
                WHEN cp.chain_id = 7290058140886
                THEN cp.median_price
            END
        ) AS rami_levy_price,
		
		MAX(
		CASE
			WHEN cp.chain_id = 7290696200003
			THEN cp.median_price
		END
		) AS victory_price
	FROM grocery.chain_prices cp
	GROUP BY cp.item_code
),

with_cheapest_price as (
select 
	*,
	LEAST(
		shufersal_price,
		rami_levy_price,
		victory_price
	) AS cheapest_price
from pivoted_prices
),

with_cheapest_chain AS (
    SELECT
        *,
		CASE 
			WHEN shufersal_price = cheapest_price AND rami_levy_price = cheapest_price AND victory_price = cheapest_price THEN 'All three'
			WHEN shufersal_price = cheapest_price AND rami_levy_price = cheapest_price THEN 'Shufersal & Rami Levy'
			WHEN shufersal_price = cheapest_price AND victory_price = cheapest_price THEN 'Shufersal & Victory' 
			WHEN rami_levy_price = cheapest_price AND victory_price = cheapest_price THEN 'Rami Levy & Victory' 
			WHEN shufersal_price = cheapest_price THEN 'Shufersal' 
			WHEN rami_levy_price = cheapest_price THEN 'Rami Levy' 
			WHEN victory_price = cheapest_price THEN 'Victory' 
		END AS cheapest_chain
	from with_cheapest_price
)
INSERT INTO grocery.price_comparison (
    item_code,
    shufersal_price,
    rami_levy_price,
    victory_price,
    cheapest_price,
    cheapest_chain
)
SELECT
    item_code,
    shufersal_price,
    rami_levy_price,
    victory_price,
    cheapest_price,
    cheapest_chain
FROM with_cheapest_chain;
SELECT *
FROM grocery.price_comparison
LIMIT 20;
