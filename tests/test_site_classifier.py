"""Tests for deterministic site category classification."""
import pytest
from site_classifier import (
    classify_site,
    ECOMMERCE,
    SAAS,
    BLOG_NEWS,
    DOCUMENTATION,
    GENERIC,
)


def test_classify_ecommerce_site():
    records = [
        {
            "url": "https://store.example.com/products/leather-jacket",
            "title": "Leather Jacket - Buy Now",
            "headings": ["Product Details", "Add to Cart"],
            "text": "Price: $199.00 USD. In stock. Free shipping on orders over $50.",
            "schema_types": ["Product", "Offer"],
            "page_type": "product",
        },
        {
            "url": "https://store.example.com/cart",
            "title": "Shopping Cart",
            "text": "Your shopping bag has items. Proceed to checkout.",
        }
    ]
    res = classify_site("https://store.example.com", records=records)
    assert res["primary"] == ECOMMERCE
    assert "schema_org" in res["evidence_families"]
    assert "url_path" in res["evidence_families"]


def test_classify_saas_site():
    records = [
        {
            "url": "https://app.cloudcorp.io/pricing",
            "title": "Plans & Pricing - CloudCorp",
            "headings": ["Choose Your Plan", "Enterprise Solutions"],
            "text": "Start free trial today. Request demo or view pricing. API documentation included.",
            "schema_types": ["SoftwareApplication"],
        },
        {
            "url": "https://app.cloudcorp.io/features",
            "title": "Platform Features",
            "text": "Sign up free. 14-day trial without credit card.",
        }
    ]
    res = classify_site("https://app.cloudcorp.io", records=records)
    assert res["primary"] == SAAS
    assert "schema_org" in res["evidence_families"]


def test_classify_generic_fallback():
    records = [
        {
            "url": "https://simple.example.com/",
            "title": "Welcome to our page",
            "text": "Hello world.",
        }
    ]
    res = classify_site("https://simple.example.com", records=records)
    assert res["primary"] == GENERIC
    assert res["confidence"] == "low"
