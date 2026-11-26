pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 60, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/heyyanu/ssdlc-cicd-pipeline.git'
                script {
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse --short=7 HEAD',
                        returnStdout: true
                    ).trim()
                    echo "Building image tag: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('Install Security Tools') {
            steps {
                sh '''
                    set -eu
                    mkdir -p .ci-tools/bin

                    if [ ! -x .ci-tools/semgrep/bin/semgrep ]; then
                        python3 -m venv .ci-tools/semgrep
                        .ci-tools/semgrep/bin/python -m pip install --upgrade pip
                        .ci-tools/semgrep/bin/python -m pip install semgrep==1.184.0
                    fi

                    if [ ! -x .ci-tools/checkov/bin/checkov ]; then
                        python3 -m venv .ci-tools/checkov
                        .ci-tools/checkov/bin/python -m pip install --upgrade pip
                        .ci-tools/checkov/bin/python -m pip install checkov==3.4.3
                    fi

                    if [ ! -x .ci-tools/pip-audit/bin/pip-audit ]; then
                        python3 -m venv .ci-tools/pip-audit
                        .ci-tools/pip-audit/bin/python -m pip install --upgrade pip
                        .ci-tools/pip-audit/bin/python -m pip install pip-audit==2.10.1
                    fi

                    if [ ! -x .ci-tools/ansible/bin/ansible ]; then
                        python3 -m venv .ci-tools/ansible
                        .ci-tools/ansible/bin/python -m pip install --upgrade pip
                        .ci-tools/ansible/bin/python -m pip install ansible-core==2.22.0
                    fi

                    # Workspace-local AWS CLI v2. Python ZIP extraction does not
                    # preserve Unix executable bits, so restore those from ZIP metadata.
                    if [ ! -x .ci-tools/bin/aws ]; then
                        ARCH="$(uname -m)"
                        case "$ARCH" in
                            x86_64|amd64) AWSCLI_ARCH="x86_64" ;;
                            aarch64|arm64) AWSCLI_ARCH="aarch64" ;;
                            *) echo "Unsupported AWS CLI architecture: $ARCH" >&2; exit 1 ;;
                        esac
                        TMP_DIR="$(mktemp -d)"
                        trap 'rm -rf "$TMP_DIR"' EXIT
                        curl -fsSL \
                            "https://awscli.amazonaws.com/awscli-exe-linux-${AWSCLI_ARCH}.zip" \
                            -o "$TMP_DIR/awscliv2.zip"
                        python3 -m zipfile -e "$TMP_DIR/awscliv2.zip" "$TMP_DIR"
                        python3 - "$TMP_DIR/awscliv2.zip" "$TMP_DIR" <<'PYEOF'
import os
import pathlib
import sys
import zipfile
archive_path, extract_root = sys.argv[1:]
root = pathlib.Path(extract_root)
with zipfile.ZipFile(archive_path) as archive:
    for entry in archive.infolist():
        mode = (entry.external_attr >> 16) & 0o777
        target = root / entry.filename
        if not entry.is_dir() and mode & 0o111 and target.is_file():
            os.chmod(target, mode)
PYEOF
                        chmod 0755 "$TMP_DIR/aws/install" "$TMP_DIR/aws/dist/aws"
                        if [ -f "$TMP_DIR/aws/dist/aws_completer" ]; then
                            chmod 0755 "$TMP_DIR/aws/dist/aws_completer"
                        fi
                        "$TMP_DIR/aws/install" \
                            --install-dir "$PWD/.ci-tools/aws-cli" \
                            --bin-dir "$PWD/.ci-tools/bin"
                        rm -rf "$TMP_DIR"
                        trap - EXIT
                    fi

                    # Standalone cdxgen binary, pinned and checksum-verified.
                    if [ ! -x .ci-tools/bin/cdxgen ]; then
                        ARCH="$(uname -m)"
                        case "$ARCH" in
                            x86_64|amd64) CDXGEN_ASSET="cdxgen-linux-amd64" ;;
                            *) echo "Unsupported cdxgen architecture: $ARCH" >&2; exit 1 ;;
                        esac
                        CDXGEN_VERSION="v13.8.0"
                        CDXGEN_BASE="https://github.com/cdxgen/cdxgen/releases/download/${CDXGEN_VERSION}"
                        TMP_DIR="$(mktemp -d)"
                        trap 'rm -rf "$TMP_DIR"' EXIT
                        curl -fsSL "${CDXGEN_BASE}/${CDXGEN_ASSET}" -o "$TMP_DIR/${CDXGEN_ASSET}"
                        curl -fsSL "${CDXGEN_BASE}/${CDXGEN_ASSET}.sha256" -o "$TMP_DIR/${CDXGEN_ASSET}.sha256"
                        (cd "$TMP_DIR" && sha256sum -c "${CDXGEN_ASSET}.sha256")
                        install -m 0755 "$TMP_DIR/${CDXGEN_ASSET}" .ci-tools/bin/cdxgen
                        rm -rf "$TMP_DIR"
                        trap - EXIT
                    fi

                    .ci-tools/semgrep/bin/semgrep --version
                    .ci-tools/checkov/bin/checkov --version
                    .ci-tools/pip-audit/bin/pip-audit --version
                    .ci-tools/ansible/bin/ansible --version
                    .ci-tools/bin/aws --version
                    .ci-tools/bin/cdxgen --version
                    echo "Security tools ready!"
                '''
            }
        }

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

        stage('Test') {
            steps {
                sh '''
                    set -eu
                    .venv/bin/python -m pytest test_app.py -v
                '''
            }
        }

        stage('SAST - Bandit') {
            steps {
                sh '''
                    set -eu
                    .venv/bin/python -m bandit -r . -ll \
                        --exclude ./.venv,./.ci-tools,./ansible,./sbom-output
                '''
            }
        }

        stage('Semgrep') {
            steps {
                withCredentials([
                    string(credentialsId: 'SEMGREP_APP_TOKEN', variable: 'SEMGREP_APP_TOKEN')
                ]) {
                    sh '''
                        set -eu
                        set +x
                        .ci-tools/semgrep/bin/semgrep ci --no-suppress-errors
                        echo "Semgrep scan completed!"
                    '''
                }
            }
        }

        stage('Secret Scan - Gitleaks') {
            steps {
                sh '''
                    set -eu
                    VERSION="8.30.1"
                    ARCH="$(uname -m)"
                    case "$ARCH" in
                        x86_64) GITLEAKS_ARCH="x64" ;;
                        aarch64|arm64) GITLEAKS_ARCH="arm64" ;;
                        *) echo "Unsupported Gitleaks architecture: $ARCH" >&2; exit 1 ;;
                    esac
                    ASSET="gitleaks_${VERSION}_linux_${GITLEAKS_ARCH}.tar.gz"
                    BASE="https://github.com/gitleaks/gitleaks/releases/download/v${VERSION}"
                    TMP_DIR="$(mktemp -d)"
                    trap 'rm -rf "$TMP_DIR"' EXIT
                    curl -fsSL "${BASE}/${ASSET}" -o "$TMP_DIR/${ASSET}"
                    curl -fsSL "${BASE}/gitleaks_${VERSION}_checksums.txt" -o "$TMP_DIR/checksums.txt"
                    (cd "$TMP_DIR" && grep -F "${ASSET}" checksums.txt | sha256sum --check --status)
                    tar -xzf "$TMP_DIR/${ASSET}" -C "$TMP_DIR" gitleaks
                    install -m 0755 "$TMP_DIR/gitleaks" .ci-tools/bin/gitleaks
                    .ci-tools/bin/gitleaks git --verbose .
                    echo "Gitleaks scan completed!"
                '''
            }
        }

        stage('SCA - Dependency Check') {
            steps {
                sh '''
                    set -eu
                    .ci-tools/pip-audit/bin/pip-audit -r requirements.txt
                    echo "Dependency audit completed!"
                '''
            }
        }

        stage('SBOM - CycloneDX') {
            steps {
                sh '''
                    set -eu
                    mkdir -p sbom-output
                    .ci-tools/bin/cdxgen \
                        --type python \
                        --no-install-deps \
                        --no-include-formulation \
                        --exclude '**/.ci-tools/**' \
                        --exclude '**/.venv/**' \
                        --exclude '**/ansible/**' \
                        --exclude '**/sbom-output/**' \
                        --output "$PWD/sbom-output/sbom.json" \
                        "$PWD"
                    python3 - <<'PYEOF'
import json
from pathlib import Path
bom_path = Path('sbom-output/sbom.json')
with bom_path.open(encoding='utf-8') as handle:
    bom = json.load(handle)
components = bom.get('components', [])
print(f"CycloneDX components: {len(components)}")
for component in components:
    print(f"  {component.get('name', '?')}=={component.get('version', '?')}")
PYEOF
                    echo "SBOM generation completed!"
                '''
                archiveArtifacts artifacts: 'sbom-output/sbom.json', fingerprint: true
            }
        }

        stage('IaC Scan - Checkov') {
            steps {
                sh '''
                    set -eu
                    .ci-tools/checkov/bin/checkov \
                        -d . \
                        --framework ansible dockerfile \
                        --skip-path .ci-tools \
                        --skip-path .venv
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu
                    docker version
                    docker build --pull -t "ssdlc-app:${IMAGE_TAG}" .
                    docker tag "ssdlc-app:${IMAGE_TAG}" ssdlc-app:latest
                    echo "Docker image built: ssdlc-app:${IMAGE_TAG}"
                '''
            }
        }

        stage('ECR Network Diagnostics') {
            steps {
                withCredentials([
                    string(credentialsId: 'AWS_REGION', variable: 'AWS_REGION'),
                    string(credentialsId: 'ECR_REGISTRY', variable: 'ECR_REGISTRY')
                ]) {
                    sh '''
                        set -eu
                        set +x
                        case "$ECR_REGISTRY" in
                            *://*|*/*) echo "ECR_REGISTRY must be a registry hostname only" >&2; exit 1 ;;
                        esac
                        echo "Checking ECR HTTPS endpoint..."
                        HTTP_STATUS="$(curl -sS --connect-timeout 10 --max-time 20 \
                            -o /dev/null -w '%{http_code}' "https://${ECR_REGISTRY}/v2/")"
                        echo "ECR unauthenticated /v2 response: ${HTTP_STATUS} (401 is expected)"
                        [ "$HTTP_STATUS" = "401" ] || {
                            echo "Unexpected ECR response; check registry, DNS and network." >&2
                            exit 1
                        }
                        docker info --format 'Docker proxy: HTTP={{.HTTPProxy}} HTTPS={{.HTTPSProxy}} NO_PROXY={{.NoProxy}}'
                        docker context show
                    '''
                }
            }
        }

        stage('Push to ECR') {
            steps {
                withCredentials([
                    string(credentialsId: 'AWS_REGION', variable: 'AWS_REGION'),
                    string(credentialsId: 'ECR_REGISTRY', variable: 'ECR_REGISTRY'),
                    string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh '''
                        set -eu
                        set +x
                        DOCKER_CONFIG="$(mktemp -d)"
                        export DOCKER_CONFIG
                        trap 'rm -rf "$DOCKER_CONFIG"' EXIT
                        .ci-tools/bin/aws ecr get-login-password --region "$AWS_REGION" \
                            | docker login --username AWS --password-stdin "$ECR_REGISTRY"
                        docker tag "ssdlc-app:${IMAGE_TAG}" "${ECR_REGISTRY}/ssdlc-app:${IMAGE_TAG}"
                        docker tag ssdlc-app:latest "${ECR_REGISTRY}/ssdlc-app:latest"
                        docker push "${ECR_REGISTRY}/ssdlc-app:${IMAGE_TAG}"
                        docker push "${ECR_REGISTRY}/ssdlc-app:latest"
                        echo "Pushed image tag ${IMAGE_TAG} to ECR."
                    '''
                }
            }
        }

        stage('Deploy to Staging - Ansible') {
            steps {
                withCredentials([
                    string(credentialsId: 'AWS_REGION', variable: 'AWS_REGION'),
                    string(credentialsId: 'ECR_REGISTRY', variable: 'ECR_REGISTRY'),
                    string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY'),
                    string(credentialsId: 'EC2_HOST', variable: 'EC2_HOST'),
                    sshUserPrivateKey(
                        credentialsId: 'EC2_SSH_PRIVATE_KEY',
                        keyFileVariable: 'EC2_SSH_KEY_FILE',
                        usernameVariable: 'EC2_SSH_USER'
                    )
                ]) {
                    dir('ansible') {
                        sh '''
                            set -eu
                            set +x
                            test -s "$EC2_SSH_KEY_FILE"
                            ssh-keygen -y -f "$EC2_SSH_KEY_FILE" >/dev/null

                            ECR_PASSWORD_FILE="$(mktemp)"
                            trap 'rm -f "$ECR_PASSWORD_FILE"' EXIT
                            chmod 600 "$ECR_PASSWORD_FILE"
                            ../.ci-tools/bin/aws ecr get-login-password \
                                --region "$AWS_REGION" > "$ECR_PASSWORD_FILE"
                            test -s "$ECR_PASSWORD_FILE"

                            mkdir -p inventory
                            cat > inventory/staging.ini <<INI
[staging]
staging-host ansible_host=${EC2_HOST} ansible_user=${EC2_SSH_USER}

[staging:vars]
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
INI

                            echo "Testing EC2 SSH connection..."
                            ../.ci-tools/ansible/bin/ansible \
                                staging -i inventory/staging.ini -m ping \
                                --private-key "$EC2_SSH_KEY_FILE"

                            echo "Running Ansible deployment..."
                            ../.ci-tools/ansible/bin/ansible-playbook \
                                deploy.yml \
                                -i inventory/staging.ini \
                                --private-key "$EC2_SSH_KEY_FILE" \
                                --extra-vars "ecr_registry=${ECR_REGISTRY} aws_region=${AWS_REGION} image_tag=${IMAGE_TAG} ecr_password_file=${ECR_PASSWORD_FILE}" \
                                -v
                        '''
                    }
                }
            }
        }

        // Compliance scan runs in the official Cinc Auditor container.
        // This avoids extracting a Debian package into a workspace and then
        // relying on a relocated executable with broken embedded paths.
        stage('Compliance - Cinc Auditor') {
            steps {
                withCredentials([
                    string(credentialsId: 'EC2_HOST', variable: 'EC2_HOST'),
                    sshUserPrivateKey(
                        credentialsId: 'EC2_SSH_PRIVATE_KEY',
                        keyFileVariable: 'EC2_SSH_KEY_FILE',
                        usernameVariable: 'EC2_SSH_USER'
                    )
                ]) {
                    sh '''
                        set -eu
                        set +x

                        : "${EC2_HOST:?EC2_HOST credential is empty}"
                        : "${EC2_SSH_USER:?EC2_SSH_USER credential is empty}"
                        test -s "$EC2_SSH_KEY_FILE"
                        ssh-keygen -y -f "$EC2_SSH_KEY_FILE" >/dev/null

                        case "$EC2_HOST" in
                            *://*|*/*|*' '*)
                                echo "EC2_HOST must contain only an IP address or hostname, without a scheme or path." >&2
                                exit 1
                                ;;
                        esac

                        CINC_IMAGE="cincproject/auditor:7.3.4"
                        CINC_CONTAINER="cinc-auditor-${BUILD_NUMBER:-0}-$$"
                        mkdir -p inspec-profile/controls inspec-output

                        cleanup_cinc() {
                            docker rm -f "$CINC_CONTAINER" >/dev/null 2>&1 || true
                            rm -f inspec-ssh-config
                        }
                        trap cleanup_cinc EXIT

                        echo "Pulling official Cinc Auditor image: ${CINC_IMAGE}"
                        docker pull "$CINC_IMAGE"

                        # Create an ephemeral container. docker cp is used instead
                        # of bind mounts because the Docker daemon may run outside
                        # the Jenkins container and may not see its workspace path.
                        docker run -d \\
                            --name "$CINC_CONTAINER" \\
                            --entrypoint /bin/bash \\
                            "$CINC_IMAGE" \\
                            -lc 'while :; do sleep 3600; done' >/dev/null

                        cat > inspec-profile/inspec.yml << 'PROFILEEOF'
name: ssdlc-staging-baseline
title: SSDLC Staging Compliance Baseline
maintainer: SSDLC Pipeline
version: 1.0.0
supports:
  - platform: linux
PROFILEEOF

                        cat > inspec-profile/controls/docker.rb << 'RUBYEOF'
# Control 1: Docker service must be running
control 'docker-service-running' do
  impact 1.0
  title 'Docker service is running'
  desc 'Docker must be active and running to serve the application container.'
  describe service('docker') do
    it { should be_running }
    it { should be_enabled }
  end
end

# Control 2: App container must be running
control 'app-container-running' do
  impact 1.0
  title 'Staging app container is running'
  desc 'The ssdlc-app staging container must be in a running state.'
  describe command('docker inspect -f {{.State.Running}} staging-app') do
    its('stdout.strip') { should eq 'true' }
    its('exit_status') { should eq 0 }
  end
end

# Control 3: Container must run as non-root
control 'container-non-root-user' do
  impact 1.0
  title 'Container runs as non-root user'
  desc 'The app container must not run as UID 0 (root).'
  describe command("docker inspect -f '{{.Config.User}}' staging-app") do
    its('stdout.strip') { should_not eq '' }
    its('stdout.strip') { should_not eq '0' }
    its('stdout.strip') { should_not eq 'root' }
  end
end

# Control 4: SSH password authentication must be disabled
control 'ssh-password-auth-disabled' do
  impact 0.7
  title 'SSH password authentication is disabled'
  desc 'Only key-based SSH authentication is permitted on the staging host.'
  describe sshd_config do
    its('PasswordAuthentication') { should eq 'no' }
  end
end

# Control 5: Container port must be listening
control 'app-port-listening' do
  impact 1.0
  title 'Application port 8081 is listening'
  desc 'The staging app must be reachable on port 8081.'
  describe port(8081) do
    it { should be_listening }
  end
end
RUBYEOF

                        # InSpec/Train reads the container's SSH config. This
                        # retains the same host-key-checking behavior as the
                        # existing Ansible staging inventory.
                        cat > inspec-ssh-config << 'SSHEOF'
Host *
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    IdentitiesOnly yes
    LogLevel ERROR
SSHEOF

                        docker exec "$CINC_CONTAINER" mkdir -p \\
                            /work /work/inspec-output /root/.ssh
                        docker cp inspec-profile "$CINC_CONTAINER:/work/"
                        docker cp inspec-ssh-config "$CINC_CONTAINER:/root/.ssh/config"
                        docker cp "$EC2_SSH_KEY_FILE" "$CINC_CONTAINER:/tmp/jenkins-ec2-key"
                        docker exec "$CINC_CONTAINER" chmod 0700 /root/.ssh
                        docker exec "$CINC_CONTAINER" chmod 0600 \\
                            /root/.ssh/config /tmp/jenkins-ec2-key

                        echo "Cinc Auditor version:"
                        docker exec "$CINC_CONTAINER" cinc-auditor version

                        echo "Running compliance scan against ${EC2_HOST}..."
                        if docker exec "$CINC_CONTAINER" cinc-auditor exec \\
                            /work/inspec-profile \\
                            -t "ssh://${EC2_SSH_USER}@${EC2_HOST}" \\
                            -i /tmp/jenkins-ec2-key \\
                            --reporter cli json:/work/inspec-output/inspec-report.json; then
                            INSPEC_EXIT=0
                        else
                            INSPEC_EXIT=$?
                        fi

                        # Copy the report back even when controls fail, so Jenkins
                        # can archive the compliance evidence in the stage post block.
                        if docker exec "$CINC_CONTAINER" test -s \\
                            /work/inspec-output/inspec-report.json; then
                            docker cp \\
                                "$CINC_CONTAINER:/work/inspec-output/inspec-report.json" \\
                                inspec-output/inspec-report.json
                        else
                            echo "Cinc Auditor did not produce a JSON report." >&2
                        fi

                        echo "Cinc Auditor exit code: ${INSPEC_EXIT}"
                        case "$INSPEC_EXIT" in
                            0)
                                echo "Compliance scan: all controls passed."
                                ;;
                            100)
                                echo "Compliance scan: one or more controls failed." >&2
                                exit 1
                                ;;
                            101)
                                echo "Compliance scan: one or more controls were skipped; review the report."
                                ;;
                            *)
                                echo "Cinc Auditor execution failed with exit code ${INSPEC_EXIT}." >&2
                                exit 1
                                ;;
                        esac

                        echo "Compliance scan completed."
                    '''
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'inspec-output/inspec-report.json',
                                     allowEmptyArchive: true,
                                     fingerprint: true
                }
            }
        }

        stage('DAST - OWASP ZAP') {
            steps {
                withCredentials([
                    string(credentialsId: 'EC2_HOST', variable: 'EC2_HOST')
                ]) {
                    sh '''
                        set -eu
                        set +x
                        TARGET="http://${EC2_HOST}:8081"
                        echo "Waiting for staging health endpoint..."
                        READY="false"
                        for ATTEMPT in $(seq 1 30); do
                            if curl -fsS --max-time 5 "${TARGET}/health" >/dev/null 2>&1; then
                                READY="true"
                                break
                            fi
                            sleep 2
                        done
                        if [ "$READY" != "true" ]; then
                            echo "Staging health endpoint not reachable at ${TARGET}/health" >&2
                            exit 1
                        fi
                        docker run --rm ghcr.io/zaproxy/zaproxy:stable \
                            zap-baseline.py -t "$TARGET" -I
                        echo "DAST scan completed!"
                    '''
                }
            }
        }

        // This stage promotes the same ECR manifest by tagging it production.
        // It does NOT deploy to a separate production EC2 host.
        stage('Promote Image in ECR - Production Tag') {
            steps {
                input message: 'Promote this image to the ECR production tag?', ok: 'Promote image'
                withCredentials([
                    string(credentialsId: 'AWS_REGION', variable: 'AWS_REGION'),
                    string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY'),
                    string(credentialsId: 'ECR_REGISTRY', variable: 'ECR_REGISTRY')
                ]) {
                    sh '''
                        set -eu
                        set +x
                        MANIFEST="$(.ci-tools/bin/aws ecr batch-get-image \
                            --repository-name ssdlc-app \
                            --image-ids imageTag="$IMAGE_TAG" \
                            --region "$AWS_REGION" \
                            --query 'images[0].imageManifest' \
                            --output text)"
                        if [ -z "$MANIFEST" ] || [ "$MANIFEST" = "None" ]; then
                            echo "Could not retrieve manifest for image tag ${IMAGE_TAG}" >&2
                            exit 1
                        fi
                        .ci-tools/bin/aws ecr put-image \
                            --repository-name ssdlc-app \
                            --image-tag production \
                            --image-manifest "$MANIFEST" \
                            --region "$AWS_REGION"
                        echo "Promoted ${ECR_REGISTRY}/ssdlc-app:${IMAGE_TAG} to :production."
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed. Review the first failed stage in the console output.'
        }
    }
}