FROM odoo:18.0

USER root
COPY odoo.conf /etc/odoo/odoo.conf
COPY addons/ /mnt/extra-addons/
RUN chown -R odoo:odoo /mnt/extra-addons /etc/odoo/odoo.conf /var/lib/odoo

USER odoo
EXPOSE 8069
