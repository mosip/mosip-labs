# mosip-labs: MinIO Report Tracker

This repository automates the extraction, transformation, and visualization of report metadata from MinIO buckets. It generates `.csv` and `.xlsx` reports with charts and commits them to the repository daily.

## What It Does

1. Fetches metadata from MinIO buckets using aliases such as `cellbox21`, `dev-int`.  
   Note: These aliases represent different environments.

2. Parses filenames to extract key values:
   - T (Total), P (Passed), S (Skipped), F (Failed), I (Ignored), KI (Known Issues)

3. Generates:
   - A `.csv` file containing the last 5 days of data per module.
   - A `.xlsx` report with two sheets:
     - Module Data: Tabular data
     - Module Graphs: Line charts for Total, Passed, and Failed

4. Commits updated reports to the `master` or `reporting` branch.

## Why Self-Hosted Runner with WireGuard?

Using a self-hosted GitHub Actions runner in combination with WireGuard provides:

- Full control over networking  
- Secure access to internal MinIO services  
- Compatibility with custom tools, VPNs, and service discovery  
- Scalable and fully customizable setup

## Setting Up Self-Hosted Runner

This section guides you through setting up a self-hosted GitHub Actions runner on a VM to automate MinIO report tracking.

### Step 1: Create a Virtual Machine (VM)

Use any cloud provider or local setup (Ubuntu preferred).

### Step 2: Install and Configure GitHub Runner

1. Go to your GitHub repository → Settings → Actions → Runners → New self-hosted runner

2. Follow the instructions shown on GitHub UI or use the steps below:

```bash
mkdir actions-runner && cd actions-runner

# Download the runner (update version as needed)
curl -o actions-runner-linux-x64.tar.gz -L https://github.com/actions/runner/releases/download/v2.X.X/actions-runner-linux-x64-2.X.X.tar.gz
tar xzf actions-runner-linux-x64-2.X.X.tar.gz

# Configure the runner (use repo URL and token from GitHub UI)
./config.sh --url https://github.com/<your-org>/<your-repo> --token <TOKEN>
```

### Step 3: Install Runner as a Service

```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

Enable on reboot:

```bash
sudo systemctl enable actions.runner.<your-repo>.service
```

## Configure MinIO Client (mc)

Install MinIO client:

```bash
curl -O https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/
```

Set aliases for environments:

```bash
mc alias set <env-name> https://<minio-host>:<port> <ACCESS_KEY> <SECRET_KEY> --api S3v2
```

Verify:

```bash
mc alias ls
```

Example output:

```
[env-name]
  URL       : https://minio.example.com:9000
  AccessKey : admin
  SecretKey : *****
  API       : S3v2
```

## Python Scripts

### scripts/update_csv.py

- Connects to defined MinIO aliases  
- Uses regex to parse filenames  
- Extracts metadata for latest two days  
- Saves `.csv` in the `csv/` folder

### scripts/generate_xlsx.py

- Reads all `.csv` files from the `csv/` folder  
- Creates `.xlsx` reports with:
  - Sheet 1: Tabular data
  - Sheet 2: Line chart for T, P, F  
- Saves `.xlsx` in the `xlxs/` folder

## Maintenance Instructions

### Add New Environment

1. Set alias:

```bash
mc alias set <env-name> https://<host>:<port> <user> <password> --api S3v2
```

2. Update this in `scripts/update_csv.py`:

```python
MINIO_ALIASES = ["env1", "env2", "new-env"]
```

### Remove Environment

1. Remove alias:

```bash
mc alias remove <env-name>
```

2. Remove it from `MINIO_ALIASES` list in `update_csv.py`.
