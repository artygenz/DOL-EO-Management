from __future__ import annotations

"""
Centralized enrichment utilities for chat queries.

This module provides utilities to enrich raw database results with human-readable
information, such as converting UUIDs to user names, emails, etc.

Design principles:
- Centralized: All enrichment logic in one place
- Extensible: Easy to add new enrichment types
- Efficient: Batch operations to minimize database queries
- Type-safe: Clear interfaces and return types
"""

from typing import Dict, List, Any, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.models.user import User


class UserEnrichment:
    """Enriches user-related data with human-readable information."""
    
    def __init__(self, db: Session):
        self.db = db
        self._user_cache: Dict[str, Dict[str, str]] = {}
    
    def enrich_user_ids(self, user_ids: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Enrich a list of user IDs with human-readable information.
        
        Args:
            user_ids: List of user UUIDs to enrich
            
        Returns:
            Dict mapping user_id -> {"name": str, "email": str, "role": str}
        """
        if not user_ids:
            return {}
        
        # Remove duplicates and filter out already cached
        unique_ids = list(set(user_ids))
        uncached_ids = [uid for uid in unique_ids if uid not in self._user_cache]
        
        if uncached_ids:
            # Batch fetch uncached users
            users = self.db.query(User).filter(User.id.in_(uncached_ids)).all()
            for user in users:
                user_id_str = str(user.id)
                self._user_cache[user_id_str] = {
                    "name": user.name or "Unknown User",
                    "email": user.email or "No Email",
                    "role": user.role or "Unknown Role"
                }
        
        # Return enriched data for requested IDs
        return {uid: self._user_cache.get(uid, {
            "name": "Unknown User",
            "email": "No Email", 
            "role": "Unknown Role"
        }) for uid in user_ids}
    
    def enrich_user_id(self, user_id: str) -> Dict[str, str]:
        """Enrich a single user ID."""
        return self.enrich_user_ids([user_id]).get(user_id, {
            "name": "Unknown User",
            "email": "No Email",
            "role": "Unknown Role"
        })


class AggregateEnrichment:
    """Enriches aggregate query results with human-readable information."""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_enrichment = UserEnrichment(db)
    
    def enrich_pmo_aggregates(self, aggregates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich PMO aggregate results with human-readable PMO names.
        
        Args:
            aggregates: List of aggregate results with "group" field containing PMO IDs
            
        Returns:
            Enriched aggregates with human-readable PMO information
        """
        if not aggregates:
            return aggregates
        
        # Extract PMO IDs from aggregates
        pmo_ids = []
        for agg in aggregates:
            if "group" in agg and agg["group"] != "all":
                pmo_ids.append(agg["group"])
        
        # Enrich PMO IDs
        enriched_pmos = self.user_enrichment.enrich_user_ids(pmo_ids)
        
        # Update aggregates with enriched data
        enriched_aggregates = []
        for agg in aggregates:
            enriched_agg = agg.copy()
            group_id = agg.get("group")
            
            if group_id == "all":
                enriched_agg["group_display"] = "All PMOs"
            elif group_id in enriched_pmos:
                pmo_info = enriched_pmos[group_id]
                enriched_agg["group_display"] = f"{pmo_info['name']} ({pmo_info['email']})"
                enriched_agg["pmo_name"] = pmo_info["name"]
                enriched_agg["pmo_email"] = pmo_info["email"]
                enriched_agg["pmo_role"] = pmo_info["role"]
            else:
                enriched_agg["group_display"] = f"Unknown PMO ({group_id})"
            
            enriched_aggregates.append(enriched_agg)
        
        return enriched_aggregates
    
    def enrich_executor_aggregates(self, aggregates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich executor aggregate results with human-readable user names.
        
        Args:
            aggregates: List of aggregate results with "user_id" field
            
        Returns:
            Enriched aggregates with human-readable user information
        """
        if not aggregates:
            return aggregates
        
        # Extract user IDs from aggregates
        user_ids = []
        for agg in aggregates:
            if "user_id" in agg:
                user_ids.append(agg["user_id"])
        
        # Enrich user IDs
        enriched_users = self.user_enrichment.enrich_user_ids(user_ids)
        
        # Update aggregates with enriched data
        enriched_aggregates = []
        for agg in aggregates:
            enriched_agg = agg.copy()
            user_id = agg.get("user_id")
            
            if user_id in enriched_users:
                user_info = enriched_users[user_id]
                enriched_agg["user_name"] = user_info["name"]
                enriched_agg["user_email"] = user_info["email"]
                enriched_agg["user_role"] = user_info["role"]
                enriched_agg["user_display"] = f"{user_info['name']} ({user_info['email']})"
            else:
                enriched_agg["user_name"] = "Unknown User"
                enriched_agg["user_email"] = "No Email"
                enriched_agg["user_role"] = "Unknown Role"
                enriched_agg["user_display"] = f"Unknown User ({user_id})"
            
            enriched_aggregates.append(enriched_agg)
        
        return enriched_aggregates
    
    def enrich_generic_user_aggregates(self, aggregates: List[Dict[str, Any]], group_field: str = "group") -> List[Dict[str, Any]]:
        """
        Enrich generic aggregates where the group field contains user IDs.
        
        Args:
            aggregates: List of aggregate results
            group_field: Field name containing user IDs (default: "group")
            
        Returns:
            Enriched aggregates with human-readable user information
        """
        if not aggregates:
            return aggregates
        
        # Extract user IDs from aggregates
        user_ids = []
        for agg in aggregates:
            group_value = agg.get(group_field)
            if group_value and group_value != "all":
                user_ids.append(group_value)
        
        # Enrich user IDs
        enriched_users = self.user_enrichment.enrich_user_ids(user_ids)
        
        # Update aggregates with enriched data
        enriched_aggregates = []
        for agg in aggregates:
            enriched_agg = agg.copy()
            group_value = agg.get(group_field)
            
            if group_value == "all":
                enriched_agg[f"{group_field}_display"] = "All Users"
            elif group_value in enriched_users:
                user_info = enriched_users[group_value]
                enriched_agg[f"{group_field}_display"] = f"{user_info['name']} ({user_info['email']})"
                enriched_agg[f"{group_field}_name"] = user_info["name"]
                enriched_agg[f"{group_field}_email"] = user_info["email"]
                enriched_agg[f"{group_field}_role"] = user_info["role"]
            else:
                enriched_agg[f"{group_field}_display"] = f"Unknown User ({group_value})"
            
            enriched_aggregates.append(enriched_agg)
        
        return enriched_aggregates


def create_enrichment(db: Session) -> AggregateEnrichment:
    """Factory function to create an enrichment instance."""
    return AggregateEnrichment(db)
