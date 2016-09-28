Example configuration and systemd service
=========================================

Install:

    mkdir -p --mode=750 /etc/custodia /var/log/custodia /var/lib/custodia /var/run/custodia
    cp custodia.conf /etc/custodia/
    cp custodia.service custodia.socket /usr/lib/systemd/system/

    systemctl daemon-reload
    systemctl start custodia.socket
