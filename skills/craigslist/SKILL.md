# Craigslist Skill

A generic skill for searching and (future) posting on Craigslist.

## Capability
- Search: Allows searching for items with specific keywords, geography, and price filters.
- Monitor: Can be used to set up recurring cron-based searches.

## Self-Improvement
This skill is designed to be self-improving. Whenever a search yields refined parameters, new reliable keywords, or a better way to filter out spam, update the logic in scripts/search.sh and document the learning here.

## Improving Me (Placeholder)
- Roadmap: Add a "Posting" capability to automate creating Craigslist listings.

## Usage
- Search: `./scripts/search.sh --query "litter robot" --location "sfbay" --price-max 100`

---
*Maintained by Janet*
