"""Many-to-many association tables linking products to global charges.

Note: product_utility_charges, product_labour_charges, and product_tax_charges
were removed in migration 042. Utility/labour are now tracked as monthly overhead
entries, and taxes are applied at the order level.
"""
