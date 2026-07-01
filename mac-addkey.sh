#!/bin/bash
set -e
mkdir -p ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFpM3oq/X0S1r4okwNK/JHmZ/d0Ee4n6cqf+oKI25diJ root@136587.ip-ns.net" >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
echo "✅ Server key added to authorized_keys"
