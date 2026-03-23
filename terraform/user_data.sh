#!/bin/bash
dnf update -y
dnf install nginx -y
systemctl enable nginx
systemctl start nginx