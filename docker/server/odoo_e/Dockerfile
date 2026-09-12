# Match the production Odoo version used by the server compose file.
FROM odoo:19.0
# Switch to root user
USER root
RUN apt-get update && apt-get install -y nodejs npm \
    && npm install -g less less-plugin-clean-css \
    && pip3 install --no-cache-dir pyzk \
    && apt-get clean
# Install Python package hijri-converter to /usr/lib/python3/dist-packages # default odoo path
# RUN pip install --target=/usr/lib/python3/dist-packages hijri_converter==2.3.1
# Install Python package hijri-converter
# RUN pip3 install hijri-converter==2.3.1
# pip install hijri_converter==2.3.1
# Upgrade pip to the latest version and install hijri-converter
# RUN pip install --upgrade pip && \
#     pip install hijri_converter==2.3.1
# Copy your custom Odoo addons if needed (optional)
# COPY ./addons /mnt/extra-addons
# Set the entrypoint (Odoo entrypoint is already handled)
# Switch back to the Odoo user
USER odoo
