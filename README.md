# Baserow Table Functions

This project contains Python scripts to automate data synchronization and linking between tables in a Baserow database. The scripts use the Baserow API to fetch, process, and update rows in various tables based on predefined mappings and relationships.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Scripts](#scripts)
  - [baserow_company_investors_link.py](#baserow_company_investors_linkpy)
  - [baserow_deal_investors_link.py](#baserow_deal_investors_linkpy)
  - [baserow_deals_tracker_field_mappings.py](#baserow_deals_tracker_field_mappingspy)
- [Configuration](#configuration)
- [Deployment](#deployment)

## Overview

This project automates the following tasks:

1. Linking investors to companies based on shared identifiers.
2. Linking deals to company investors based on company IDs.
3. Synchronizing field mappings between source and target fields in a deals tracker table.

## Prerequisites

- Python 3.7 or higher
- A valid Baserow API token
- Access to the Baserow database with the required tables and fields

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/baserow-table-functions.git
   cd baserow-table-functions
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Scripts

`baserow_company_investors_link.py`
This script links investors to companies by:

- Fetching all rows from the "Investors" table.
- Creating a mapping of investor_id to row IDs.
- Fetching rows from the "Company Investors" table and updating missing links.

`baserow_deal_investors_link.py`
This script links deals to company investors by:

- Fetching all rows from the "Company Investors" table and mapping company_id to row IDs.
- Fetching rows from the "Deals" table and linking them to matching company investors.

`baserow_deals_tracker_field_mappings.py`
This script synchronizes field mappings in the "Deals Tracker" table by:

- Fetching valid options for multiple and single select fields.
- Matching source field values to target field options.
- Updating rows with the matched options.

## Configuration

Each script requires the following configuration:

- API Token: Replace the API_TOKEN variable with your Baserow API token.
- Base URL: Update the BASE_URL variable if your Baserow instance is hosted on a custom domain.
- Table and Field IDs: Update the table and field IDs in each script to match your database schema.

## Deployment

This project is hosted on Heroku and runs as a scheduled task using a cron job. The scripts are executed at predefined intervals to ensure data synchronization and linking remain up-to-date. To modify the schedule or deployment settings, update the Heroku scheduler configuration.

`https://dashboard.heroku.com/apps/baserow-table-functions`
