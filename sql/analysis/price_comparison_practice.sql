--1. Find products available in at least 2 chains.
select lp.item_code,
lp.item_name,
count(Distinct lp.chain_id) as number_of_chains
from grocery.latest_product_prices lp
group by lp.item_code,lp.item_name
having count(distinct lp.chain_id)>=2;

--2. Calculate one representative price for each product in each chain.
select 
lp.item_code,
lp.chain_id,
percentile_cont(0.5)
	within group (order by lp.item_price) as median_price
from grocery.latest_product_prices lp
where lp.item_price > 0
group by lp.item_code,lp.chain_id;

--3. Build CTE for comparable items

with comparable_products as (
	select lp.item_code
	from grocery.latest_product_prices lp
	group by lp.item_code
	having count(distinct lp.chain_id)>=2
) 
select lp.item_code,
lp.chain_id,
percentile_cont(0.5)
	within group (order by lp.item_price) as median_price
from grocery.latest_product_prices lp
join comparable_products cp on lp.item_code = cp.item_code
where lp.item_price > 0
group by lp.item_code,lp.chain_id;

--4. Put each chain's price into its own column.
with comparable_products as (
	select lp.item_code
	from grocery.latest_product_prices lp
	group by lp.item_code
	having count(distinct lp.chain_id)>=2
),
chain_prices as (
		select lp.item_code,
		lp.chain_id,
		percentile_cont(0.5)
			within group (order by lp.item_price) as median_price
	FROM grocery.latest_product_prices lp
	JOIN comparable_products cp
	    ON lp.item_code = cp.item_code
	WHERE lp.item_price > 0
	GROUP BY
	    lp.item_code,
	    lp.chain_id
)

SELECT 
	cp.item_code,
	Max (CASE 
			WHEN cp.chain_id = 7290027600007
			THEN cp.median_price
		END
	) as shufersal_price,
	Max (CASE 
			WHEN cp.chain_id = 7290058140886
			THEN cp.median_price
		END
	) as rami_levy_price,
	Max (CASE 
			WHEN cp.chain_id = 7290696200003
			THEN cp.median_price
		END
	) as victory_price
From chain_prices cp
Group by cp.item_code;

--5. Find the cheapest price for each product.

with comparable_products as (
	select lp.item_code
	from grocery.latest_product_prices lp
	group by lp.item_code
	having count(distinct lp.chain_id)>=2
),
chain_prices as (
		select lp.item_code,
		lp.chain_id,
		percentile_cont(0.5)
			within group (order by lp.item_price) as median_price
	FROM grocery.latest_product_prices lp
	JOIN comparable_products cp
	    ON lp.item_code = cp.item_code
	WHERE lp.item_price > 0
	GROUP BY
	    lp.item_code,
	    lp.chain_id
),
price_comparison as (

	SELECT 
		cp.item_code,
		Max (CASE 
				WHEN cp.chain_id = 7290027600007
				THEN cp.median_price
			END
		) as shufersal_price,
		Max (CASE 
				WHEN cp.chain_id = 7290058140886
				THEN cp.median_price
			END
		) as rami_levy_price,
		Max (CASE 
				WHEN cp.chain_id = 7290696200003
				THEN cp.median_price
			END
		) as victory_price
	From chain_prices cp
	Group by cp.item_code
),
with_cheapest_price as (
	select 
		*,
		LEAST(
		    shufersal_price,
		    rami_levy_price,
		    victory_price
		) AS cheapest_price

from price_comparison
) 
select 
	*,
	CASE 
		WHEN shufersal_price = cheapest_price AND rami_levy_price = cheapest_price THEN 'Tie'
		WHEN shufersal_price = cheapest_price AND victory_price = cheapest_price THEN 'Tie' 
		WHEN rami_levy_price = cheapest_price AND victory_price = cheapest_price THEN 'Tie' 
		WHEN shufersal_price = cheapest_price THEN 'Shufersal' 
		WHEN rami_levy_price = cheapest_price THEN 'Rami Levy' 
		WHEN victory_price = cheapest_price THEN 'Victory' 
	END AS cheapest_chain
from with_cheapest_price;







