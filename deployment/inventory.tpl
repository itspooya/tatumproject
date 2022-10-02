all:
  children:
    dataserver:
      hosts: ${dataserver_ip}
      vars:
        ansible_user: ubuntu