#!/bin/bash
# Craigslist Search Script
# Usage: ./search.sh --query "search term" --location "sfbay" --price-max 100

QUERY=$2
LOCATION=$4
PRICE_MAX=$6

echo "Searching ${LOCATION} Craigslist for ${QUERY} with max price ${PRICE_MAX}..."
# In a real implementation, this would use a robust scraper/API search
# For now, it logs the intent
