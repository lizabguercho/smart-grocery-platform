-- ============================================================
-- Smart Grocery Platform: Load Classifications & Create Views
-- ============================================================
-- Safe transactional load of all 14,816 comparable product classifications
-- into grocery.product_classification, followed by the Tableau view definition.
-- ============================================================

BEGIN;

-- 1. Create temporary staging table
CREATE TEMP TABLE staging_product_classification (
    item_code BIGINT,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    include_in_analysis BOOLEAN,
    classification_method VARCHAR(50),
    classification_confidence NUMERIC(4,3)
);

-- 2. Populate staging from CSV
\copy staging_product_classification FROM 'data/processed/product_classification_table.csv' WITH (FORMAT csv, HEADER true);

-- 3. Insert into grocery.product_classification with conflict safety
INSERT INTO grocery.product_classification (
    item_code,
    category,
    subcategory,
    include_in_analysis,
    classification_method,
    classification_confidence
)
SELECT 
    item_code,
    category,
    NULLIF(TRIM(subcategory), ''),
    include_in_analysis,
    classification_method,
    classification_confidence
FROM staging_product_classification
ON CONFLICT (item_code) DO UPDATE SET
    category = EXCLUDED.category,
    subcategory = EXCLUDED.subcategory,
    include_in_analysis = EXCLUDED.include_in_analysis,
    classification_method = EXCLUDED.classification_method,
    classification_confidence = EXCLUDED.classification_confidence;

-- 4. Create primary analytical Tableau view: grocery.v_price_comparison_with_categories
CREATE OR REPLACE VIEW grocery.v_price_comparison_with_categories AS
SELECT
    pc.item_code,
    p.item_name,
    p.manufacture_name,
    p.unit_qty,
    p.quantity,
    p.unit_of_measure,
    p.is_weighted,
    cl.category,
    cl.subcategory,
    cl.include_in_analysis,
    cl.classification_method,
    
    -- Representative chain prices (median store price per chain, strictly positive)
    CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price ELSE NULL END AS shufersal_price,
    CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price ELSE NULL END AS rami_levy_price,
    CASE WHEN pc.victory_price > 0 THEN pc.victory_price ELSE NULL END AS victory_price,
    
    -- Chains compared count (must be >= 2 for comparable items)
    (
        CASE WHEN pc.shufersal_price > 0 THEN 1 ELSE 0 END +
        CASE WHEN pc.rami_levy_price > 0 THEN 1 ELSE 0 END +
        CASE WHEN pc.victory_price > 0 THEN 1 ELSE 0 END
    ) AS chains_compared,
    
    CASE 
        WHEN (
            CASE WHEN pc.shufersal_price > 0 THEN 1 ELSE 0 END +
            CASE WHEN pc.rami_levy_price > 0 THEN 1 ELSE 0 END +
            CASE WHEN pc.victory_price > 0 THEN 1 ELSE 0 END
        ) = 3 THEN 'All 3 Chains'
        ELSE '2 Chains Only'
    END AS chain_availability,
    
    -- Cheapest and highest representative prices across valid chains
    LEAST(
        CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
        CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
        CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
    ) AS cheapest_price,
    
    GREATEST(
        CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
        CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
        CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
    ) AS highest_price,
    
    -- Cheapest chain label
    pc.cheapest_chain,
    
    -- Absolute cross-chain price difference
    (
        GREATEST(
            CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
            CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
            CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
        )
        -
        LEAST(
            CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
            CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
            CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
        )
    ) AS price_difference,
    
    -- Cross-chain price difference percentage (spread over cheapest price)
    ROUND(
        (
            GREATEST(
                CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
                CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
                CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
            )
            -
            LEAST(
                CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
                CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
                CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
            )
        ) * 100.0 /
        NULLIF(
            LEAST(
                CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
                CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
                CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
            ),
            0
        ),
        2
    ) AS price_difference_pct,
    
    -- Chain-specific price difference percentage vs cheapest
    CASE 
        WHEN pc.shufersal_price > 0 THEN
            ROUND(
                (pc.shufersal_price - LEAST(
                    CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
                    CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
                    CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
                )) * 100.0 /
                NULLIF(LEAST(
                    CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
                    CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
                    CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
                ), 0),
                2
            )
        ELSE NULL
    END AS shufersal_diff_pct,
    
    CASE 
        WHEN pc.rami_levy_price > 0 THEN
            ROUND(
                (pc.rami_levy_price - LEAST(
                    CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
                    CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
                    CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
                )) * 100.0 /
                NULLIF(LEAST(
                    CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
                    CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
                    CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
                ), 0),
                2
            )
        ELSE NULL
    END AS rami_levy_diff_pct,
    
    CASE 
        WHEN pc.victory_price > 0 THEN
            ROUND(
                (pc.victory_price - LEAST(
                    CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
                    CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
                    CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
                )) * 100.0 /
                NULLIF(LEAST(
                    CASE WHEN pc.shufersal_price > 0 THEN pc.shufersal_price END,
                    CASE WHEN pc.rami_levy_price > 0 THEN pc.rami_levy_price END,
                    CASE WHEN pc.victory_price > 0 THEN pc.victory_price END
                ), 0),
                2
            )
        ELSE NULL
    END AS victory_diff_pct

FROM grocery.price_comparison AS pc
JOIN grocery.product_classification AS cl
    ON cl.item_code = pc.item_code
LEFT JOIN grocery.products AS p
    ON p.item_code = pc.item_code
WHERE (
    (CASE WHEN pc.shufersal_price > 0 THEN 1 ELSE 0 END +
     CASE WHEN pc.rami_levy_price > 0 THEN 1 ELSE 0 END +
     CASE WHEN pc.victory_price > 0 THEN 1 ELSE 0 END) >= 2
);

-- Also update grocery.price_comparison_with_categories for complete parity
CREATE OR REPLACE VIEW grocery.price_comparison_with_categories AS
SELECT * FROM grocery.v_price_comparison_with_categories;

COMMIT;
