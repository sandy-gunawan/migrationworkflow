targetScope = 'resourceGroup'

param location string = 'eastasia'
param runId string
@allowed(['deploy-maf', 'verify-maf', 'diagnose-maf', 'verify-logic', 'rehearse-core'])
param jobMode string = 'deploy-maf'
@secure()
param scriptBase64 string
@secure()
param sourceZipBase64 string
@secure()
param requirementsBase64 string
@secure()
param testDataBase64 string

resource publisher 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: 'kppdemo-deploy-48254cc6'
}

resource job 'Microsoft.ContainerInstance/containerGroups@2023-05-01' = {
  name: 'kppdemo-${jobMode}-48254cc6-${runId}'
  location: location
  tags: {
    demo_id: '48254cc6'
    workload: 'mining-migration'
    purpose: 'bounded-deployment-helper-not-app-host'
    data_classification: 'synthetic-only'
    max_runtime_seconds: '3600'
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${publisher.id}': {}
    }
  }
  properties: {
    osType: 'Linux'
    restartPolicy: 'Never'
    containers: [
      {
        name: 'publisher'
        properties: {
          image: 'mcr.microsoft.com/azure-cli@sha256:a4e2660b4099b76f02001a9316a0eb0dc56e330b5f7d1d1312c932200645bf26'
          command: [
            'python3'
            '-c'
            'import base64, os; exec(base64.b64decode(os.environ["KPP_JOB_SCRIPT"]))'
          ]
          environmentVariables: [
            { name: 'KPP_JOB_SCRIPT', secureValue: scriptBase64 }
            { name: 'KPP_SOURCE_ZIP', secureValue: sourceZipBase64 }
            { name: 'KPP_REQUIREMENTS', secureValue: requirementsBase64 }
            { name: 'KPP_TEST_DATA', secureValue: testDataBase64 }
            { name: 'KPP_IDENTITY_CLIENT_ID', value: publisher.properties.clientId }
            { name: 'KPP_JOB_MODE', value: jobMode }
            { name: 'HOME', value: '/tmp/kpphome' }
            { name: 'AZURE_CONFIG_DIR', value: '/tmp/kpp-azure' }
            { name: 'PIP_CACHE_DIR', value: '/tmp/kpp-pip' }
            { name: 'PYTHONUNBUFFERED', value: '1' }
            { name: 'AZURE_CORE_COLLECT_TELEMETRY', value: 'no' }
          ]
          resources: {
            requests: {
              cpu: 1
              memoryInGB: 2
            }
          }
          securityContext: {
            privileged: false
          }
        }
      }
    ]
  }
}

output jobName string = job.name
output jobId string = job.id
