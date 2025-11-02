docker restart mep18
docker exec -it mep18 odoo -i base --stop-after-init
docker restart mep18