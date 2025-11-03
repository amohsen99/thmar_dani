### connect to server
ssh user@serverip
```
ssh root@72.61.186.1
```

### copy

**Syntax:**

```bash
scp /path/to/local/file username@server_ip:/path/to/remote/directory
```

**Example:**

```bash
scp ~/Downloads/project.zip root@http://72.61.186.1/:/root/odoo19
```

**To copy a whole folder:**

```bash
scp -r ~/Documents/my_project ubuntu@192.168.1.10:/home/ubuntu/
```

✅ *Works if you can SSH into your server (e.g. `ssh ubuntu@192.168.1.10`)*

---



