Example configuration and systemd service
=========================================

Install:

    groupadd -r custodia
    useradd -r -g custodia -d /var/lib/custodia -s /bin/false -c "Custodia" custodia

    cp tmpfiles.d/custodia.conf /etc/tmpfiles.d/
    systemd-tmpfiles --create

    install -d -m 750 -o custodia -g custodia /etc/custodia /var/log/custodia /var/lib/custodia
    cp custodia/custodia.conf /etc/custodia/
    cp systemd/system/custodia.* /etc/systemd/system/

    systemctl daemon-reload
    systemctl enable --now custodia.socket
