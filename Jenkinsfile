pipeline {
    agent any

    options {
        skipDefaultCheckout()
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    def revision = checkout scm
                    env.GIT_COMMIT = revision.GIT_COMMIT ?: ''
                    env.GIT_BRANCH = revision.GIT_BRANCH ?: ''
                }
            }
        }

        stage('Testes SMTP') {
            steps {
                sh '''#!/bin/sh
mkdir -p reports
python3 -m coverage run -m unittest discover -s tests -v > reports/smtp-tests.log 2>&1
test_status=$?
cat reports/smtp-tests.log
exit "$test_status"
'''
            }
            post {
                always {
                    sh script: 'mkdir -p reports && python3 -m coverage xml --fail-under=0',
                       returnStatus: true
                    archiveArtifacts artifacts: 'reports/smtp-coverage.xml,reports/smtp-tests.log',
                                     allowEmptyArchive: true
                    sh 'python3 -m coverage report'
                }
            }
        }

        stage('Testes') {
            steps {
                sh 'mvn -B -ntp clean test'
            }
            post {
                always {
                    junit testResults: 'target/surefire-reports/TEST-*.xml',
                          allowEmptyResults: true
                    archiveArtifacts artifacts: 'target/surefire-reports/TEST-*.xml,target/site/jacoco/**',
                                     allowEmptyArchive: true
                }
            }
        }

        stage('Build e verificação') {
            steps {
                sh 'mvn -B -ntp verify'
                archiveArtifacts artifacts: 'target/chamados-laboratorio-*.jar',
                                 fingerprint: true
            }
            post {
                always {
                    archiveArtifacts artifacts: 'target/site/jacoco/**',
                                     allowEmptyArchive: true
                }
            }
        }
    }

    post {
        always {
            script {
                def pipelineResult = currentBuild.currentResult
                catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE', catchInterruptions: false) {
                    withEnv(["BUILD_STATUS=${pipelineResult}"]) {
                        sh 'python3 scripts/notify_email.py'
                    }
                }
            }
        }
    }
}