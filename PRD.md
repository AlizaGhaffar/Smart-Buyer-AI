# Product Requirements Document (PRD) — Mamu Export Lead Finder

## 1. Problem Statement
Mamu raw materials (Raw Sheep Wool, Cashmere, Duck Down) export karte hain aur unhein international buyers ki verified **contact list (Emails & Phone Numbers)** chahiye hoti hai taake woh business outreach kar sakein.

Currently, buyers dhoondhne ka process bohot manual, time-consuming aur tiring hai:
1. Google par har country ke importers search karna.
2. Har website ko individual open karke verify karna ke woh actual buyer hain ya nahi.
3. Website par ja kar publicly listed contact emails (e.g., info@, sales@) aur phone numbers dhoondhna.
4. Un saare contacts aur URLs ko manually Excel sheet mein copy-paste karna aur yeh process baar-baar repeat karna.

Is manual process mein ghanto zaya ho jaate hain. Mamu ko ek aisa automated, zero-cost tool chahiye jo ek click par relevant buyer candidates dhoondh kar unke **verified contacts (Email/Phone)** aur **source links** ke sath ek downloadable **CSV/Excel sheet** tayyar kar ke de de.

## 2. Target Audience
- **Persona:** Mamu (B2B Raw Material Exporter)
- **Need:** Zero-setup, ultra-fast web tool with beautiful UI, direct source verification links, extracted email/phone leads, and instant CSV export.

## 3. Core Features
1. Multi-product selection + Custom product & country text input.
2. Free DuckDuckGo search + Python scraping engine.
3. Rule-based buyer scoring and Regex public contact (Email/Phone) extraction.
4. Animated Next.js dashboard with source URL badges and one-click CSV export.