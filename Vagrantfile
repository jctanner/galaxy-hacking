# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure("2") do |config|
  #config.vm.box = "generic/fedora34"
  config.vm.synced_folder ".", "/vagrant", type: "nfs", nfs_udp: false

  config.vm.define "galaxy-dev" do |dev|
    dev.vm.box = "generic/ubuntu2004"
    dev.vm.hostname = "galaxy-dev"
  end

  config.vm.define "galaxy-latest" do |latest|
    latest.vm.box = "generic/ubuntu2004"
    latest.vm.hostname = "galaxy-latest"
  end

  config.vm.define "galaxy-45" do |fourfive|
    fourfive.vm.box = "generic/ubuntu2004"
    fourfive.vm.hostname = "galaxy-45"
  end

  config.vm.define "galaxy-44" do |fourfour|
    fourfour.vm.box = "generic/ubuntu2004"
    fourfour.vm.hostname = "galaxy-44"
  end

  config.vm.define "galaxy-43" do |fourthree|
    fourthree.vm.box = "generic/ubuntu2004"
    fourthree.vm.hostname = "galaxy-43"
  end

  config.vm.define "galaxy-42" do |fourtwo|
    fourtwo.vm.box = "generic/ubuntu2004"
    fourtwo.vm.hostname = "galaxy-42"
  end

  config.vm.provider :libvirt do |libvirt|
    libvirt.cpus = 2
    libvirt.memory = 8000
  end

  config.vm.provision "shell", inline: <<-SHELL
     export DEBIAN_FRONTEND=noninteractive
     apt -y update
     apt -y upgrade
     apt -y install git jq python3-pip docker.io libpq-dev python3-virtualenv

     # there should be a package for this right?
     if [ ! -L /usr/local/bin/python ]; then
       ln -s /usr/bin/python3 /usr/local/bin/python
     fi
     pip3 install -U pip wheel
     which ansible || pip3 install ansible
     ansible-galaxy role install geerlingguy.docker
     cd /vagrant && ansible-playbook -i 'localhost,' docker.yml

     # pulp workarounds?
     mkdir -p /var/lib/gems
     chown -R vagrant:vagrant /var/lib/gems

  SHELL

end
