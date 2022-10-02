all:
  vars:
    ansible_user: root
    resolveconf_server: 1.1.1.1
  children:
    wireguard:
        hosts: ${dataserver_ip}

        vars:
          ansible_user: ubuntu