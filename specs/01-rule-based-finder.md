# Spec 01: Dynamic & Multi-Product Buyer Finder

> **Status:** superseded in part. Spec 03 replaces the keyword scoring and single-step output described here.

## Goal
Support single, multi-product, and custom product searches using DuckDuckGo search, HTML scraping, rule-based keyword scoring, and regex contact extraction without an LLM.

## Requirements
1. Query builder supporting multiple products or custom product text inputs.
2. Keyword scoring (+25 for buyer terms, +25 for product match).
3. Regex extraction for public email addresses and phone numbers.
4. Output JSON schema containing: company_name, website, relevance_score, matched_keywords, contact_info, source_url.