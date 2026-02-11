from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class CustomerTier(Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"

@dataclass
class CustomerActivity:
    last_purchase_date: datetime      # Days since last purchase
    total_orders_12m: int             # Orders in last 12 months
    total_spend_12m: float            # $ spent in last 12 months
    account_age_days: int             # How long they've been a customer

class SegmentationEngine:
    def __init__(self, reference_date: Optional[datetime] = None):
        """
        reference_date: Used to calculate "recency" (days since last purchase).
                       Defaults to today.
        """
        self.reference_date = reference_date or datetime.now()

    def _apply_constraints(self, customer: CustomerActivity, current_tier: CustomerTier) -> CustomerTier:
        if self.reference_date < customer.last_purchase_date:
            raise ValueError("Reference date must be after last purchase date")
            
        if customer.account_age_days < 30 and current_tier != CustomerTier.BRONZE:
            return CustomerTier.SILVER
        else:
            return current_tier

    @staticmethod
    def _recency_score(days_since_purchase: int) -> float:
        return max(0, 40 - (days_since_purchase * 40 / 365))

    @staticmethod
    def _map_score_to_tier(score: float) -> CustomerTier:
        if score >= 85:
            return CustomerTier.PLATINUM
        elif score >= 70:
            return CustomerTier.GOLD
        elif score >= 50:
            return CustomerTier.SILVER
        else:
            return CustomerTier.BRONZE

    @staticmethod
    def _frequency_score(total_orders_12m: int) -> float:
        points_per_order = 3
        return min(30, min(100, total_orders_12m) * points_per_order)
    
    @staticmethod
    def _monetary_score(total_spend_12m: float) -> float:
        points_per_dollar = 0.03
        return max(0, min(30, total_spend_12m * points_per_dollar))
        
    def calculate_tier(self, customer: CustomerActivity) -> CustomerTier:
        """
        Assign tier based on RFM scoring:
        
        SCORING (0-100 total):
        - Recency (0-40): 0 days = 40 pts, 365+ days = 0 pts
        - Frequency (0-30): 0 orders = 0 pts, 10+ orders = 30 pts  
        - Monetary (0-30): $0 = 0 pts, $1000+ = 30 pts
    
        Example:
        (recency * 0.4) + (frequency * 0.3) + (monetary * 0.3) = total_score
        
        TIER THRESHOLDS:
        - Platinum: 85+ points
        - Gold: 70-84 points
        - Silver: 50-69 points
        - Bronze: <50 points
        
        CONSTRAINTS/EDGE CASES:
        - New customers (account_age < 30 days) capped at SILVER max
        - If total_spend_12m < 0, treat as 0 (refunds don't negate)
        - If total_orders_12m > 100, cap at 100 for calculation
        - Reference date must be after last_purchase_date
        
        Returns the appropriate CustomerTier.
        """
  
       
        recency_score = self._recency_score((self.reference_date - customer.last_purchase_date).days)
        frequency_score = self._frequency_score(customer.total_orders_12m)
        monetary_score = self._monetary_score(customer.total_spend_12m)
        score = int( recency_score + frequency_score + monetary_score)
       
        return self._apply_constraints(customer, self._map_score_to_tier(score))