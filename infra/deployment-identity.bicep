targetScope = 'resourceGroup'

param location string = 'eastasia'

resource publisher 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'kppdemo-deploy-48254cc6'
  location: location
  tags: {
    demo_id: '48254cc6'
    workload: 'mining-migration'
    purpose: 'bounded-deployment-helper'
    data_classification: 'synthetic-only'
  }
}

resource maf 'Microsoft.Web/sites@2024-11-01' existing = {
  name: 'kppdemo-maf-48254cc6'
}

var websiteContributor = 'de139f84-1756-47ae-9be6-808fbbe84772'
resource publishAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(maf.id, publisher.id, websiteContributor)
  scope: maf
  properties: {
    principalId: publisher.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions', websiteContributor
    )
  }
}

output identityId string = publisher.id
output principalId string = publisher.properties.principalId
output clientId string = publisher.properties.clientId
