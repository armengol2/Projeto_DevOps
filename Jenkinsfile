pipeline {
    agent any

    options {
        skipDefaultCheckout()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
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
                    archiveArtifacts artifacts: 'target/surefire-reports/TEST-*.xml',
                                     allowEmptyArchive: true
                }
            }
        }

        stage('Build e verificação') {
            steps {
                sh 'mvn -B -ntp -DskipTests verify'
                archiveArtifacts artifacts: 'target/chamados-laboratorio-*.jar',
                                 fingerprint: true
            }
        }
    }
}
