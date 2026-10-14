# Odoo 19.0-20260926. Bump the digest deliberately: docker pull odoo:19.0, then copy its digest here.
FROM odoo:19.0@sha256:dd9013e669caaa23d26765dc55814655eaeecca7cfc2c265dbabae913bce22fd

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

# click-odoo-update for the entrypoint, plus report_xlsx's deps; see requirements.txt
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages --no-deps -r /tmp/requirements.txt \
 && rm /tmp/requirements.txt

# Addons live outside the base image's VOLUME /mnt/extra-addons: Compose keeps anonymous volumes
# across recreates, so code there would survive a rebuild and run stale.
COPY repos.txt build-addons.sh /tmp/
RUN bash /tmp/build-addons.sh /opt/odoo-addons /tmp/repos.txt \
 && rm /tmp/repos.txt /tmp/build-addons.sh

COPY addons/ /opt/odoo-addons/pcp/
COPY config/odoo.conf /etc/odoo/odoo.conf
COPY entrypoint.sh /pcp-entrypoint.sh
RUN chown -R odoo:odoo /opt/odoo-addons /etc/odoo

USER odoo
ENTRYPOINT ["/pcp-entrypoint.sh"]
CMD ["odoo"]
