FROM odoo:18.0

USER root
COPY odoo.conf /etc/odoo/odoo.conf
COPY entrypoint.sh /entrypoint-cortoba.sh
COPY addons/ /mnt/extra-addons/
RUN chmod +x /entrypoint-cortoba.sh \
    && chown -R odoo:odoo /mnt/extra-addons /etc/odoo/odoo.conf /var/lib/odoo

USER odoo
EXPOSE 8069

# Replaces the stock entrypoint so PORT (Render's HTTP port) is never mistaken
# for the Postgres port. See entrypoint.sh.
ENTRYPOINT ["/entrypoint-cortoba.sh"]
CMD ["odoo"]
