pipeline {
    agent any

    options {
        disableConcurrentBuilds()
    }

    environment {
        SEMGREP_APP_TOKEN         = credentials('SEMGREP_APP_TOKEN')
        // ── AWS / ECR ────────────────────────────────────────────────────
        AWS_REGION                = credentials('AWS_REGION')
        ECR_REGISTRY              = credentials('ECR_REGISTRY')
        AWS_ACCESS_KEY_ID         = credentials('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY     = credentials('AWS_SECRET_ACCESS_KEY')
        // ── EC2 target ───────────────────────────────────────────────────
        EC2_HOST                  = credentials('EC2_HOST')        
        EC2_SSH_KEY               = credentials('EC2_SSH_KEY')     
        // ── Image tag: Git short SHA for full traceability ───────────────
        IMAGE_TAG                 = "${env.GIT_COMMIT?.take(7) ?: 'latest'}"
    }

    stages {

        // ── 1. Source ────────────────────────────────────────────────────
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/heyyanu/ssdlc-cicd-pipeline.git'
            }
        }

        // ── 2. Tooling ───────────────────────────────────────────────────
        stage('Install Security Tools') {
            steps {
                sh '''
                    set -eu
                    mkdir -p .ci-tools/bin

                    echo "── Semgrep ──────────────────────────────────"
                    if [ ! -x .ci-tools/semgrep/bin/semgrep ]; then
                        python3 -m venv .ci-tools/semgrep
                        .ci-tools/semgrep/bin/python -m pip install --upgrade pip semgrep
                    fi

                    echo "── Checkov ──────────────────────────────────"
                    if [ ! -x .ci-tools/checkov/bin/checkov ]; then
                        python3 -m venv .ci-tools/checkov
                        .ci-tools/checkov/bin/python -m pip install --upgrade pip checkov
                    fi

                    echo "── pip-audit ─────────────────────────────────"
                    if [ ! -x .ci-tools/pip-audit/bin/pip-audit ]; then
                        python3 -m venv .ci-tools/pip-audit
                        .ci-tools/pip-audit/bin/python -m pip install --upgrade pip pip-audit
                    fi

                    echo "── Ansible + community.docker ───────────────"
                    if [ ! -x .ci-tools/ansible/bin/ansible ]; then
                        python3 -m venv .ci-tools/ansible
                        .ci-tools/ansible/bin/python -m pip install --upgrade pip ansible boto3
                        .ci-tools/ansible/bin/ansible-galaxy collection install community.docker
                    fi

                    .ci-tools/semgrep/bin/semgrep  --version
                    .ci-tools/checkov/bin/checkov  --version
                    .ci-tools/pip-audit/bin/pip-audit --version
                    .ci-tools/ansible/bin/ansible  --version

                    echo "── Node.js + cdxgen (SBOM / CycloneDX) ─────"
                    if ! command -v node >/dev/null 2>&1; then
                        echo "Installing Node.js 20..."
                        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
                        apt-get install -y nodejs
                    fi

                    if ! command -v cdxgen >/dev/null 2>&1; then
                        echo "Installing cdxgen..."
                        npm install -g @cyclonedx/cdxgen
                    fi

                    node --version
                    cdxgen --version

                    echo "Security tools ready!"
                '''
            }
        }

        // ── 3. Build (Python) ────────────────────────────────────────────
        stage('Build') {
            steps {
                sh '''
                    set -eu
                    if [ ! -x .venv/bin/python ]; then
                        python3 -m venv .venv
                    fi
                    .venv/bin/python -m pip install --upgrade pip
                    .venv/bin/python -m pip install -r requirements.txt
                    .venv/bin/python -m py_compile app.py
                    echo "Build successful!"
                '''
            }
        }

        // ── 4. Unit tests ────────────────────────────────────────────────
        stage('Test') {
            steps {
                sh '''
                    set -eu
                    .venv/bin/python -m pytest test_app.py -v
                '''
            }
        }

        // ── 5. SAST — Bandit ─────────────────────────────────────────────
        stage('SAST - Bandit') {
            steps {
                sh '''
                    set -eu
                    .venv/bin/python -m bandit \
                        -r . \
                        -ll \
                        --exclude ./.venv,./.ci-tools,./ansible
                '''
            }
        }

        // ── 6. SAST — Semgrep ────────────────────────────────────────────
        stage('Semgrep') {
            steps {
                sh '''
                    set -eu
                    .ci-tools/semgrep/bin/semgrep ci --no-suppress-errors
                    echo "Semgrep scan completed!"
                '''
            }
        }

        // ── 7. Secret scan — Gitleaks ────────────────────────────────────
        stage('Secret Scan - Gitleaks') {
            steps {
                sh '''
                    set -eu
                    VERSION="8.30.1"
                    ARCH="$(uname -m)"
                    case "$ARCH" in
                        x86_64)        GITLEAKS_ARCH="x64"   ;;
                        aarch64|arm64) GITLEAKS_ARCH="arm64" ;;
                        *)             echo "Unsupported arch: $ARCH"; exit 1 ;;
                    esac

                    TMP_DIR="$(mktemp -d)"
                    trap \'rm -rf "$TMP_DIR"\' EXIT

                    curl -fsSL \
                        "https://github.com/gitleaks/gitleaks/releases/download/v${VERSION}/gitleaks_${VERSION}_linux_${GITLEAKS_ARCH}.tar.gz" \
                        -o "$TMP_DIR/gitleaks.tar.gz"
                    tar -xzf "$TMP_DIR/gitleaks.tar.gz" -C "$TMP_DIR" gitleaks
                    install -m 0755 "$TMP_DIR/gitleaks" .ci-tools/bin/gitleaks

                    .ci-tools/bin/gitleaks git --verbose .
                    echo "Gitleaks scan completed!"
                '''
            }
        }

        // ── 8. SCA — pip-audit ───────────────────────────────────────────
        stage('SCA - Dependency Check') {
            steps {
                sh '''
                    set -eu
                    .ci-tools/pip-audit/bin/pip-audit -r requirements.txt
                    echo "Dependency audit completed!"
                '''
            }
        }

        // ── 9. SBOM — CycloneDX via cdxgen ──────────────────────────────
        stage('SBOM - CycloneDX') {
            steps {
                sh '''
                    set -eu

                    echo "Generating CycloneDX SBOM..."
                    mkdir -p sbom-output

                    cdxgen \
                        --type python \
                        --output sbom-output/sbom.json \
                        --format json \
                        .

                    echo "── SBOM summary ─────────────────────────────"
                    python3 - <<'PYEOF'
import json, sys
with open("sbom-output/sbom.json") as f:
    bom = json.load(f)
components = bom.get("components", [])
print(f"  Components : {len(components)}")
for c in components:
    name    = c.get("name", "?")
    version = c.get("version", "?")
    purl    = c.get("purl", "")
    print(f"  {name}=={version}  ({purl})")
PYEOF

                    echo "SBOM generation completed!"
                '''

                archiveArtifacts artifacts: 'sbom-output/sbom.json',
                                 fingerprint: true
            }
        }

        // ── 10. IaC scan — Checkov (Ansible + Dockerfile, NOT Terraform) ─
        stage('IaC Scan - Checkov') {
            steps {
                sh '''
                    set -eu
                    echo "Scanning Ansible playbooks and Dockerfile..."
                    .ci-tools/checkov/bin/checkov \
                        -d . \
                        --framework ansible dockerfile \
                        --skip-path .ci-tools \
                        --skip-path .venv
                    echo "IaC scan completed!"
                '''
            }
        }

        // ── 10. Build Docker image ────────────────────────────────────────
        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu
                    docker version
                    docker build -t "ssdlc-app:${IMAGE_TAG}" .
                    docker tag  "ssdlc-app:${IMAGE_TAG}" ssdlc-app:latest
                    echo "Docker image built: ssdlc-app:${IMAGE_TAG}"
                '''
            }
        }

        // ── 11. Push to ECR ──────────────────────────────────────────────
        stage('Push to ECR') {
            steps {
                sh '''
                    set -eu
                    aws ecr get-login-password --region "${AWS_REGION}" \
                        | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

                    docker tag "ssdlc-app:${IMAGE_TAG}" "${ECR_REGISTRY}/ssdlc-app:${IMAGE_TAG}"
                    docker tag  ssdlc-app:latest        "${ECR_REGISTRY}/ssdlc-app:latest"

                    docker push "${ECR_REGISTRY}/ssdlc-app:${IMAGE_TAG}"
                    docker push "${ECR_REGISTRY}/ssdlc-app:latest"

                    echo "Pushed: ${ECR_REGISTRY}/ssdlc-app:${IMAGE_TAG}"
                '''
            }
        }

        // ── 12. Deploy to Staging — Ansible (replaces Terraform stage) ───
        stage('Deploy to Staging - Ansible') {
            steps {
                dir('ansible') {
                    sh '''
                        set -eu

                        # Write the EC2 SSH private key to a secure temp file
                        KEY_FILE="$(mktemp)"
                        trap \'rm -f "$KEY_FILE"\' EXIT
                        printf \'%s\' "${EC2_SSH_KEY}" > "$KEY_FILE"
                        chmod 600 "$KEY_FILE"

                        # Dynamically generate the inventory with the real EC2 host
                        cat > inventory/staging.ini <<INI
[staging]
staging-host ansible_host=${EC2_HOST} ansible_user=ec2-user

[staging:vars]
ansible_ssh_common_args=\'-o StrictHostKeyChecking=no\'
INI

                        echo "Running Ansible deploy playbook..."
                        ../.ci-tools/ansible/bin/ansible-playbook deploy.yml \
                            --private-key "$KEY_FILE" \
                            --extra-vars "ecr_registry=${ECR_REGISTRY} aws_region=${AWS_REGION} image_tag=${IMAGE_TAG}" \
                            -v

                        echo "Staging deployment completed!"
                    '''
                }
            }
        }

        // ── 13. DAST — OWASP ZAP ─────────────────────────────────────────
        stage('DAST - OWASP ZAP') {
            steps {
                sh '''
                    set -eu
                    TARGET="http://${EC2_HOST}:8081"

                    echo "Waiting for staging app at ${TARGET}..."
                    READY="false"
                    for ATTEMPT in $(seq 1 30); do
                        if curl -fsS "${TARGET}/" >/dev/null 2>&1; then
                            READY="true"
                            break
                        fi
                        echo "  attempt ${ATTEMPT}/30 — waiting 2s..."
                        sleep 2
                    done

                    if [ "$READY" != "true" ]; then
                        echo "Staging app not reachable at ${TARGET}!"
                        exit 1
                    fi

                    echo "Starting OWASP ZAP baseline scan..."
                    docker run --rm \
                        ghcr.io/zaproxy/zaproxy:stable \
                        zap-baseline.py \
                        -t "${TARGET}" \
                        -I

                    echo "DAST scan completed!"
                '''
            }
        }

        // ── 14. Deploy to Production (manual gate) ───────────────────────
        stage('Deploy to Production') {
            steps {
                input message: 'Deploy to Production?',
                      ok: 'Yes, Deploy!'

                sh '''
                    set -eu
                    aws ecr get-login-password --region "${AWS_REGION}" \
                        | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

                    # Re-tag the same image digest as :production in ECR
                    MANIFEST=$(aws ecr batch-get-image \
                        --repository-name ssdlc-app \
                        --image-ids imageTag="${IMAGE_TAG}" \
                        --region "${AWS_REGION}" \
                        --query "images[0].imageManifest" \
                        --output text)

                    aws ecr put-image \
                        --repository-name ssdlc-app \
                        --image-tag production \
                        --image-manifest "$MANIFEST" \
                        --region "${AWS_REGION}"

                    echo "Production image tagged: ${ECR_REGISTRY}/ssdlc-app:production"
                '''
            }
        }
    }

    post {
        success { echo 'Pipeline completed successfully!' }
        failure { echo 'Pipeline failed! Check the console output.' }
    }
}