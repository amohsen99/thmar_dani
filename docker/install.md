Here’s the **correct and up-to-date** way (as of 2025) to install **Docker Engine** and **Docker Compose** on **Ubuntu 22.04 or newer**.

---

### 🧩 Step 1: Uninstall old versions (optional)

```bash
sudo apt remove docker docker-engine docker.io containerd runc
```

---

### 🧩 Step 2: Update system packages

```bash
sudo apt update
sudo apt upgrade -y
```

---

### 🧩 Step 3: Install required dependencies

```bash
sudo apt install ca-certificates curl gnupg lsb-release -y
```

---

### 🧩 Step 4: Add Docker’s official GPG key

```bash
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
```

---

### 🧩 Step 5: Add Docker repository

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

---

### 🧩 Step 6: Install Docker Engine and CLI

```bash
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
```

---

### 🧩 Step 7: Verify installation

Check Docker version:

```bash
docker --version
```

Check Docker Compose (it’s now a plugin):

```bash
docker compose version
```

Run a test container:

```bash
sudo docker run hello-world
```

---

### 🧩 Step 8: (Optional) Run Docker without `sudo`

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Then test:

```bash
docker ps
```

---

✅ **Done!**
Now you have **Docker Engine + Compose plugin** installed and ready to use on Ubuntu.

---

Would you like me to show how to install the **standalone `docker-compose` binary** (the old method) too, in case your project depends on it?
