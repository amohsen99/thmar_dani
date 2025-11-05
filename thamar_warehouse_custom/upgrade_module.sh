#!/bin/bash

# Thamar Warehouse Custom - Module Upgrade Script
# This script helps you upgrade the module easily

echo "=========================================="
echo "Thamar Warehouse Custom - Module Upgrade"
echo "=========================================="
echo ""

# Check if database name is provided
if [ -z "$1" ]; then
    echo "Usage: ./upgrade_module.sh <database_name>"
    echo "Example: ./upgrade_module.sh test123"
    echo ""
    exit 1
fi

DB_NAME=$1

echo "Database: $DB_NAME"
echo "Module: thamar_warehouse_custom"
echo ""

# Navigate to Odoo directory
cd /home/mohsen/Documents/thmar-dani/odoo19

echo "Upgrading module..."
./odoo-bin -u thamar_warehouse_custom -d $DB_NAME --stop-after-init

echo ""
echo "=========================================="
echo "Upgrade completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start your Odoo server normally"
echo "2. Go to Settings → Users & Companies → Users"
echo "3. Assign 'Warehouse Keeper' or 'Warehouse Manager' groups to users"
echo "4. Go to Inventory → Configuration → Warehouses"
echo "5. Assign Manager and Keeper to each warehouse"
echo ""

