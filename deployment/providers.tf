terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "4.38.0"
    }
  }
}
provider "google" {
    project = "project-id"
    region  = "us-central1"
    zone    = "us-central1-a"
    credentials = file("key.json")

}