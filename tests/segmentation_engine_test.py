from datetime import datetime, timedelta

import pytest  # pylint: disable=import-error

from app import CustomerActivity, CustomerTier, SegmentationEngine

# pylint: disable=redefined-outer-name  # pytest fixtures are injected by param name



@pytest.fixture
def reference_date():
    """Fixed reference date for deterministic tests."""
    return datetime.now()


@pytest.fixture
def engine(reference_date):
    """Shared SegmentationEngine instance for tests using default reference_date."""
    return SegmentationEngine(reference_date=reference_date)

class TestRecency:
    """Tests for recency scoring (days since last purchase)."""

    def test_new_customer_purchased_today_is_bronze(self, engine, reference_date):
        new_customer = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=1,
            total_spend_12m=0,
            account_age_days=365,
        )
        assert engine.calculate_tier(new_customer) == CustomerTier.BRONZE

    def test_old_customer_with_no_purchases_is_bronze(self, engine, reference_date):
        old_customer = CustomerActivity(
            last_purchase_date=reference_date - timedelta(days=400),
            total_orders_12m=0,
            total_spend_12m=0,
            account_age_days=401,
        )
        assert engine.calculate_tier(old_customer) == CustomerTier.BRONZE

    def test_mid_recency_customer_bronze(self, engine, reference_date):
        mid_recency_customer = CustomerActivity(
            last_purchase_date=reference_date - timedelta(days=182),
            total_orders_12m=1,
            total_spend_12m=10,
            account_age_days=181,
        )
        assert engine.calculate_tier(mid_recency_customer) == CustomerTier.BRONZE


class TestFrequency:
    """Tests for frequency scoring (orders in last 12 months)."""

    def test_mid_frequency_and_recent_purchase_is_silver(self, engine, reference_date):
        mid_frequency_and_recent_purchase = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=5,
            total_spend_12m=0,
            account_age_days=365,
        )
        assert engine.calculate_tier(mid_frequency_and_recent_purchase) == CustomerTier.SILVER

    def test_max_frequency_is_gold(self, engine, reference_date):
        max_frequency = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=10,
            total_spend_12m=0,
            account_age_days=365,
        )
        assert engine.calculate_tier(max_frequency) == CustomerTier.GOLD

    def test_frequency_is_capped_at_30(self, engine, reference_date):
        max_frequency = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=100,
            total_spend_12m=0,
            account_age_days=365,
        )
        assert engine.calculate_tier(max_frequency) == CustomerTier.GOLD


class TestSpend:
    """Tests for monetary scoring (spend in last 12 months)."""

    def test_on_day_high_spend_is_gold(self, engine, reference_date):
        high_spend_customer = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=0,
            total_spend_12m=1000,
            account_age_days=365,
        )
        assert engine.calculate_tier(high_spend_customer) == CustomerTier.GOLD
    
    def test_over_cap_spend_is_gold(self, engine, reference_date):
        over_cap_spend_customer = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=0,
            total_spend_12m=5000,
            account_age_days=365,
        )
        assert engine.calculate_tier(over_cap_spend_customer) == CustomerTier.GOLD

    def test_mid_on_day_spend_is_silver(self, engine, reference_date):
        mid_on_day_spend_customer = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=0,
            total_spend_12m=500,
            account_age_days=1,
        )
        assert engine.calculate_tier(mid_on_day_spend_customer) == CustomerTier.SILVER

class TestBoundary:
    """Tests for boundary conditions."""

    def test_exact_boundary_is_platinum(self, engine, reference_date):
        """~136 days ago: recency≈25 + 30 + 30 = 85."""
        exact_boundary_customer = CustomerActivity(
            last_purchase_date=reference_date - timedelta(days=136),
            total_orders_12m=10,
            total_spend_12m=1000,
            account_age_days=200,
        )
        assert engine.calculate_tier(exact_boundary_customer) == CustomerTier.PLATINUM

    def test_exact_to_next_boundary_is_gold(self, engine, reference_date):
        """~137 days ago: recency≈25 + 30 + 30 = 84 (just below PLATINUM)."""
        exact_to_next_boundary_customer = CustomerActivity(
            last_purchase_date=reference_date - timedelta(days=137),
            total_orders_12m=10,
            total_spend_12m=1000,
            account_age_days=200,
        )
        assert engine.calculate_tier(exact_to_next_boundary_customer) == CustomerTier.GOLD

    def test_exact_to_previous_boundary_is_gold(self, engine, reference_date):
        """270 days ago: recency≈10 + 30 + 30 = 70."""
        exact_to_previous_boundary_customer = CustomerActivity(
            last_purchase_date=reference_date - timedelta(days=270),
            total_orders_12m=10,
            total_spend_12m=1000,
            account_age_days=200,
        )
        assert engine.calculate_tier(exact_to_previous_boundary_customer) == CustomerTier.GOLD

    def test_exact_to_next_boundary_is_silver(self, engine, reference_date):
        exact_to_next_boundary_customer = CustomerActivity(
            last_purchase_date=reference_date - timedelta(days=280),
            total_orders_12m=10,
            total_spend_12m=1000,
            account_age_days=200,
        )
        assert engine.calculate_tier(exact_to_next_boundary_customer) == CustomerTier.SILVER

    def test_exact_to_previous_boundary_is_silver(self, engine, reference_date):
        customer = CustomerActivity(
            last_purchase_date=reference_date - timedelta(days=1000),
            total_orders_12m=10,
            total_spend_12m=700,
            account_age_days=100,
        )
        assert engine.calculate_tier(customer) == CustomerTier.SILVER


    def test_exact_boundary_score_49_is_bronze(self, engine, reference_date):
        customer = CustomerActivity(
            last_purchase_date=reference_date - timedelta(days=300),  # ≈9 points
            total_orders_12m=7,     
            total_spend_12m=666.66,
            account_age_days=200,
        )
        assert engine.calculate_tier(customer) == CustomerTier.BRONZE



class TestEdgeCasesAndConstraints:
    """Tests for edge cases and constraints."""

    def test_new_customer_capped_at_silver(self, engine, reference_date):
        new_customer = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=30,
            total_spend_12m=1000,
            account_age_days=0,
        )
        assert engine.calculate_tier(new_customer) == CustomerTier.SILVER

    def test_new_customer_already_silver_is_silver(self, engine, reference_date):
        new_customer = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=30,
            total_spend_12m=500,
            account_age_days=15,
        )
        assert engine.calculate_tier(new_customer) == CustomerTier.SILVER
    
    def test_new_customer_already_bronze_is_bronze(self, engine, reference_date):
        new_customer = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=1,
            total_spend_12m=0,
            account_age_days=5,
        )
        assert engine.calculate_tier(new_customer) == CustomerTier.BRONZE
    
    def test_account_exact_30_days_is_not_capped(self, engine, reference_date):
        customer = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=30,
            total_spend_12m=1000,
            account_age_days=30,
        )
        assert engine.calculate_tier(customer) == CustomerTier.PLATINUM
    
    def test_negative_spend_is_treated_as_0(self, engine, reference_date):
        customer = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=0,
            total_spend_12m=-50,
            account_age_days=0,
        )
        assert engine.calculate_tier(customer) == CustomerTier.BRONZE
    
    def test_order_is_capped_at_100(self, engine, reference_date):
        customer = CustomerActivity(
            last_purchase_date=reference_date,
            total_orders_12m=150,
            total_spend_12m=0,
            account_age_days=0,
        )
        assert engine.calculate_tier(customer) == CustomerTier.SILVER

    def test_reference_date_before_last_purchase_date_raises_error(self):
        last_purchase = datetime.now()
        reference_date = last_purchase - timedelta(days=1)
        customer = CustomerActivity(
            last_purchase_date=last_purchase,
            total_orders_12m=5,
            total_spend_12m=200,
            account_age_days=50,
        )
        engine = SegmentationEngine(reference_date=reference_date)
        
        with pytest.raises(ValueError):
            engine.calculate_tier(customer)


class TestRealisticCustomers:
    def test_realistic_churning_customer_is_bronze(self, engine, reference_date):
        churning_customer = CustomerActivity(
            last_purchase_date=reference_date - timedelta(days=300),
            total_orders_12m=2,
            total_spend_12m=100,
            account_age_days=3 * 365,
        )
        assert engine.calculate_tier(churning_customer) == CustomerTier.BRONZE

    def test_zero_everything_is_bronze(self, engine, reference_date):
        zero_customer = CustomerActivity(
            last_purchase_date=reference_date - timedelta(days=400),
            total_orders_12m=0,
            total_spend_12m=0,
            account_age_days=500,
        )
        assert engine.calculate_tier(zero_customer) == CustomerTier.BRONZE
