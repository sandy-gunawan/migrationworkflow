targetScope = 'resourceGroup'

resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' = {
  name: 'kppdeploy48254cc6'
  location: 'southeastasia'
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  tags: {
    demo_id: '48254cc6'
    workload: 'mining-migration-artifacts'
    data_classification: 'synthetic-only'
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Disabled'
  }
}

resource blobs 'Microsoft.Storage/storageAccounts/blobServices@2025-01-01' = {
  parent: storage
  name: 'default'
}

resource packages 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-01-01' = {
  parent: blobs
  name: 'demo-artifacts'
  properties: {
    publicAccess: 'None'
  }
}

resource setupRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, '50d57e04-3ed5-4123-bf9f-e3a8739009c9', 'blob-setup')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: '50d57e04-3ed5-4123-bf9f-e3a8739009c9'
    principalType: 'User'
  }
}

output storageId string = storage.id
