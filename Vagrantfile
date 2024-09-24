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
    #dev.vm.box = "generic/ubuntu2004"
    dev.vm.box = "generic/debian11"
    dev.vm.hostname = "galaxy-dev"

    dev.vm.provider :libvirt do |libvirt|
      libvirt.cpus = 4
      libvirt.memory = 8000
      libvirt.machine_virtual_size = 20
    end

  end

  config.vm.define "galaxy-latest" do |latest|
    latest.vm.box = "generic/debian11"
    latest.vm.hostname = "galaxy-latest"
  end

  config.vm.define "galaxy-49" do |fournine|
    fournine.vm.box = "generic/debian11"
    fournine.vm.hostname = "galaxy-49"
  end

  config.vm.define "galaxy-48" do |foureight|
    foureight.vm.box = "generic/debian11"
    foureight.vm.hostname = "galaxy-48"
  end

  config.vm.define "galaxy-47" do |fourseven|
    fourseven.vm.box = "generic/debian11"
    fourseven.vm.hostname = "galaxy-47"
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
    libvirt.memory = 4000
  end

  config.vm.define "ghacktion" do |ghacktion|
    #ghacktion.vm.box = "generic/ubuntu2204"
    #ghacktion.vm.box = "generic/debian11"
    ghacktion.vm.box = "generic/debian12"
    ghacktion.vm.hostname = "ghacktion"

    ghacktion.vm.provider :libvirt do |libvirt|
      libvirt.cpus = 2
      libvirt.memory = 7000
      libvirt.machine_virtual_size = 20
    end

  end

  config.vm.provision "shell", inline: <<-SHELL
       export DEBIAN_FRONTEND=noninteractive
       apt -y update
       #apt -y upgrade
       apt -y install git jq python3-pip docker.io libpq-dev python3-virtualenv

       # python3 -m venv ~/venv.ansible
       virtualenv ~/venv.ansible
       source ~/venv.ansible/bin/activate

       # there should be a package for this right?
       if [ ! -L /usr/local/bin/python ]; then
         ln -s /usr/bin/python3 /usr/local/bin/python
       fi
       ~/venv.ansible/bin/pip3 install -U pip wheel
       which ansible || ~/venv.ansible/bin/pip3 install ansible
       ~/venv.ansible/bin/ansible-galaxy role install geerlingguy.docker
       cd /vagrant && ~/venv.ansible/bin/ansible-playbook -i 'localhost,' playbooks/docker.yml

       # install docker-compose
       curl -L -o /tmp/docker-compose https://github.com/docker/compose/releases/download/v2.29.1/docker-compose-linux-x86_64
       install /tmp/docker-compose /usr/local/bin/

       # pulp workarounds?
       mkdir -p /var/lib/gems
       chown -R vagrant:vagrant /var/lib/gems

       # for ghacktion
       if [[ $(hostname -s) == "ghacktion" ]]; then
         useradd --shell=/bin/bash runner
         cp -Rp /home/vagrant /home/runner
         chown -R runner:runner /home/runner
         usermod -aG docker runner
         usermod -aG docker vagrant
         cp /etc/sudoers.d/vagrant /etc/sudoers.d/runner
         sed -i.bak 's:vagrant:runner:g' /etc/sudoers.d/runner
         rm -f /etc/sudoers.d/runner.bak
       fi

  SHELL

end
