targetScope = 'resourceGroup'

@description('Region approved for the isolated mining demo.')
param location string = 'southeastasia'

@description('New account name; deployment must be refused if an unrelated account already exists.')
param accountName string = 'kppfoundry48254cc6'

@description('New project belonging only to this demo.')
param projectName string = 'kpp-mining-demo'

@description('Object ID of the operator authorized to run the new demo project.')
param operatorPrincipalId string

var tags = {
  demo_id: '48254cc6'
  workload: 'mining-migration'
  data_classification: 'synthetic-only'
  managed_by: 'kpp-demo'
}

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
  properties: {
    allowProjectManagement: true
    customSubDomainName: accountName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: projectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
  properties: {
    displayName: 'KPP Synthetic Mining Migration Demo'
    description: 'Demo-owned synthetic content only. No existing business system connections.'
  }
}

resource operatorAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, operatorPrincipalId, '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  scope: project
  properties: {
    principalId: operatorPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

output accountId string = account.id
output projectId string = project.id
output accountName string = account.name
output projectName string = project.name
