environment variables in docker compose

❌ Avoid putting DB credentials in environment: section
Even though Docker lets you pass things like HOST, USER, PASSWORD via environment variables, Odoo itself does not use those by default. It only uses the config file unless you explicitly pass them via command-line, which is rarely needed.

✅ In short:
Use etc/odoo.conf for DB connection settings — it’s cleaner, more secure, and works as expected with Odoo in Docker.

Let me know if you want help securing your config file or managing secrets in production setups.








