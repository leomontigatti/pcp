FROM odoo:19.0

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

# report_xlsx (OCA) is the only addon with python deps outside Odoo's own requirements
RUN pip3 install --no-cache-dir --break-system-packages xlsxwriter xlrd

COPY repos.txt build-addons.sh /tmp/
RUN bash /tmp/build-addons.sh /mnt/extra-addons /tmp/repos.txt \
 && rm /tmp/repos.txt /tmp/build-addons.sh

COPY addons/ /mnt/extra-addons/pcp/
COPY config/odoo.conf /etc/odoo/odoo.conf
RUN chown -R odoo:odoo /mnt/extra-addons /etc/odoo/odoo.conf

USER odoo
