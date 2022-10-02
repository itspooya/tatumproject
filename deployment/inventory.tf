resource "local_file" "inventory-cfg" {
  content = templatefile("${path.module}/inventory.tpl",
    {
      dataserver_ip = google_compute_instance.data_server.network_interface[0].access_config[0].nat_ip
    }
  )
  filename = "./ansible.yaml"
}