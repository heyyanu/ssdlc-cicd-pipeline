
pipeline {
    agent any

    options {
        disableConcurrentBuilds()
    }

    environment {
        SEMGREP_APP_TOKEN = credentials('SEMGREP_APP_TOKEN')
    }

    stages {

        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/heyyanu/ssdlc-cicd-pipeline.git'
            }
        }
        

        stage('Install Security Tools') {
            steps {
                sh '''
                    set -eu

                    mkdir -p .ci-tools/bin

                    echo "Installing Semgrep..."
                    if [ ! -x .ci-tools/semgrep/bin/semgrep ]; then
                        python3 -m venv .ci-tools/semgrep
                        .ci-tools/semgrep/bin/python -m pip install --upgrade pip semgrep
                    fi

                    echo "Installing Checkov..."
                    if [ ! -x .ci-tools/checkov/bin/checkov ]; then
                        python3 -m venv .ci-tools/checkov
                        .ci-tools/checkov/bin/python -m pip install --upgrade pip checkov
                    fi

                    echo "Installing pip-audit..."
                    if [ ! -x .ci-tools/pip-audit/bin/pip-audit ]; then
                        python3 -m venv .ci-tools/pip-audit
                        .ci-tools/pip-audit/bin/python -m pip install --upgrade pip pip-audit
                    fi

                    .ci-tools/semgrep/bin/semgrep --version
                    .ci-tools/checkov/bin/checkov --version
                    .ci-tools/pip-audit/bin/pip-audit --version

                    echo "Security tools ready!"
                '''
            }
        }

        stage('Build') {
            steps {
                sh '''
                    set -eu

                    echo "Creating Python virtual environment..."

                    if [ ! -x .venv/bin/python ]; then
                        python3 -m venv .venv
                    fi

                    .venv/bin/python -m pip install --upgrade pip

                    echo "Installing application dependencies..."
                    .venv/bin/python -m pip install -r requirements.txt

                    echo "Checking Python syntax..."
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

                    .venv/bin/python -m bandit \
                        -r . \
                        -ll \
                        --exclude ./.venv,./.ci-tools,./terraform/.terraform
                '''
            }
        }

        stage('Semgrep') {
            steps {
                sh '''
                    set -eu

                    echo "Running Semgrep..."

                    .ci-tools/semgrep/bin/semgrep ci --no-suppress-errors

                    echo "Semgrep scan completed!"
                '''
            }
        }

        stage('Secret Scan - Gitleaks') {
            steps {
                sh '''
                    set -eu

                    VERSION="8.30.1"
                    ARCH="$(uname -m)"

                    case "$ARCH" in
                        x86_64)
                            GITLEAKS_ARCH="x64"
                            ;;
                        aarch64|arm64)
                            GITLEAKS_ARCH="arm64"
                            ;;
                        *)
                            echo "Unsupported architecture: $ARCH"
                            exit 1
                            ;;
                    esac

                    TMP_DIR="$(mktemp -d)"
                    trap 'rm -rf "$TMP_DIR"' EXIT

                    echo "Downloading Gitleaks ${VERSION}..."

                    curl -fsSL \
                        "https://github.com/gitleaks/gitleaks/releases/download/v${VERSION}/gitleaks_${VERSION}_linux_${GITLEAKS_ARCH}.tar.gz" \
                        -o "$TMP_DIR/gitleaks.tar.gz"

                    tar -xzf "$TMP_DIR/gitleaks.tar.gz" -C "$TMP_DIR" gitleaks

                    install -m 0755 "$TMP_DIR/gitleaks" .ci-tools/bin/gitleaks

                    echo "Scanning Git history for secrets..."

                    .ci-tools/bin/gitleaks git --verbose .
                    
                    echo "Gitleaks scan completed!"
                '''
            }
        }

        stage('SCA - Dependency Check') {
            steps {
                sh '''
                    set -eu

                    echo "Auditing Python dependencies..."

                    .ci-tools/pip-audit/bin/pip-audit -r requirements.txt

                    echo "Dependency audit completed!"
                '''
            }
        }

        stage('IaC Scan - Checkov') {
            steps {
                sh '''
                    set -eu

                    echo "Scanning Terraform and Dockerfile..."

                    .ci-tools/checkov/bin/checkov \
                        -d . \
                        --framework terraform dockerfile

                    echo "IaC scan completed!"
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu

                    echo "Checking Docker access..."
                    docker version

                    docker build -t ssdlc-app:latest .

                    echo "Docker image built successfully!"
                '''
            }
        }

        stage('Deploy to Staging - Terraform') {
            steps {
                dir('terraform') {
                    sh '''
                        set -eu

                        TF_VERSION="1.6.0"
                        ARCH="$(uname -m)"

                        case "$ARCH" in
                            x86_64)
                                TF_ARCH="amd64"
                                ;;
                            aarch64|arm64)
                                TF_ARCH="arm64"
                                ;;
                            *)
                                echo "Unsupported architecture: $ARCH"
                                exit 1
                                ;;
                        esac

                        TF_BIN="../.ci-tools/bin/terraform"

                        if [ ! -x "$TF_BIN" ]; then

                            TMP_DIR="$(mktemp -d)"
                            trap 'rm -rf "$TMP_DIR"' EXIT

                            echo "Downloading Terraform..."

                            curl -fsSL \
                                "https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_${TF_ARCH}.zip" \
                                -o "$TMP_DIR/terraform.zip"

                            unzip -oq "$TMP_DIR/terraform.zip" -d ../.ci-tools/bin

                            chmod +x "$TF_BIN"
                        fi

                        echo "Formatting Terraform..."
                        "$TF_BIN" fmt -check -recursive

                        echo "Initializing Terraform..."
                        "$TF_BIN" init -input=false

                        echo "Validating Terraform..."
                        "$TF_BIN" validate

                        echo "Creating deployment plan..."
                        "$TF_BIN" plan -input=false -out=tfplan

                        echo "Deploying to staging..."
                        "$TF_BIN" apply -input=false -auto-approve tfplan

                        echo "Staging deployment completed!"

                        "$TF_BIN" output
                    '''
                }
            }
        }

        stage('DAST - OWASP ZAP') {
            steps {
                sh '''
                    set -eu

                    TARGET="http://host.docker.internal:8081"

                    echo "Checking staging application..."

                    READY="false"

                    for ATTEMPT in $(seq 1 30); do
                        if curl -fsS "$TARGET/" >/dev/null; then
                            READY="true"
                            break
                        fi

                        echo "Waiting for staging application..."
                        sleep 2
                    done

                    if [ "$READY" != "true" ]; then
                        echo "Staging application is not reachable!"
                        exit 1
                    fi

                    echo "Starting OWASP ZAP baseline scan..."

                    docker run --rm \
                        ghcr.io/zaproxy/zaproxy:stable \
                        zap-baseline.py \
                        -t "$TARGET" \
                        -I

                    echo "DAST scan completed!"
                '''
            }
        }

        stage('Deploy to Production') {
            steps {
                input message: 'Deploy to Production?',
                      ok: 'Yes Deploy!'

                sh '''
                    set -eu

                    docker tag ssdlc-app:latest ssdlc-app:production

                    docker image inspect ssdlc-app:production

                    echo "Production image tagged successfully!"
                '''
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully!'
        }

        failure {
            echo 'Pipeline failed! Check the console output.'
        }
    }
}
