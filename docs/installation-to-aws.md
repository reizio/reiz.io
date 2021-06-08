# Demo mode installation to an AWS machine

## Requirements

- AWS account
- SSH client
- Browser (firefox/chrome)

## Instance

- Image: `Ubuntu Server 18.04 LTS (HVM), SSD Volume Type`
- Type: `t2.large` (2 vCPU, 8GB ram)
- Storage: 30 GB

## Install Docker / Docker-Compose

Find the instance IP address and then login the instance via SSH (with
forwarding the `8000` port);

```
$ ssh -L 8000:localhost:8000 ubuntu@<ip addr> -i <identity file>
Welcome to Ubuntu 18.04.5 LTS (GNU/Linux 5.4.0-1045-aws x86_64)

  System information as of Tue Jun  8 17:14:49 UTC 2021

  System load:  0.23              Processes:           117
  Usage of /:   3.9% of 29.02GB   Users logged in:     0
  Memory usage: 2%                IP address for eth0: 172.31.9.52
  Swap usage:   0%

ubuntu@ip-172-31-9-52:~$ 
```

After the login, go and install docker.

```
$ sudo apt update
$ sudo apt install apt-transport-https ca-certificates curl software-properties-common
$ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
$ sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
$ sudo apt update
$ sudo apt install docker-ce
```

Add your user to the `docker` group to not to use `sudo` for every command

```
$ sudo groupadd docker
$ sudo usermod -aG docker $USER
$ newgrp docker
$ docker --version
Docker version 20.10.7, build f0df350
```

Ensure that you use either the same or a newer version. Then install
docker-compose

```
$ sudo curl -L https://github.com/docker/compose/releases/download/1.29.2/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
$ sudo chmod +x /usr/local/bin/docker-compose
$ docker-compose --version
docker-compose version 1.29.2, build 5becea4c
```

## Install Reiz

For installing reiz, you only need `git` and `docker-compose`.

Clone and ensure that you have the latest revision;

```
$ git clone https://github.com/reizio/reiz.io
$ cd reiz.io/
~/reiz.io$ git fetch origin
~/reiz.io$ git reset --hard origin/master
```

And finally start the reiz

```
$ docker-compose up
```

In case of you are interested, here are the
[full logs](https://gist.github.com/isidentical/bf6b4e2dbdd60407a4b51d6fbfc8e28a).
You should pretty much get the similiar stuff. After getting these lines;

```
reiz_1    | [2021-06-08 17:29:34,186] insert_file     --- 'pip/tests/lib/certs.py' has been inserted successfully
reiz_1    | [2021-06-08 17:29:37,175] insert_file     --- 'pip/tests/lib/local_repos.py' has been inserted successfully
reiz_1    | [2021-06-08 17:29:40,128] insert_file     --- 'pip/tests/lib/configuration_helpers.py' has been inserted successfully
reiz_1    | + python -m reiz.web.api
reiz_1    | [2021-06-08 17:29:40 +0000] [151] [INFO] Goin' Fast @ http://0.0.0.0:8000
reiz_1    | [2021-06-08 17:29:40,944] _helper         --- Goin' Fast @ http://0.0.0.0:8000
reiz_1    | [2021-06-08 17:29:41 +0000] [151] [INFO] Starting worker [151]
reiz_1    | [2021-06-08 17:29:41,226] serve           --- Starting worker [151]
```

You can go to the `localhost:8000` on your browser and be greeted by the web
page;

![image](https://user-images.githubusercontent.com/47358913/121231015-911b4600-c898-11eb-9c99-5d46efb4d356.png)

After that you could either click on one of pre-selected queries or write your
own;

![image](https://user-images.githubusercontent.com/47358913/121231095-a98b6080-c898-11eb-9fcd-d250ae44ad5f.png)

If you want to see the size of dataset, you could go to the
`localhost:8000/stats`. Mine for example indexes 10k nodes;

```
{
    "status": "success",
    "results": {
        "Module": 91,
        "AST": 10785,
        "stmt": 2204,
        "expr": 8426
    },
    "exception": null
}
```

Every time you do `docker-compose up`, it will index more files from the 10
projects it downloaded (~75, +/- 20).
