#!/usr/bin/env groovy

pipeline {
    agent any
    environment {
        DOCKER_API_VERSION="1.24"
        DOCKER_CREDS=credentials('docker_m25907@cdoolympic.att.com')
        BUILD_IMAGE="dockercentral.it.att.com:5300/com.att.cdoolympic/com-att-cdo-olympic-build-system:latest"
        DOCKER_CMD="docker run --env TWINE_USERNAME=${DOCKER_CREDS_USR} --env TWINE_PASSWORD=${DOCKER_CREDS_PSW} " +
                "--env TWINE_REPOSITORY_URL=http://dockercentral.it.att.com:8093/nexus/repository/pypi-hosted/ " +
                "--env DOCKER_API_VERSION=${DOCKER_API_VERSION} --rm -v /var/run/docker.sock:/var/run/docker.sock " +
                "-v \${WORKSPACE}:/repo ${BUILD_IMAGE} /bin/bash -c"
    }
    options {
        buildDiscarder(logRotator(numToKeepStr: '5'))
    }
    stages {
        stage('Setup') {
            steps {
                sh("docker login -u ${DOCKER_CREDS_USR} -p ${DOCKER_CREDS_PSW} dockercentral.it.att.com:5300;" +
                   "docker pull ${BUILD_IMAGE};" +
                   "docker logout dockercentral.it.att.com:5300;")
            }
        }
        stage('Build & Upload Development') {
            when { not { branch 'master'} }
            steps {
                checkout scm
                sh("${DOCKER_CMD} \"source activate build; " +
                   "pip install jinja2 docker twine gitpython; " +
                   "pyb -X analyze publish twine_upload\"")
                archiveArtifacts artifacts: 'target/dist/*/dist/*.tar.gz', fingerprint: true
            }
        }
        
        stage('Build & Upload Release') {
            when { branch 'master' }
            steps {
                checkout scm
                sh("${DOCKER_CMD} \"source activate build; " +
                        "pip install jinja2 docker twine gitpython; " +
                        "pyb -X -P release=true analyze publish twine_upload\"")
                archiveArtifacts artifacts: 'target/dist/*/dist/*.tar.gz', fingerprint: true
            }
        }
    }
}
