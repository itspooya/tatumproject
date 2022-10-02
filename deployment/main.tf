resource "tls_private_key" "pk" {
  algorithm = "RSA"
  rsa_bits = 4096
}
resource "local_sensitive_file" "pem_file" {
  filename = pathexpand("./sshkeys/key")
  file_permission = "600"
  directory_permission = "700"
  content = tls_private_key.pk.private_key_pem
}
resource "local_file" "pem_file_pub" {
  filename = pathexpand("./sshkeys/key.pub")
  file_permission = "644"
  directory_permission = "700"
  content = tls_private_key.pk.public_key_pem

}

resource "google_compute_instance" "data_server" {
    name = "data-server"
    zone = "us-central1-a"
    machine_type = "n1-standard-1"
    tags = ["data-server"]
    boot_disk {
        initialize_params {
            image = "ubuntu-os-cloud/ubuntu-2204-lts"
        }
    }
  scratch_disk {
    interface = "SCSI"
  }
  network_interface {
    network = "default"
    access_config {


    }

  }
    metadata = {
        ssh-keys = "ubuntu:${tls_private_key.pk.public_key_openssh}"
    }
}
resource "google_compute_firewall" "default" {

  name    = "webserver-firewall"
  network = "default"
  allow {
    protocol = "icmp"
  }
  allow {
    protocol = "tcp"
    ports    = ["22", "80", "443"]
  }
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["data-server"]
}
resource "random_password" "root_password" {
  special = false
  length = 16
}
# show ip address after instance is created
output "ip_address" {
  value = google_compute_instance.data_server.network_interface[0].access_config[0].nat_ip
}

# After the instance is created run ansible playbook
resource "null_resource" "null" {
  provisioner "local-exec" {
    command = "sleep 60; ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook --extra-vars 'root_password=${random_password.root_password.result}' -i ./ansible.yaml --private-key ./sshkeys/key ./ansible/main.yaml"
  }
  depends_on = [random_password.root_password]
}
# save the root password to a file
resource "local_file" "root_password" {
  filename = pathexpand("./sshkeys/root_password")
  file_permission = "600"
  directory_permission = "700"
  content = random_password.root_password.result
}
# copy key.json to the ansible folder
resource "local_file" "key_json" {
  filename = pathexpand("./ansible/key.json")
  file_permission = "600"
  directory_permission = "700"
  content = file("./key.json")
}